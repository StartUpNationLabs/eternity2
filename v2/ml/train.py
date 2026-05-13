"""Imitation training loop for vol-26 PlacementModel.

usage: uv run python train.py --data data/train_6x6_5c.jsonl --out runs/v1/model.pt
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split

from dataset import TrajectoryDataset, action_count, load_jsonl
from model import PlacementModel, param_count


def get_device() -> torch.device:
    forced = os.environ.get("E2_ML_DEVICE")
    if forced:
        return torch.device(forced)
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/train_6x6_5c.jsonl")
    ap.add_argument("--out", default="runs/v1/model.pt")
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--batch-size", type=int, default=512)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--hidden", type=int, default=64)
    ap.add_argument("--val-frac", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    device = get_device()
    print(f"device: {device}")

    records = load_jsonl(args.data)
    size = records[0].size
    n_pieces = size * size
    print(f"records: {len(records)}, size: {size}x{size}, n_pieces: {n_pieces}")

    ds = TrajectoryDataset(records)
    n_total = len(ds)
    n_val = int(n_total * args.val_frac)
    n_train = n_total - n_val
    train_ds, val_ds = random_split(
        ds, [n_train, n_val], generator=torch.Generator().manual_seed(args.seed)
    )
    print(f"train: {n_train}, val: {n_val}")

    # MPS doesn't support multi-worker DataLoader well; use 0 workers there.
    nw = 0 if device.type == "mps" else 2
    pin = device.type == "cuda"
    train_loader = DataLoader(
        train_ds, batch_size=args.batch_size, shuffle=True,
        num_workers=nw, pin_memory=pin, persistent_workers=nw > 0,
    )
    val_loader = DataLoader(
        val_ds, batch_size=args.batch_size, shuffle=False,
        num_workers=nw, pin_memory=pin, persistent_workers=nw > 0,
    )

    model = PlacementModel(size=size, n_pieces=n_pieces, hidden=args.hidden).to(device)
    print(f"params: {param_count(model):,}")

    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    loss_fn = nn.CrossEntropyLoss()
    n_actions = action_count(n_pieces)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    log_path = out_path.with_suffix(".log.jsonl")
    log_f = open(log_path, "w")

    best_val_acc = 0.0
    for epoch in range(1, args.epochs + 1):
        model.train()
        t0 = time.time()
        train_loss = 0.0
        train_correct = 0
        train_n = 0
        for feats, tp, ta in train_loader:
            feats = feats.to(device, non_blocking=True)
            tp = tp.to(device, non_blocking=True)
            ta = ta.to(device, non_blocking=True)
            logits = model(feats, tp)
            loss = loss_fn(logits, ta)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            opt.step()
            train_loss += loss.item() * feats.size(0)
            train_correct += int((logits.argmax(dim=1) == ta).sum().item())
            train_n += feats.size(0)

        train_loss /= train_n
        train_acc = train_correct / train_n

        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_n = 0
        with torch.no_grad():
            for feats, tp, ta in val_loader:
                feats = feats.to(device, non_blocking=True)
                tp = tp.to(device, non_blocking=True)
                ta = ta.to(device, non_blocking=True)
                logits = model(feats, tp)
                loss = loss_fn(logits, ta)
                val_loss += loss.item() * feats.size(0)
                val_correct += int((logits.argmax(dim=1) == ta).sum().item())
                val_n += feats.size(0)
        val_loss /= val_n
        val_acc = val_correct / val_n

        dt = time.time() - t0
        msg = {
            "epoch": epoch,
            "train_loss": train_loss,
            "train_acc": train_acc,
            "val_loss": val_loss,
            "val_acc": val_acc,
            "seconds": dt,
        }
        print(json.dumps(msg))
        log_f.write(json.dumps(msg) + "\n")
        log_f.flush()

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            payload = {
                "state_dict": model.state_dict(),
                "size": size,
                "n_pieces": n_pieces,
                "n_actions": n_actions,
                "hidden": args.hidden,
                "epoch": epoch,
                "val_acc": val_acc,
            }
            torch.save(payload, out_path)
            print(f"  saved checkpoint (val_acc={val_acc:.4f})")

    log_f.close()
    print(f"best val_acc: {best_val_acc:.4f}")
    print(f"checkpoint: {out_path}")


if __name__ == "__main__":
    main()
