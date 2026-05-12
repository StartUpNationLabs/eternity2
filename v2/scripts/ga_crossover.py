#!/usr/bin/env python3
"""Block crossover for the Eternity II memetic genetic algorithm.

Given two parent boards A and B (both with score ≥ 440):
1. Pick a random K×K region (default K=6).
2. For cells inside the region: take pieces from parent A.
3. For cells outside: take pieces from parent B.
4. Detect piece duplicates (some pieces may now appear twice; some
   may not appear at all).
5. Repair duplicates: for each duplicate piece, find an unused piece
   of the same class (corner/edge/interior) and swap the duplicate
   instance with one of B's pieces that's currently unused.

The result is a valid full board (each piece used exactly once),
class-respecting, with a coherent A-block transplanted onto a
B-skeleton.

Each piece's rotation is initially copied from its source parent;
no rotation re-optimization (left to subsequent SA polish).

Usage:
    python3 scripts/ga_crossover.py PARENT_A.json PARENT_B.json \\
        --region-x X --region-y Y --region-k K \\
        --out child.json [--seed N]

The output JSON has a `placement` array compatible with
`pt_e2 --start-from` for follow-up polishing.

This is the FIRST building block of the GA. Future:
- ga_population.py (manage pop, run generations).
- ga_orchestrator.sh (call pt_e2 short-PT for mutation/settle).
"""

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path


W = 16
H = 16
BORDER = 0


def parse_csv_piece_word(s):
    v = int(s.strip(), 2)
    if v == 65535:
        return 0
    return v


def load_pieces(path):
    pieces = []
    with open(path) as f:
        size = int(f.readline().strip())
        for pid, line in enumerate(f):
            cols = line.strip().split(',')
            if len(cols) < 4:
                continue
            pieces.append(tuple(parse_csv_piece_word(cols[i]) for i in range(4)))
    return pieces


def piece_class(quad):
    n = sum(1 for c in quad if c == BORDER)
    return 0 if n >= 2 else (1 if n == 1 else 2)


def cell_class_pos(pos):
    x, y = pos % W, pos // W
    n = (x == 0) + (x == W-1) + (y == 0) + (y == H-1)
    return 0 if n >= 2 else (1 if n == 1 else 2)


def rotate_quad(q, rot):
    t, r, b, l = q
    if rot == 0: return (t, r, b, l)
    if rot == 1: return (l, t, r, b)
    if rot == 2: return (b, l, t, r)
    if rot == 3: return (r, b, l, t)


def load_board_placement(path):
    j = json.load(open(path))
    placement = j.get('placement')
    if placement is None:
        raise ValueError(f"no placement in {path}")
    return placement, j


