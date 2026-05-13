"""Vol-28 train_v2 reading from a preprocessed .pt cache (built by
preprocess_v2.py). Each epoch becomes a pure tensor iteration, ~3-5s CPU."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader, random_split

from model_v2 import (
    PositionRelativeModel,
    build_neighbour_indices,
    build_valid_mask,
    param_count,
)


def get_device():
    forced = os.environ.get("E2_ML_DEVICE")
    if forced:
        return torch.device(forced)
    return torch.device("cpu")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", action="append", required=True)
    ap.add_argument("--out", default="runs/v2/model.pt")
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--batch-size", type=int, default=512)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--hidden", type=int, default=64)
    ap.add_argument("--color-emb", type=int, default=16)
    ap.add_argument("--val-frac", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    device = get_device()
    if device.type == "cpu":
        torch.set_num_threads(int(os.environ.get("E2_ML_THREADS", "8")))
    print(f"device: {device}, threads: {torch.get_num_threads()}")

    size_datasets = {}
    for path in args.data:
        payload = torch.load(path, map_location="cpu", weights_only=False)
        size = int(payload["size"])
        ds = TensorDataset(
            payload["feats"], payload["target_pos"],
            payload["cand_edges"], payload["target_idx"],
        )
        if size in size_datasets:
            old = size_datasets[size]
            tensors = [torch.cat([old.tensors[i], ds.tensors[i]], dim=0) for i in range(4)]
            size_datasets[size] = TensorDataset(*tensors)
        else:
            size_datasets[size] = ds
        print(f"  {path}: size={size}, samples={len(ds)}")

    nb_cache = {s: build_neighbour_indices(s, s).to(device) for s in size_datasets}
    vm_cache = {s: build_valid_mask(s, s).to(device) for s in size_datasets}

    train_loaders = {}
    val_loaders = {}
    for s, ds in size_datasets.items():
        n_total = len(ds)
        n_val = int(n_total * args.val_frac)
        n_train = n_total - n_val
        train_ds, val_ds = random_split(ds, [n_train, n_val], generator=torch.Generator().manual_seed(args.seed))
        train_loaders[s] = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=0)
        val_loaders[s] = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)
    print(f"sizes: {sorted(size_datasets.keys())}")

    model = PositionRelativeModel(hidden=args.hidden, color_emb=args.color_emb).to(device)
    print(f"params: {param_count(model):,}")

    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    loss_fn = nn.CrossEntropyLoss()

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
        iters = {s: iter(train_loaders[s]) for s in size_datasets}
        active = set(iters.keys())
        while active:
            for s in list(active):
                try:
                    feats_b, tp_b, cand_b, tidx_b = next(iters[s])
                except StopIteration:
                    active.discard(s)
                    continue
                feats_b = feats_b.to(device)
                tp_b = tp_b.to(device)
                cand_b = cand_b.to(device)
                tidx_b = tidx_b.to(device)
                logits = model(feats_b, nb_cache[s], vm_cache[s], tp_b, cand_b)
                loss = loss_fn(logits, tidx_b)
                opt.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                opt.step()
                B = feats_b.size(0)
                train_loss += float(loss.item()) * B
                train_correct += int((logits.argmax(dim=1) == tidx_b).sum().item())
                train_n += B
        train_loss /= max(1, train_n)
        train_acc = train_correct / max(1, train_n)

        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_n = 0
        with torch.no_grad():
            for s in size_datasets:
                for feats_b, tp_b, cand_b, tidx_b in val_loaders[s]:
                    feats_b = feats_b.to(device); tp_b = tp_b.to(device)
                    cand_b = cand_b.to(device); tidx_b = tidx_b.to(device)
                    logits = model(feats_b, nb_cache[s], vm_cache[s], tp_b, cand_b)
                    loss = loss_fn(logits, tidx_b)
                    B = feats_b.size(0)
                    val_loss += float(loss.item()) * B
                    val_correct += int((logits.argmax(dim=1) == tidx_b).sum().item())
                    val_n += B
        val_loss /= max(1, val_n)
        val_acc = val_correct / max(1, val_n)

        dt = time.time() - t0
        msg = {"epoch": epoch, "train_loss": train_loss, "train_acc": train_acc,
               "val_loss": val_loss, "val_acc": val_acc, "seconds": dt}
        print(json.dumps(msg), flush=True)
        log_f.write(json.dumps(msg) + "\n"); log_f.flush()

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save({
                "state_dict": model.state_dict(),
                "hidden": args.hidden, "color_emb": args.color_emb,
                "epoch": epoch, "val_acc": val_acc,
            }, out_path)
            print(f"  saved (val_acc={val_acc:.4f})", flush=True)

    log_f.close()
    print(f"best val_acc: {best_val_acc:.4f}")


if __name__ == "__main__":
    main()
