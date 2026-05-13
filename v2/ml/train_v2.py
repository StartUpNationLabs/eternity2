"""Vol-28 imitation training for the position-relative scorer."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split

from dataset_v2 import TrajectoryDatasetV2
from dataset import load_jsonl
from model_v2 import PositionRelativeModel, build_neighbour_indices, build_valid_mask, param_count


def get_device():
    forced = os.environ.get("E2_ML_DEVICE")
    if forced:
        return torch.device(forced)
    return torch.device("cpu")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", action="append", required=True, help="path to JSONL (can be repeated for multi-size training)")
    ap.add_argument("--out", default="runs/v2/model.pt")
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--batch-size", type=int, default=512)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--hidden", type=int, default=64)
    ap.add_argument("--color-emb", type=int, default=16)
    ap.add_argument("--candidates", type=int, default=12)
    ap.add_argument("--val-frac", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    device = get_device()
    print(f"device: {device}")

    # Vol-28 — use all cores. M1 has 8 (4 perf + 4 efficiency); default
    # PyTorch picks 4. Bumping to 8 ~2x throughput on this workload.
    if device.type == "cpu":
        torch.set_num_threads(int(os.environ.get("E2_ML_THREADS", "8")))
        print(f"torch threads: {torch.get_num_threads()}")

    # Load records from all data paths. Each path can have a different
    # (size, color_count) since the model is size-agnostic.
    all_records = []
    sizes = set()
    for path in args.data:
        recs = load_jsonl(path)
        all_records.extend(recs)
        for r in recs:
            sizes.add(r.size)
        print(f"  {path}: {len(recs)} records, size {recs[0].size}")
    print(f"total: {len(all_records)} records, sizes: {sorted(sizes)}")

    # Build per-size nb_idx / valid_mask caches. Group samples by size at
    # collate time so each batch has a single shape.
    nb_cache = {s: build_neighbour_indices(s, s) for s in sizes}
    vm_cache = {s: build_valid_mask(s, s) for s in sizes}

    ds = TrajectoryDatasetV2(all_records, n_candidates=args.candidates, seed=args.seed)
    # Tag each sample with its size for size-aware batching.
    sample_sizes = [all_records[ds.index[i].rec_idx].size for i in range(len(ds))]

    n_total = len(ds)
    n_val = int(n_total * args.val_frac)
    n_train = n_total - n_val
    train_ds, val_ds = random_split(ds, [n_train, n_val], generator=torch.Generator().manual_seed(args.seed))

    # Build per-size sample-index lists for round-robin batch sampling
    # (each batch has a single size).
    def by_size(subset):
        out = {s: [] for s in sizes}
        for i in subset.indices:
            out[sample_sizes[i]].append(i)
        return out

    train_by_size = by_size(train_ds)
    val_by_size = by_size(val_ds)

    def batches_for(subset_by_size, batch_size, shuffle):
        # Yield (size, [indices]) batches, all same-size within a batch.
        import random
        out = []
        for sz, idxs in subset_by_size.items():
            if shuffle:
                random.shuffle(idxs)
            for k in range(0, len(idxs), batch_size):
                out.append((sz, idxs[k:k + batch_size]))
        if shuffle:
            random.shuffle(out)
        return out

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
        batch_iter = batches_for(train_by_size, args.batch_size, shuffle=True)
        n_batches = len(batch_iter)
        batch_t0 = time.time()
        for b_idx, (sz, idxs) in enumerate(batch_iter):
            B = len(idxs)
            feats_b = torch.stack([ds[i][0] for i in idxs]).to(device)
            tp_b = torch.stack([ds[i][1] for i in idxs]).to(device)
            cand_b = torch.stack([ds[i][2] for i in idxs]).to(device)
            tidx_b = torch.stack([ds[i][3] for i in idxs]).to(device)
            nb = nb_cache[sz].to(device)
            vm = vm_cache[sz].to(device)

            logits = model(feats_b, nb, vm, tp_b, cand_b)
            loss = loss_fn(logits, tidx_b)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            opt.step()
            train_loss += float(loss.item()) * B
            train_correct += int((logits.argmax(dim=1) == tidx_b).sum().item())
            train_n += B
            # Heartbeat every 100 batches so we can monitor stuck runs.
            if b_idx > 0 and b_idx % 100 == 0:
                rate = (b_idx + 1) / (time.time() - batch_t0)
                print(f"  epoch {epoch} batch {b_idx}/{n_batches} rate={rate:.1f}/s loss={train_loss/max(1,train_n):.3f} acc={train_correct/max(1,train_n):.3f}", flush=True)
        train_loss /= max(1, train_n)
        train_acc = train_correct / max(1, train_n)

        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_n = 0
        with torch.no_grad():
            for sz, idxs in batches_for(val_by_size, args.batch_size, shuffle=False):
                B = len(idxs)
                feats_b = torch.stack([ds[i][0] for i in idxs]).to(device)
                tp_b = torch.stack([ds[i][1] for i in idxs]).to(device)
                cand_b = torch.stack([ds[i][2] for i in idxs]).to(device)
                tidx_b = torch.stack([ds[i][3] for i in idxs]).to(device)
                nb = nb_cache[sz].to(device)
                vm = vm_cache[sz].to(device)
                logits = model(feats_b, nb, vm, tp_b, cand_b)
                loss = loss_fn(logits, tidx_b)
                val_loss += float(loss.item()) * B
                val_correct += int((logits.argmax(dim=1) == tidx_b).sum().item())
                val_n += B
        val_loss /= max(1, val_n)
        val_acc = val_correct / max(1, val_n)

        dt = time.time() - t0
        msg = {
            "epoch": epoch, "train_loss": train_loss, "train_acc": train_acc,
            "val_loss": val_loss, "val_acc": val_acc, "seconds": dt,
        }
        print(json.dumps(msg))
        log_f.write(json.dumps(msg) + "\n")
        log_f.flush()

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save({
                "state_dict": model.state_dict(),
                "hidden": args.hidden,
                "color_emb": args.color_emb,
                "epoch": epoch,
                "val_acc": val_acc,
            }, out_path)
            print(f"  saved (val_acc={val_acc:.4f})")

    log_f.close()
    print(f"best val_acc: {best_val_acc:.4f}")


if __name__ == "__main__":
    main()
