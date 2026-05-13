"""Vol-29 — preprocess canonical-E2 trajectory JSONL into a v2 .pt cache.

Joins the trajectory (depth, position, piece_id, rotation) records from
`canonical-capture` with the piece edge data parsed from
`../data/puzzles/size_16_official_eternity.csv`. Emits a single .pt
file with the same schema as `preprocess_v2.py` (feats / target_pos /
cand_edges / target_idx / size).

Filter: by default keep ALL placements from all seeds. Use
`--min-depth` to drop placements before some depth (e.g. skip the
trivial border-ring placements where almost any piece works), and
`--keep-top-frac` to keep only placements from runs that beat the
median max_depth (oracle-style imitation: learn from the "good"
trajectories, not the average).
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
import torch

from dataset_v2 import (
    fits_border,
    fits_placed_neighbours,
    border_mask_for,
    piece_rotations,
)
from dataset import _rotate

BORDER = 0


def parse_canonical_csv(path: str) -> list[list[int]]:
    """Returns a list of 256 piece edge tuples [top, right, bottom, left],
    indexed by piece_id. Color 65535 (BORDER) maps to 0; other colors
    map to their decimal value."""
    with open(path) as f:
        lines = [l.rstrip() for l in f if l.strip()]
    size = int(lines[0])
    n = size * size
    pieces: list[list[int]] = []
    for line in lines[1:n + 1]:
        cols = line.split(",")
        if len(cols) < 4:
            raise ValueError(f"bad line: {line!r}")
        e = []
        for col in cols[:4]:
            v = int(col, 2)
            e.append(0 if v == 65535 else v)
        pieces.append(e)
    return pieces


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traj", default="data/canonical_traj.jsonl")
    ap.add_argument("--puzzle", default="../data/puzzles/size_16_official_eternity.csv")
    ap.add_argument("--out", default="data/canonical_traj.v2.pt")
    ap.add_argument("--candidates", type=int, default=12)
    ap.add_argument("--min-depth", type=int, default=0)
    ap.add_argument("--keep-top-frac", type=float, default=1.0,
                    help="Keep placements only from runs whose max_depth is at or above this quantile (1.0=keep all)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    pieces = parse_canonical_csv(args.puzzle)
    n_pieces = len(pieces)
    size = int(np.sqrt(n_pieces))
    n_cells = size * size
    assert size * size == n_pieces, f"non-square puzzle: {n_pieces} pieces"
    print(f"canonical puzzle: {size}x{size}, {n_pieces} pieces")

    # Pre-compute rotations.
    rotations = [piece_rotations(p) for p in pieces]

    # Load trajectories.
    records = []
    with open(args.traj) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    print(f"loaded {len(records)} seed records; max_depth: {[r['max_depth'] for r in records]}")

    # Filter by max-depth quantile.
    if args.keep_top_frac < 1.0:
        depths = sorted(r["max_depth"] for r in records)
        cutoff_idx = int(len(depths) * (1.0 - args.keep_top_frac))
        cutoff = depths[cutoff_idx]
        records = [r for r in records if r["max_depth"] >= cutoff]
        print(f"after keep-top-frac={args.keep_top_frac}: {len(records)} seed records (depth >= {cutoff})")

    # Flatten to (state, target_pos, cand_edges, target_idx) tuples.
    samples = []
    for rec in records:
        placed_edges = np.zeros((n_cells, 4), dtype=np.int64)
        placed_flag = np.zeros(n_cells, dtype=np.int64)
        for step_idx, step in enumerate(rec["placements"]):
            depth = step["depth"]
            if depth >= args.min_depth:
                # Sample at this depth (BEFORE applying step).
                target_pos = int(step["position"])
                target_pid = int(step["piece_id"])
                target_rot = int(step["rotation"])
                samples.append({
                    "placed_edges": placed_edges.copy(),
                    "placed_flag": placed_flag.copy(),
                    "target_pos": target_pos,
                    "target_pid": target_pid,
                    "target_rot": target_rot,
                })
            # Apply this step to the partial.
            pos = int(step["position"])
            pid = int(step["piece_id"])
            rot = int(step["rotation"])
            placed_flag[pos] = 1
            placed_edges[pos] = _rotate(pieces[pid], rot)
    n_samples = len(samples)
    print(f"flattened: {n_samples} (state, target) samples")

    feats = torch.zeros(n_samples, n_cells, 13, dtype=torch.float32)
    tp = torch.zeros(n_samples, dtype=torch.long)
    cand = torch.zeros(n_samples, args.candidates, 4, dtype=torch.long)
    tidx = torch.zeros(n_samples, dtype=torch.long)

    for i, s in enumerate(samples):
        placed_edges = s["placed_edges"]
        placed_flag = s["placed_flag"]
        target_pos = s["target_pos"]
        target_pid = s["target_pid"]
        target_rot = s["target_rot"]

        # Build the 13-D per-cell features.
        nb_known = np.zeros((n_cells, 4), dtype=np.int64)
        border_mask = np.zeros((n_cells, 4), dtype=np.int64)
        for y in range(size):
            for x in range(size):
                pos = y * size + x
                if y == 0:
                    border_mask[pos, 0] = 1; nb_known[pos, 0] = 1
                elif placed_flag[(y - 1) * size + x] == 1:
                    nb_known[pos, 0] = 1
                if x == size - 1:
                    border_mask[pos, 1] = 1; nb_known[pos, 1] = 1
                elif placed_flag[y * size + (x + 1)] == 1:
                    nb_known[pos, 1] = 1
                if y == size - 1:
                    border_mask[pos, 2] = 1; nb_known[pos, 2] = 1
                elif placed_flag[(y + 1) * size + x] == 1:
                    nb_known[pos, 2] = 1
                if x == 0:
                    border_mask[pos, 3] = 1; nb_known[pos, 3] = 1
                elif placed_flag[y * size + (x - 1)] == 1:
                    nb_known[pos, 3] = 1
        f = np.concatenate([
            placed_edges, nb_known, placed_flag[:, None], border_mask,
        ], axis=1).astype(np.float32)
        feats[i] = torch.from_numpy(f)

        # Build candidates: expert + N-1 negatives.
        expert = rotations[target_pid][target_rot]
        bm = border_mask_for(target_pos, size, size)
        cands = [expert]
        seen = {tuple(expert)}
        attempts = 0
        while len(cands) < args.candidates and attempts < 800:
            attempts += 1
            pid = rng.randrange(n_pieces)
            rot = rng.randrange(4)
            if pid == target_pid and rot == target_rot:
                continue
            ce = rotations[pid][rot]
            if not fits_border(ce, bm):
                continue
            if not fits_placed_neighbours(ce, placed_edges, target_pos, size, size):
                continue
            t = tuple(ce)
            if t in seen:
                continue
            seen.add(t)
            cands.append(ce)
        # Pad with synthetic border-only edges if needed.
        while len(cands) < args.candidates:
            ce = [
                0 if bm[0] else rng.randint(1, 22),
                0 if bm[1] else rng.randint(1, 22),
                0 if bm[2] else rng.randint(1, 22),
                0 if bm[3] else rng.randint(1, 22),
            ]
            t = tuple(ce)
            if t in seen:
                continue
            seen.add(t)
            cands.append(ce)
        # Shuffle so the expert isn't always at index 0.
        order = list(range(args.candidates))
        rng.shuffle(order)
        cand_arr = np.array([cands[k] for k in order], dtype=np.int64)
        target_idx = order.index(0)

        tp[i] = target_pos
        cand[i] = torch.from_numpy(cand_arr)
        tidx[i] = target_idx

        if i > 0 and i % 500 == 0:
            print(f"  {i}/{n_samples}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "feats": feats, "target_pos": tp, "cand_edges": cand, "target_idx": tidx,
        "size": size, "n_cells": n_cells, "n_candidates": args.candidates,
    }, out)
    print(f"saved -> {out} ({out.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
