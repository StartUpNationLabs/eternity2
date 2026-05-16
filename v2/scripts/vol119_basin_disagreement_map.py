#!/usr/bin/env python3
"""Vol-119 — basin disagreement / skeleton map.

For a corpus of basins:
- skeleton(c) = number of distinct (piece, rot) values seen at cell c across the corpus.
- skeleton(c) = 1  → all basins agree → MIP has no choice here.
- skeleton(c) > 1  → MIP can pick — but only piece-uniqueness limits.

Reports:
- # cells with skeleton = 1 (no MIP choice).
- # cells with skeleton ≥ 2 (mip-relevant).
- Per-cell-class breakdown (corner / border / interior).
- Distribution of skeleton sizes.

Usage:
    vol119_basin_disagreement_map.py board1.json board2.json ...
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path


def load_board(p):
    with open(p) as f:
        d = json.load(f)
    arr = d.get("placement") or d.get("board", {}).get("placement", [])
    out = {}
    for idx, item in enumerate(arr):
        if item is None:
            continue
        pos = int(item.get("pos", idx))
        out[pos] = (int(item["piece_id"]), int(item["rotation"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("boards", nargs="+")
    args = ap.parse_args()

    W, H = 16, 16
    boards = []
    for p in args.boards:
        b = load_board(Path(p))
        if len(b) > 200:
            boards.append((p, b))
    print(f"# loaded {len(boards)} boards with ≥200 placements")

    # Per-cell skeleton size (distinct (pid, rot))
    cell_choices = defaultdict(set)
    for path, b in boards:
        for pos, (pid, rot) in b.items():
            cell_choices[pos].add((pid, rot))

    skeleton_size = {pos: len(s) for pos, s in cell_choices.items()}
    distribution = defaultdict(int)
    for pos, sz in skeleton_size.items():
        distribution[sz] += 1

    print(f"\nSkeleton size distribution (cell → #distinct (pid,rot)):")
    for sz in sorted(distribution):
        print(f"  size={sz}: {distribution[sz]} cells")

    # Cell-class breakdown
    def cell_class(pos):
        x, y = pos % W, pos // W
        if (x == 0 or x == W - 1) and (y == 0 or y == H - 1):
            return "corner"
        if x == 0 or x == W - 1 or y == 0 or y == H - 1:
            return "border"
        return "interior"

    by_class_diverse = defaultdict(int)
    by_class_total = defaultdict(int)
    for pos in range(W * H):
        cc = cell_class(pos)
        by_class_total[cc] += 1
        if skeleton_size.get(pos, 0) > 1:
            by_class_diverse[cc] += 1

    print(f"\nDiversity by cell class:")
    for cc in ("corner", "border", "interior"):
        d = by_class_diverse[cc]
        t = by_class_total[cc]
        print(f"  {cc:9s}: {d}/{t} cells have ≥2 choices ({100*d/t:.1f}%)")

    n_total = sum(by_class_total.values())
    n_diverse = sum(by_class_diverse.values())
    print(f"  TOTAL:    {n_diverse}/{n_total} cells diverse ({100*n_diverse/n_total:.1f}%)")

    # If MIP picks the best (piece, rot) at each diverse cell, what's the
    # upper-bound score given all (pid, rot) options are available?
    # (This is a CRUDE upper bound — ignores piece-uniqueness.)
    print(f"\nDiverse-cell list (first 20):")
    diverse_cells = sorted([p for p, sz in skeleton_size.items() if sz > 1])
    print(f"  count = {len(diverse_cells)}")
    print(f"  positions = {diverse_cells[:20]}{'...' if len(diverse_cells) > 20 else ''}")


if __name__ == "__main__":
    main()