def crossover(parent_a_placement, parent_b_placement, region_x, region_y, region_k,
              pieces, rng):
    """Block crossover: child = (A inside region) + (B outside region),
    with duplicate-piece repair.

    Returns (child_placement, n_repairs) where child_placement is a
    list of {piece_id, rotation} dicts (or None for empty cells —
    shouldn't happen for full boards).
    """
    # Build the inside set.
    region_cells = set()
    for dy in range(region_k):
        for dx in range(region_k):
            cx, cy = region_x + dx, region_y + dy
            if 0 <= cx < W and 0 <= cy < H:
                region_cells.add(cy * W + cx)

    child = []
    for pos in range(W * H):
        if pos in region_cells:
            child.append(parent_a_placement[pos])
        else:
            child.append(parent_b_placement[pos])

    # Detect duplicates and missing pieces.
    used = Counter()
    for p in child:
        if p is None:
            continue
        used[p['piece_id']] += 1

    n_pieces = len(pieces)
    duplicates = []  # (piece_id, list_of_positions_using_it)
    for pid, count in used.items():
        if count > 1:
            positions = [pos for pos, p in enumerate(child)
                          if p is not None and p['piece_id'] == pid]
            duplicates.append((pid, positions))

    missing = [pid for pid in range(n_pieces) if used[pid] == 0]

    # Repair: for each duplicate, replace ALL BUT ONE instance with a
    # missing piece of the same class. Prefer to keep the instance
    # whose source parent was A (= region) for region coherence.
    n_repairs = 0
    region_cells_set = region_cells
    for dup_pid, positions in duplicates:
        # Choose one to keep. Prefer in-region (came from A), else any.
        in_region = [p for p in positions if p in region_cells_set]
        if in_region:
            keep_pos = in_region[0]
        else:
            keep_pos = positions[0]
        replace_positions = [p for p in positions if p != keep_pos]

        dup_class = piece_class(pieces[dup_pid])
        for rep_pos in replace_positions:
            # Find a missing piece of the same class as needed for this cell.
            cell_cls = cell_class_pos(rep_pos)
            candidates = [m for m in missing if piece_class(pieces[m]) == cell_cls]
            if not candidates:
                # No missing piece fits this cell. Try any class match
                # (might violate class but full board still). Worst case
                # leave duplicate — child is invalid.
                candidates = [m for m in missing if piece_class(pieces[m]) == dup_class]
            if not candidates:
                continue  # leave as dup
            # Pick uniformly random from candidates.
            new_pid = rng.choice(candidates)
            missing.remove(new_pid)
            # Place new piece. Rotation: random valid rotation.
            child[rep_pos] = {"piece_id": new_pid, "rotation": 0}  # rotation TBD
            n_repairs += 1

    return child, n_repairs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("parent_a")
    ap.add_argument("parent_b")
    ap.add_argument("--puzzle", default="../data/puzzles/size_16_official_eternity.csv")
    ap.add_argument("--region-x", type=int, default=None,
                    help="if not given, randomized")
    ap.add_argument("--region-y", type=int, default=None)
    ap.add_argument("--region-k", type=int, default=6)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    pieces = load_pieces(args.puzzle)
    pa, ja = load_board_placement(args.parent_a)
    pb, jb = load_board_placement(args.parent_b)
    rng = random.Random(args.seed)

    if args.region_x is None:
        # Random interior position.
        rx = rng.randint(1, W - args.region_k - 1)
    else:
        rx = args.region_x
    if args.region_y is None:
        ry = rng.randint(1, H - args.region_k - 1)
    else:
        ry = args.region_y

    print(f"# crossover at region ({rx},{ry}) size {args.region_k}", file=sys.stderr)
    child, n_repairs = crossover(pa, pb, rx, ry, args.region_k, pieces, rng)
    print(f"# {n_repairs} duplicate-piece repairs", file=sys.stderr)

    # Compute resulting child score.
    quads = []
    for p in child:
        if p is None:
            quads.append((BORDER,)*4)
        else:
            quads.append(rotate_quad(pieces[p['piece_id']], p['rotation']))
    score = 0
    for y in range(H):
        for x in range(W):
            pos = y*W+x
            if x+1<W:
                if quads[pos][1] == quads[pos+1][3] and quads[pos][1] != BORDER:
                    score += 1
            if y+1<H:
                if quads[pos][2] == quads[pos+W][0] and quads[pos][2] != BORDER:
                    score += 1
    print(f"# child score: {score}/480", file=sys.stderr)

    out = {
        "run_name": f"ga_crossover_{rx}_{ry}_k{args.region_k}",
        "puzzle": {"name": "size_16_official_eternity"},
        "placement": child,
        "score": {"matched_edges": int(score), "total_edges": 480,
                  "percent": 100.0 * score / 480,
                  "placed_cells": int(sum(1 for c in child if c is not None)),
                  "total_cells": W*H},
        "ga": {"parent_a": args.parent_a, "parent_b": args.parent_b,
               "region_x": rx, "region_y": ry, "region_k": args.region_k,
               "n_repairs": int(n_repairs)},
    }
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print(f"# wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
