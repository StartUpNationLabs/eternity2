#!/usr/bin/env python3
"""Vol-65 — Multiset-twin diagnostic on known 458/459 boards.

For each multiset-twin pair, look up where each twin sits in:
- local 459 (p06)
- vol-32 458
- vol-61 458 (seed17)
- vol-61 458 (seed200)

Goals:
1. Are twin pairs SWAPPED between any two boards? If so, those two
   boards differ by a twin-swap (Hamming distance ~2).
2. Are twin pieces near each other's positions across boards?
3. What's the rotation of each twin piece in each board?
"""

import json
from pathlib import Path

TWIN_PAIRS = [
    (2, 3, "corners"),
    (5, 14, "edges"),
    (7, 51, "edges"),
    (109, 110, "interior"),
    (171, 181, "interior"),
]

BOARDS = [
    ("local-459-p06", "output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json"),
    ("vol32-458", "output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json"),
    ("vol61-458-s17", "output/vol-61/faithful_sota_20260515T174124/stage3_seed17.json"),
    ("vol61-458-s200", "output/vol-61/faithful_sota_20260515T174124/stage3_seed200.json"),
]


def load_placement(path):
    """Return dict piece_id -> (pos, rotation)."""
    with open(path) as f:
        d = json.load(f)
    arr = d.get("placement", [])
    out = {}
    for idx, item in enumerate(arr):
        if item is None:
            continue
        pos = item.get("pos", idx)
        pid = item["piece_id"]
        rot = item["rotation"]
        out[pid] = (pos, rot)
    return out


def main():
    boards = {}
    for name, path in BOARDS:
        if not Path(path).exists():
            print(f"MISSING: {path}")
            continue
        boards[name] = load_placement(path)
    print(f"Loaded {len(boards)} boards:")
    for name in boards:
        print(f"  {name}: {len(boards[name])} pieces placed")
    print()

    # Per-twin-pair diagnostic
    for (a, b, kind) in TWIN_PAIRS:
        print(f"=== Twin pair ({a}, {b}) — {kind} ===")
        print(f"{'board':<20} | {'piece':>5} | {'pos':>5} | {'(x,y)':>7} | {'rot':>3}")
        for name, placement in boards.items():
            for p in (a, b):
                if p in placement:
                    pos, rot = placement[p]
                    x, y = pos % 16, pos // 16
                    print(f"  {name:<18} | {p:>5} | {pos:>5} | ({x:>2},{y:>2}) | {rot:>3}")
                else:
                    print(f"  {name:<18} | {p:>5} | NOT PLACED")
        print()

    # Cross-board comparison: is twin A's position in board1 = twin B's position in board2?
    # That's a swap signature.
    print("=" * 70)
    print("CROSS-BOARD SWAP DETECTION")
    print("Looking for: piece A at position P in board X, piece B at position P in board Y")
    print()
    for (a, b, kind) in TWIN_PAIRS:
        for n1 in boards:
            for n2 in boards:
                if n1 >= n2:
                    continue
                pa1 = boards[n1].get(a, (None, None))[0]
                pb1 = boards[n1].get(b, (None, None))[0]
                pa2 = boards[n2].get(a, (None, None))[0]
                pb2 = boards[n2].get(b, (None, None))[0]
                if pa1 == pb2 and pa1 is not None:
                    print(f"  Pair ({a},{b}): piece {a}@pos{pa1} in {n1} = piece {b}@pos{pb2} in {n2}")
                if pb1 == pa2 and pb1 is not None:
                    print(f"  Pair ({a},{b}): piece {b}@pos{pb1} in {n1} = piece {a}@pos{pa2} in {n2}")

    # Hamming distance between board pairs (piece-position-rotation tuples)
    print()
    print("=" * 70)
    print("HAMMING DISTANCES (cells where placement differs)")
    print()
    names = sorted(boards.keys())
    print(f"{'':>20}", end="")
    for n in names:
        print(f" {n[:14]:>15}", end="")
    print()
    for n1 in names:
        print(f"{n1:>20}", end="")
        for n2 in names:
            if n1 == n2:
                print(f" {'-':>15}", end="")
                continue
            # Cells differ if (piece, rot) at position differs
            # Build pos -> (piece, rot)
            d1 = {pos: (p, r) for p, (pos, r) in boards[n1].items()}
            d2 = {pos: (p, r) for p, (pos, r) in boards[n2].items()}
            all_pos = set(d1.keys()) | set(d2.keys())
            diff = sum(1 for pos in all_pos if d1.get(pos) != d2.get(pos))
            same_piece_diff_rot = sum(
                1 for pos in all_pos
                if d1.get(pos) and d2.get(pos)
                and d1[pos][0] == d2[pos][0]
                and d1[pos][1] != d2[pos][1]
            )
            print(f" {diff:>11}/{same_piece_diff_rot:<3}", end="")
        print()
    print("(value=different_cells / of_which_same_piece_different_rotation)")


if __name__ == "__main__":
    main()
