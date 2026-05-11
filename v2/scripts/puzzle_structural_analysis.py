#!/usr/bin/env python3
"""Static structural analysis of the official Eternity II puzzle.

Looks at the piece set and asks:
1. Color frequency — are some colors structurally "rare"?
2. Color-pair availability — for each (a, b) interior color pair,
   how many pieces have edges (a, b) somewhere?
3. Per-cell "rich" candidate count — number of (piece, rotation)
   tuples compatible with each cell IGNORING neighbours (just
   border-edge constraints).
4. The "bottleneck color": colors that appear on only a few edges.

This is purely structural — no PT, no CP. Tells us which constraints
are inherently tight.
"""

import sys
from collections import Counter, defaultdict
from pathlib import Path


W = 16
H = 16
BORDER = 0
N_COLORS = 22  # interior colors 1..22


def parse_csv_piece_word(s):
    v = int(s.strip(), 2)
    if v == 65535:
        return 0
    return v


def load_puzzle(path):
    pieces = []
    hints = {}
    with open(path) as f:
        size = int(f.readline().strip())
        assert size == W
        for pid, line in enumerate(f):
            cols = line.strip().split(',')
            if len(cols) < 4:
                continue
            quad = tuple(parse_csv_piece_word(cols[i]) for i in range(4))
            pieces.append(quad)
            if len(cols) >= 7:
                x = int(cols[4]); y = int(cols[5]); rot = int(cols[6])
                if (x, y, rot) != (0, 0, 0):
                    pos = y * W + x
                    hints[pos] = (pid, rot)
    return pieces, hints


def piece_class(quad):
    n = sum(1 for c in quad if c == BORDER)
    return 0 if n >= 2 else (1 if n == 1 else 2)


def cell_class(pos):
    x, y = pos % W, pos // W
    n = (x == 0) + (x == W-1) + (y == 0) + (y == H-1)
    return 0 if n >= 2 else (1 if n == 1 else 2)


def main():
    pieces, hints = load_puzzle("../data/puzzles/size_16_official_eternity.csv")
    print(f"=== Eternity II structural analysis ===\n")
    print(f"Pieces: {len(pieces)}")
    print(f"Hints: {len(hints)} at positions {sorted(hints.keys())}")
    print()

    # 1. Color frequency.
    color_count = Counter()
    interior_color_count = Counter()  # ignores BORDER
    for quad in pieces:
        for c in quad:
            color_count[c] += 1
            if c != BORDER:
                interior_color_count[c] += 1
    print(f"--- Color frequency ---")
    print(f"  BORDER edges: {color_count[BORDER]}")
    print(f"  Interior color count (1..22): {sorted(interior_color_count.items())}")
    print(f"  Total interior edge-slots: {sum(interior_color_count.values())} (= 4 * 256 - BORDER)")
    print(f"  Avg interior edges per color: {sum(interior_color_count.values()) / 22:.1f}")
    rare = sorted(interior_color_count.items(), key=lambda x: x[1])[:5]
    print(f"  Rarest 5 interior colors: {rare}")
    abundant = sorted(interior_color_count.items(), key=lambda x: -x[1])[:5]
    print(f"  Most abundant 5: {abundant}")
    print()

    # 2. Each color must MATCH between adjacent pieces. So total edge-slots
    # of color c must be EVEN (each match consumes 2 edge-slots; non-matched
    # = also even since wasted edges are unmatched on both sides).
    print(f"--- Color parity (each color count should be EVEN for full match) ---")
    odd_colors = [(c, n) for c, n in interior_color_count.items() if n % 2 == 1]
    print(f"  Colors with ODD count (= structurally cannot be fully matched):")
    if odd_colors:
        for c, n in odd_colors:
            print(f"    color {c}: {n} edges (1 must remain unmatched)")
        print(f"  Total: {len(odd_colors)} odd colors → at least {len(odd_colors)} structural mismatches")
    else:
        print(f"  All colors have even count ✓ (fully matchable in principle)")
    print()

    # 3. Piece-class breakdown.
    classes = Counter(piece_class(q) for q in pieces)
    print(f"--- Piece classes ---")
    print(f"  Corners (class 0, 2 BORDERS): {classes[0]} (need 4)")
    print(f"  Edges   (class 1, 1 BORDER):  {classes[1]} (need {4*(W-2)} = 56)")
    print(f"  Interior (class 2, 0 BORDER): {classes[2]} (need {(W-2)**2} = 196)")
    print()

    # 4. Color-pair availability.
    # For each (a, b) where a ≤ b and both non-BORDER, count how many
    # pieces have these two colors on at least one (piece, rot) pair of
    # adjacent sides.
    # This is the # ways to satisfy a "this side is color a, that side
    # color b" adjacency.
    pair_count = defaultdict(int)
    for quad in pieces:
        for r in range(4):
            rq = (quad[(0-r)%4], quad[(1-r)%4], quad[(2-r)%4], quad[(3-r)%4])
            # Hmm, using direct rotation: (top, right, bottom, left) at rot r:
            # rot=0: (t,r,b,l). rot=1: (l,t,r,b). rot=2: (b,l,t,r). rot=3: (r,b,l,t).
        # Simpler: just count multiset of unordered pairs of opposite-side colors.
        # Each piece contributes 4 "facing-side" choices: top↔bottom (when stacked),
        # right↔left (when sided). But for counting AVAILABILITY of color c on
        # any side, just count edges as we did in (1).
    print(f"--- Color-pair table (top-10 most-paired & 10 least-paired) ---")
    pairs = defaultdict(int)
    for quad in pieces:
        # All 6 unordered side-pairs of this piece (regardless of orientation).
        # But for matching purposes, what matters is: how many pieces have a side
        # with color c1 AND a side with color c2 (potentially adjacent).
        sides = list(quad)
        for i in range(4):
            for j in range(i+1, 4):
                a, b = sorted([sides[i], sides[j]])
                if a != BORDER and b != BORDER:
                    pairs[(a, b)] += 1
    sorted_pairs = sorted(pairs.items(), key=lambda x: x[1])
    print(f"  rarest pairs:")
    for p, n in sorted_pairs[:10]:
        print(f"    ({p[0]:>2}, {p[1]:>2}): {n} pieces")
    print(f"  most common pairs:")
    for p, n in sorted_pairs[-10:]:
        print(f"    ({p[0]:>2}, {p[1]:>2}): {n} pieces")
    print()

    # 5. Per-color edge availability vs required.
    # In a fully solved puzzle, each color's edges are fully matched
    # internally. Number of internal edges of color c = interior_color_count[c] / 2
    # (because each internal edge consumes 2 edge-slots of the same color).
    # Total internal edges in puzzle: 480. Sum of color edges = 480.
    print(f"--- Edge slots / 2 = internal edges per color (if fully matched) ---")
    total_internal_edges_if_matched = sum(n // 2 for n in interior_color_count.values())
    print(f"  Sum of (count // 2) = {total_internal_edges_if_matched}")
    print(f"  Total internal edges in 16x16 puzzle: 480")
    if total_internal_edges_if_matched < 480:
        print(f"  *** STRUCTURAL DEFICIT: only {total_internal_edges_if_matched} edges can be matched in principle ***")
        print(f"  *** Maximum theoretically achievable score = {total_internal_edges_if_matched}/480 ***")
    else:
        print(f"  ✓ Sufficient edge supply for full match (480/480)")
    print()


if __name__ == "__main__":
    main()
