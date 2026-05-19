#!/usr/bin/env python3
"""V132-T2 — Build density table across all our puzzles + correlate with scaling-curve results."""

from __future__ import annotations
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load_puzzle_csv(csv_path):
    BORDER_RAW = 65535
    pieces = []
    with open(csv_path) as f:
        size = int(f.readline().strip())
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split(",")
            sides = []
            for s in parts[:4]:
                v = int(s.strip(), 2)
                sides.append(0 if v == BORDER_RAW else v)
            pieces.append(tuple(sides))
    return size, pieces


def measure(size, pieces):
    from collections import Counter
    P = len(pieces)
    R = 4
    n_int = (size - 1) * size + size * (size - 1)
    color_freq = Counter()
    for p in pieces:
        for r in range(R):
            n_p, e_p, s_p, w_p = p
            rotated = [(n_p, e_p, s_p, w_p), (e_p, s_p, w_p, n_p),
                       (s_p, w_p, n_p, e_p), (w_p, n_p, e_p, s_p)][r]
            for c in rotated:
                color_freq[c] += 1
    total = P * R * 4
    color_prob = {c: cnt/total for c, cnt in color_freq.items()}
    p_match = sum(p*p for c, p in color_prob.items() if c != 0)
    exp_match = n_int * p_match
    return {
        "size": size, "n_pieces": P, "n_interior_edges": n_int,
        "n_colors": max(color_freq) + 1,
        "p_match_random": p_match,
        "expected_matched_random": exp_match,
        "expected_matched_pct": exp_match / n_int * 100,
    }


def main():
    # Canonical
    puzzles = [
        ("canonical_16x16/22", REPO.parent / "data/puzzles/size_16_official_eternity.csv"),
    ]
    # Generated scaling suite (one seed each)
    for size, n_colors in [(6,4),(7,5),(8,6),(10,8),(12,10),(14,12)]:
        p = REPO / f"output/vol-131/scaling_bench_20260519T123004/puzzle_s{size}_c{n_colors}_seed42.csv"
        if p.exists():
            puzzles.append((f"{size}x{size}/c{n_colors}", p))

    # Vol-131 best ALNS percentages (from the scaling bench)
    # size → median pct
    alns_pct = {6: 100.0, 7: 97.6, 8: 92.9, 10: 91.1, 12: 86.4, 14: 81.6}

    rows = []
    print(f"\n{'puzzle':>22} {'pieces':>7} {'colors':>6} {'edges':>5} {'p_match':>8} {'exp%':>6} {'ALNS%':>6} {'gap':>6}", flush=True)
    for name, path in puzzles:
        size, pieces = load_puzzle_csv(path)
        m = measure(size, pieces)
        alns = alns_pct.get(m['size'], None)
        if m['size'] == 16:
            alns_canonical = 461 / 480 * 100  # our standing record
            alns = alns_canonical
        gap = (alns - m['expected_matched_pct']) if alns else None
        print(f"{name:>22} {m['n_pieces']:>7} {m['n_colors']:>6} "
              f"{m['n_interior_edges']:>5} {m['p_match_random']:>8.4f} "
              f"{m['expected_matched_pct']:>5.1f}% "
              f"{alns if alns else 0:>5.1f}% "
              f"{gap if gap is not None else 0:>+5.1f}", flush=True)
        rows.append({"name": name, **m, "alns_best_pct": alns})

    # Save.
    out_path = REPO / "output/vol-131/density_comparison.json"
    with open(out_path, "w") as f:
        json.dump(rows, f, indent=2)
    print(f"\nWrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
