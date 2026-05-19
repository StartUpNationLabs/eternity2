#!/usr/bin/env python3
"""V132-T1 — Constraint-density characterization.

Define and measure several density metrics for an Eternity-II piece
set:

1. **rotated edge-color distribution**: for each color C, count
   how many (piece, rotation, side) triples produce color C on that
   side. With 4 rotations per piece, this is just total
   occurrences (each piece's color is on each side exactly once
   across rotations). For canonical E2 we have: 5 rare (k=24/96),
   5 medium (k=48/192), 12 common (k=50/200), 1 border (k=64/256).

2. **bipartite-matching feasibility density**: for each (cell, side)
   slot, the number of distinct (piece, rotation) combinations whose
   side-color matches each color. High density ⇒ many candidates per
   slot ⇒ easier search.

3. **piece-pair adjacency density**: for each color C, the bipartite
   matching graph between pieces with C on E sides and pieces with
   C on W sides (similarly N-S). Smaller graph ⇒ more constrained.

4. **expected-matched-edges at random placement**: a baseline
   prediction. If we place pieces uniformly at random with random
   rotations, expected matched edges = (#interior_edges) ×
   sum_C P(C)^2 where P(C) is the probability a random
   piece-side-rotation is color C.

The hypothesis (vol-131 finding): canonical E2 has LOWER constraint
density than generated 14×14/c12, which explains its higher %
matched at the standing record.
"""

from __future__ import annotations
import argparse
import json
import sys
from collections import Counter, defaultdict
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


def measure_density(size, pieces):
    P = len(pieces)
    R = 4
    n_cells = size * size
    n_interior_edges = (size - 1) * size + size * (size - 1)
    BORDER = 0

    # Metric 1: color occurrence distribution.
    # For each color C, how many piece-sides carry C? In raw (no rotation):
    raw_color_counts = Counter()
    for p in pieces:
        for side_color in p:
            raw_color_counts[side_color] += 1
    n_colors = max(raw_color_counts) + 1
    # With rotation: same counts (rotation permutes sides, doesn't change colors).

    # Metric 2: piece-multiplicity per color. How many distinct pieces
    # have color C on ANY side?
    piece_carries_color = defaultdict(set)
    for pid, p in enumerate(pieces):
        for c in p:
            piece_carries_color[c].add(pid)

    # Metric 3: candidate density per (side, color) slot.
    # For a given side (N/E/S/W) at a cell, when we want a piece-rotation
    # whose chosen-side color = C, how many candidates are there?
    # Each piece P, in 4 rotations, presents (P[0], P[1], P[2], P[3]) on
    # (N,E,S,W) respectively for r=0, etc. So for a fixed side and color C,
    # count piece-rotation pairs (P, r) where rotated(P, r)[side]==C.
    # By symmetry this is the same across sides; just count total.
    n_pr_carrying_color = Counter()  # color → # (piece, rotation) pairs where SOME side is C
    n_pr_at_side_carrying_color = defaultdict(Counter)  # side → color → # (p, r) pairs
    for pid, p in enumerate(pieces):
        for r in range(R):
            rotated = (p[(0 - r) % 4], p[(1 - r) % 4], p[(2 - r) % 4], p[(3 - r) % 4])
            # Actually rotate properly:
            # Rotation by r quarter-turns: side `s` after rotation = original side `(s - r) mod 4`.
            # Hmm let me use a standard rotation.
            n, e, s, w = p
            rotated = [(n, e, s, w), (e, s, w, n), (s, w, n, e), (w, n, e, s)][r]
            for side, color in enumerate(rotated):
                n_pr_at_side_carrying_color[side][color] += 1
                # Also accumulate the total across sides per color.

    # Metric 4: probability of match at a random interior edge.
    # If side_north_color and side_south_color (for a horiz adjacency)
    # are i.i.d. samples from the marginal P(color), then P(match) =
    # sum_C P(C)^2.
    # Marginal: total color-side count / (P*R*4) = sum over all (p, r, side).
    total_side_slots = P * R * 4
    color_freq = Counter()
    for pid, p in enumerate(pieces):
        for r in range(R):
            n_p, e_p, s_p, w_p = p
            rotated = [(n_p, e_p, s_p, w_p), (e_p, s_p, w_p, n_p),
                       (s_p, w_p, n_p, e_p), (w_p, n_p, e_p, s_p)][r]
            for c in rotated:
                color_freq[c] += 1
    color_prob = {c: count / total_side_slots for c, count in color_freq.items()}
    p_match_random = sum(p * p for c, p in color_prob.items() if c != BORDER)
    # Border match (color=0 ON border = required, but border slot is
    # exterior so doesn't count as interior edge match). So exclude
    # color 0 from match.

    # Expected matched edges at random complete placement (uniform random
    # piece-position with random rotations, ignoring uniqueness):
    expected_matched_random = n_interior_edges * p_match_random

    # Metric 5: piece-uniqueness factor. The matched count under random
    # placement WITH uniqueness is harder; ignore for now.

    # Metric 6: rare-color fraction. Fraction of piece-sides that are
    # rare (count ≤ small threshold).
    n_total_sides = P * 4  # raw piece-sides (no rotation, since rotation just permutes)
    raw_color_freq = {c: cnt / n_total_sides for c, cnt in raw_color_counts.items()}
    rare_threshold = 24  # canonical rare ~24
    rare_colors = [c for c, n in raw_color_counts.items() if c != BORDER and n <= rare_threshold]
    n_rare_sides = sum(raw_color_counts[c] for c in rare_colors)
    rare_side_fraction = n_rare_sides / n_total_sides

    out = {
        "size": size,
        "n_pieces": P,
        "n_interior_edges": n_interior_edges,
        "n_colors": n_colors,
        "raw_color_counts": dict(raw_color_counts),
        "raw_color_freq": {str(c): v for c, v in raw_color_freq.items()},
        "color_freq_rotated": {str(c): v for c, v in color_prob.items()},
        "p_match_random": p_match_random,
        "expected_matched_random": expected_matched_random,
        "expected_matched_pct": expected_matched_random / n_interior_edges * 100,
        "rare_colors": rare_colors,
        "n_rare_sides": n_rare_sides,
        "rare_side_fraction": rare_side_fraction,
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", type=str, required=True)
    args = ap.parse_args()
    csv_path = Path(args.puzzle)
    size, pieces = load_puzzle_csv(csv_path)
    res = measure_density(size, pieces)
    print(f"\n=== {csv_path.name} ===", flush=True)
    print(f"  size={res['size']}×{res['size']}  pieces={res['n_pieces']}", flush=True)
    print(f"  interior_edges={res['n_interior_edges']}  colors={res['n_colors']}", flush=True)
    print(f"  raw_color_counts: {res['raw_color_counts']}", flush=True)
    print(f"  rare_colors: {res['rare_colors']}", flush=True)
    print(f"  rare_side_fraction: {res['rare_side_fraction']:.4f}", flush=True)
    print(f"  p_match_random: {res['p_match_random']:.4f}", flush=True)
    print(f"  expected_matched_random: {res['expected_matched_random']:.1f} "
          f"({res['expected_matched_pct']:.1f}%)", flush=True)
    out_path = csv_path.parent / f"density_{csv_path.stem}.json"
    with open(out_path, "w") as f:
        json.dump(res, f, indent=2)
    print(f"  Wrote {out_path}", flush=True)
    return res


if __name__ == "__main__":
    main()
