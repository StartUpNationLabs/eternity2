#!/usr/bin/env python3
"""Vol-72 — NS-1 Δ-invariant correctly implemented (uses v11_ns1_verify defs).

Δ correlates with score:
- 480 → Δ = 0 (only on non-canonical 480 boards)
- 469 → Δ = 1 (McGavin + NEW-469 near-twin swap)
- 459 → Δ = 2 (local-459-p06)
- 458 → Δ = 3-4 (vol-32, vol-61)

Lower Δ ⇔ better border-interior match ⇔ higher score (correlation).

Implication: a search algorithm minimizing Δ during partial-board
construction would bias toward high-score basins.
"""
import sys
sys.path.insert(0, 'scripts')
from v11_ns1_verify import (
    cell_class, border_facing_colors, edge_piece_inward_colors
)
import json
import csv
from collections import Counter
from pathlib import Path


def load_pieces():
    BORDER_RAW = 65535
    pieces = []
    with open("../data/puzzles/size_16_official_eternity.csv") as f:
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


def rotate(e, k):
    n, e_, s, w = e
    if k == 0: return (n, e_, s, w)
    if k == 1: return (w, n, e_, s)
    if k == 2: return (s, w, n, e_)
    if k == 3: return (e_, s, w, n)


def quads_from_placement(path, pieces):
    out = [(0, 0, 0, 0)] * 256
    with open(path) as f: d = json.load(f)
    for idx, item in enumerate(d['placement']):
        if item is None: continue
        pos = item.get('pos', idx)
        out[pos] = rotate(pieces[item['piece_id']], item['rotation'])
    return out


def compute_delta(quads):
    edge_inward = edge_piece_inward_colors(quads)
    A = Counter(edge_inward.values())
    facing = border_facing_colors(quads)
    B = Counter(facing.values())
    delta = sum(abs(A.get(c, 0) - B.get(c, 0)) for c in set(A) | set(B)) // 2
    return delta


def main():
    pieces = load_pieces()
    paths = {
        "McGavin-469": "output/vol-65/mcgavin_469.json",
        "NEW-469-near-twin": "output/vol-68/NEW_469_BOARDS/NEW_469_swap_pieces_234_235_at_pos_73_75.json",
        "local-459-p06": "output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json",
        "vol-32-458": "output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json",
        "vol-61-s17": "output/vol-61/faithful_sota_20260515T174124/stage3_seed17.json",
        "vol-61-s200": "output/vol-61/faithful_sota_20260515T174124/stage3_seed200.json",
    }
    print(f"{'name':<25} | {'score':>5} | {'Δ':>3}")
    for name, p in paths.items():
        if not Path(p).exists(): continue
        quads = quads_from_placement(p, pieces)
        delta = compute_delta(quads)
        matched = json.load(open(p)).get('matched')
        print(f"{name:<25} | {matched:>5} | {delta:>3}")


if __name__ == "__main__":
    main()
