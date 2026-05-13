"""Precompute the (state, target_pos, cand_edges, target_idx) tuples to
a .pt cache so train_v2 doesn't pay the per-sample Python cost on every
epoch. With 360k samples this turns 5min/epoch into <1min/epoch.

Output schema: a dict of stacked tensors per size:
  feats:      (n_samples, n_cells, 13)  float32
  target_pos: (n_samples,)              int64
  cand_edges: (n_samples, n_cands, 4)   int64
  target_idx: (n_samples,)              int64
  size:       int                       grid side (W=H)
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import torch

from dataset_v2 import TrajectoryDatasetV2
from dataset import load_jsonl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--candidates", type=int, default=12)
    args = ap.parse_args()

    recs = load_jsonl(args.in_path)
    ds = TrajectoryDatasetV2(recs, n_candidates=args.candidates)
    print(f"records: {len(recs)} samples: {len(ds)}")

    size = recs[0].size
    n_cells = size * size
    n_samples = len(ds)
    feats = torch.zeros(n_samples, n_cells, 13, dtype=torch.float32)
    tp = torch.zeros(n_samples, dtype=torch.long)
    cand = torch.zeros(n_samples, args.candidates, 4, dtype=torch.long)
    tidx = torch.zeros(n_samples, dtype=torch.long)

    t0 = time.time()
    for i in range(n_samples):
        f, p, c, k = ds[i]
        feats[i] = f
        tp[i] = p
        cand[i] = c
        tidx[i] = k
        if i > 0 and i % 50000 == 0:
            rate = i / (time.time() - t0)
            print(f"  {i}/{n_samples} ({rate:.0f}/s, ETA {(n_samples - i)/rate:.0f}s)")
    print(f"preprocessing took {time.time()-t0:.1f}s")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "feats": feats, "target_pos": tp, "cand_edges": cand, "target_idx": tidx,
        "size": size, "n_cells": n_cells, "n_candidates": args.candidates,
    }, out)
    print(f"saved -> {out} ({out.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
