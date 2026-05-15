#!/usr/bin/env python3
"""Vol-68 — Strip transfer matrix analysis on canonical E2.

For each pair of "S-color row signatures" (16-tuple of bottom-side
colors of a row of cells), count how many INTERIOR piece arrangements
produce that signature in the row below (i.e., how many ways the
next row's piece-N-colors can match these S-colors).

The full transfer matrix is 23^16 × 23^16 = astronomical. But we
only care about EXISTING bottom-side signatures from valid pieces.

Method:
1. For each non-border piece, enumerate its 4 rotations.
2. For each rotation, record (N-color, S-color, E-color, W-color).
3. The set of available N-colors for row r+1 cells = the supply we
   draw from.
4. Compute: given the S-signature of row r, what's the marginal
   number of row-r+1 arrangements?

For tractability, work on a 2-piece-wide strip first: just 2 cells
side-by-side. Their inter-cell color must match (EW), AND their N+S
colors form the strip's signature.
"""

import collections
import csv
import json
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


def main():
    pieces = load_pieces()
    n_pieces = len(pieces)

    # Non-border pieces (interior set: pieces with NO border-color side)
    # For strip analysis, we want interior pieces only (no frame constraints).
    interior_pieces = [i for i, p in enumerate(pieces)
                       if all(c != 0 for c in p)]
    print(f"Interior pieces: {len(interior_pieces)}")

    # Enumerate (piece, rotation) for each interior piece × 4 rotations
    # Then collect (N, E, S, W) tuples
    placements = []
    for p in interior_pieces:
        for k in range(4):
            placements.append((p, k, rotate(pieces[p], k)))
    print(f"Interior placements (piece × rotation): {len(placements)}")

    # Question 1: How many DISTINCT (N, S) color pairs occur?
    ns_pairs = collections.Counter()
    for p, k, (n, e, s, w) in placements:
        ns_pairs[(n, s)] += 1
    print(f"\nDistinct (N, S) color pairs from interior placements: {len(ns_pairs)}")
    print(f"  Top 10 most common: {ns_pairs.most_common(10)}")

    # Question 2: Per-color, distribution of pieces with given S color
    # (we want to enumerate piece-rotations that can sit BELOW a cell
    # whose S color is fixed)
    by_S = collections.defaultdict(list)
    for placement in placements:
        p, k, (n, e, s, w) = placement
        # If this piece-rotation sits BELOW some cell, its N color must
        # equal that cell's S color.
        by_S[n].append(placement)
    print(f"\nFor a row's S-signature, supply of next-row pieces by N-color:")
    print(f"  N-color | supply")
    for c in sorted(by_S.keys()):
        print(f"  {c:>7} | {len(by_S[c]):>6} placements")

    # Question 3: 2-cell strip extension. Given top row has 2 cells with
    # S-colors (s1, s2), how many bottom-row 2-cell pairs (with EW match)
    # are compatible?
    # For top S-colors (s1, s2), bottom-row piece-pair (Pa, ra), (Pb, rb)
    # such that:
    #   Pa's N color = s1
    #   Pb's N color = s2
    #   Pa's E color = Pb's W color (horizontal match)
    # AND Pa, Pb are distinct pieces (can't use same piece twice).
    print(f"\n2-cell strip extension count (sample over 10 top-row pairs):")
    print(f"  (s1, s2) | # valid bottom-pairs")
    # Pick the 10 most common (n, s) pairs as our test S-pairs
    common_ns = [k for k, _ in ns_pairs.most_common(10)]
    for ns1 in common_ns[:5]:
        for ns2 in common_ns[:5]:
            s1 = ns1[1]; s2 = ns2[1]
            count = 0
            for (p1, k1, e1) in by_S[s1]:
                for (p2, k2, e2) in by_S[s2]:
                    if p1 == p2: continue
                    # e1 = (n1, e1_col, s1_col, w1); e2 = (n2, e2_col, s2_col, w2)
                    if e1[1] == e2[3]:  # E of Pa = W of Pb
                        count += 1
            if count > 0:
                print(f"  ({s1}, {s2}) | {count}")

    # Question 4: distribution of 2-cell strip-extension counts
    # over all distinct (s1, s2) S-pairs
    print(f"\nFull (s1, s2) distribution of 2-cell strip counts:")
    counts_dist = collections.Counter()
    n_zero = 0; n_nonzero = 0
    for s1 in by_S.keys():
        for s2 in by_S.keys():
            count = 0
            for (p1, k1, e1) in by_S[s1]:
                for (p2, k2, e2) in by_S[s2]:
                    if p1 == p2: continue
                    if e1[1] == e2[3]:
                        count += 1
            if count == 0: n_zero += 1
            else:
                n_nonzero += 1
                counts_dist[count] += 1
    print(f"  Total (s1, s2) pairs tested: {n_zero + n_nonzero}")
    print(f"  (s1, s2) with ZERO valid extensions: {n_zero}")
    print(f"  Median count among non-zero: {sorted(counts_dist.elements())[len(list(counts_dist.elements())) // 2] if counts_dist else 0}")
    print(f"  Max count: {max(counts_dist.keys()) if counts_dist else 0}")


if __name__ == "__main__":
    main()
