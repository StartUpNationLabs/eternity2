#!/usr/bin/env python3
"""Vol-65 — Global invariants on records.

Compute for each board:
1. Net "rotation count": Σ rotation_k over all interior pieces. Mod 4.
   If this is invariant under valid local moves, it's a topological
   invariant of the basin.
2. Color-direction histogram: count of (color c, world-direction d)
   for each (c, d) pair, over all interior piece-sides. The sum over c
   for each d gives the total "color budget per direction".
3. Per-row/col color profile: how does color usage vary across rows?
4. Mismatch geometry signature: 2D Fourier of mismatch indicator grid.

If any of these differs between our records and McGavin, we have a
structural invariant that constrains basin transitions.
"""

import collections
import csv
import json
import urllib.parse
from pathlib import Path

import numpy as np

PUZZLE_CSV = "../data/puzzles/size_16_official_eternity.csv"


def load_pieces():
    BORDER_RAW = 65535
    pieces = []
    with open(PUZZLE_CSV) as f:
        size = int(f.readline().strip())
        for idx, line in enumerate(f):
            line = line.strip()
            if not line: continue
            parts = line.split(",")
            def col(s):
                v = int(s.strip(), 2)
                return 0 if v == BORDER_RAW else v
            pieces.append((col(parts[0]), col(parts[1]), col(parts[2]), col(parts[3])))
    return pieces


def rotate(edges, k):
    n, e, s, w = edges
    if k == 0: return (n, e, s, w)
    if k == 1: return (w, n, e, s)
    if k == 2: return (s, w, n, e)
    if k == 3: return (e, s, w, n)


def load_placement(path):
    with open(path) as f:
        d = json.load(f)
    arr = d.get("placement", [])
    out = {}
    for idx, item in enumerate(arr):
        if item is None: continue
        pos = item.get("pos", idx)
        out[pos] = (item["piece_id"], item["rotation"])
    return out


def analyze(name, placement, pieces):
    """Compute all global invariants."""
    print(f"\n=== {name} ===")
    # 1. Sum of rotations mod 4
    rot_sum = sum(rot for pos, (pid, rot) in placement.items())
    print(f"  Σ rotations mod 4: {rot_sum} mod 4 = {rot_sum % 4}")

    # 2. Color-direction histogram: count (color c, world-direction d) pairs
    cd_hist = collections.Counter()  # (color, world_dir) where world_dir ∈ {N=0, E=1, S=2, W=3}
    for pos, (pid, rot) in placement.items():
        rotated = rotate(pieces[pid], rot)
        for d in range(4):
            cd_hist[(rotated[d], d)] += 1
    # Total color count per direction (should equal 256 per direction, since each cell has each direction)
    direction_total = {d: sum(cd_hist[(c, d)] for c in range(23)) for d in range(4)}
    print(f"  Direction totals (should be 256 each): {direction_total}")
    # Border-color count by direction
    border_by_dir = {d: cd_hist.get((0, d), 0) for d in range(4)}
    print(f"  Border-color (0) by direction: {border_by_dir}")
    # In a valid assembly: N=W=64, E=S=...no, on a 16x16 board the perimeter
    # has 64 border-color sides total (16 N + 16 S + 16 E + 16 W). Actually
    # not all of those are border-color since border-pieces have border on
    # 1 side only and corners have border on 2 sides. Total border-color
    # sides facing OUTSIDE = 60 (corners×2=8 + edges×1 = 56? wait, 56 edges
    # have 1 border side, so 56 border-color sides among edge pieces; 4
    # corners have 2 border sides each = 8. Total = 56 + 8 = 64.
    # By direction:
    #   N=0: row 0 (16 cells), all have border on top
    #   S=2: row 15, all have border on bottom
    #   etc.
    # So in canonical orientation each direction should have exactly 16
    # border-color sides facing outward.

    # 3. Most common (c, d) tuples
    print(f"  Top 5 (color, direction): {cd_hist.most_common(5)}")
    print(f"  Bottom 5: {cd_hist.most_common()[-5:]}")

    # 4. Total color budget (sum over direction)
    total_color = collections.Counter()
    for (c, d), n in cd_hist.items():
        total_color[c] += n
    print(f"  Total color counts (top 5): {total_color.most_common(5)}")

    return {
        "rot_sum_mod4": rot_sum % 4,
        "border_by_dir": border_by_dir,
        "cd_hist_size": len(cd_hist),
    }


def main():
    pieces = load_pieces()
    paths = [
        ("McGavin-469", "output/vol-65/mcgavin_469.json"),
        ("local-459-p06", "output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json"),
        ("vol32-458", "output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json"),
        ("vol61-458-s17", "output/vol-61/faithful_sota_20260515T174124/stage3_seed17.json"),
        ("vol61-458-s200", "output/vol-61/faithful_sota_20260515T174124/stage3_seed200.json"),
    ]
    invariants = {}
    for name, p in paths:
        pl = load_placement(p)
        invariants[name] = analyze(name, pl, pieces)

    print(f"\n=== INVARIANT COMPARISON ===")
    print(f"{'board':<25} | rot_sum_mod4 | border_by_dir")
    for name, inv in invariants.items():
        print(f"{name:<25} | {inv['rot_sum_mod4']:<12} | {inv['border_by_dir']}")


if __name__ == "__main__":
    main()
