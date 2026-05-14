#!/usr/bin/env python3
"""Pairwise Hamming distance across all distinct 457 boards.

A 'cell' matches if piece_id AND rotation match at the same pos.
Lower distance = closer basins; H=0 = byte-identical placements.
"""
import json
from pathlib import Path

PATHS = [
    "output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed7.json",
    "output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed10.json",
    "output/vol-32/RECORD_TIE_457_blackwood_mrv_30min_seed4.json",
    "output/vol-34/t3_signal/REAL_RECORD_TIE_457_vol34_t1signal_seed1.json",
    "output/vol-34/t3_signal/RECORD_TIE_457_vol34_t3_t01_seed1.json",
    "output/vol-35/records/RECORD_TIE_457_vol35_family255_seed1.json",
]


def load_grid(p):
    """Return dict[pos] = (piece_id, rotation)."""
    b = json.load(open(p))
    return {c["pos"]: (c["piece_id"], c["rotation"]) for c in b["placement"]}


def hamming(g1, g2):
    keys = set(g1.keys()) | set(g2.keys())
    return sum(1 for k in keys if g1.get(k) != g2.get(k))


def piece_only_hamming(g1, g2):
    """Hamming ignoring rotation — captures pieces in different slots."""
    keys = set(g1.keys()) | set(g2.keys())
    return sum(1 for k in keys if (g1.get(k) or (None,))[0] != (g2.get(k) or (None,))[0])


def main():
    grids = {Path(p).name: load_grid(p) for p in PATHS}
    names = list(grids.keys())

    print("=== Full Hamming (piece+rotation) ===")
    print(" " * 60 + " ".join(f"{i:4d}" for i in range(len(names))))
    for i, n in enumerate(names):
        row = [hamming(grids[n], grids[names[j]]) for j in range(len(names))]
        print(f"[{i}] {n[:55]:55s} " + " ".join(f"{v:4d}" for v in row))

    print()
    print("=== Piece-only Hamming (ignore rotation) ===")
    for i, n in enumerate(names):
        row = [piece_only_hamming(grids[n], grids[names[j]]) for j in range(len(names))]
        print(f"[{i}] {n[:55]:55s} " + " ".join(f"{v:4d}" for v in row))

    print()
    print("=== Summary ===")
    all_pairs = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            h = hamming(grids[names[i]], grids[names[j]])
            ph = piece_only_hamming(grids[names[i]], grids[names[j]])
            all_pairs.append((i, j, h, ph))
    h_vals = [t[2] for t in all_pairs]
    ph_vals = [t[3] for t in all_pairs]
    print(f"pairs:                 {len(all_pairs)}")
    print(f"hamming (piece+rot):   min={min(h_vals)} max={max(h_vals)} mean={sum(h_vals)/len(h_vals):.1f}")
    print(f"piece-only hamming:    min={min(ph_vals)} max={max(ph_vals)} mean={sum(ph_vals)/len(ph_vals):.1f}")
    print()
    print("Pairs with H == 0 (byte-identical placements):")
    for i, j, h, _ in all_pairs:
        if h == 0:
            print(f"  [{i}] {names[i]} == [{j}] {names[j]}")
    print()
    print("Pairs with H <= 20 (near-clones):")
    for i, j, h, ph in all_pairs:
        if 0 < h <= 20:
            print(f"  H={h} ph={ph}  [{i}] {names[i]}\n         [{j}] {names[j]}")


if __name__ == "__main__":
    main()
