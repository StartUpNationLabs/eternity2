#!/usr/bin/env python3
"""V127-T2 — CONCRETION step 2: rare-color forced pairings.

Per V127-T1 finding: all 120 rare-color slots (colors 1-5, 24 each) are on
the BORDER PIECES (60 = 4 corners + 56 edges). Interior pieces have 0 rare
edges.

So CONCRETION's first wave operates on BORDER PIECES. For each rare color C:
- Identify the (border_piece, side) occurrences where side carries color C.
- Each rare color has 24 occurrences → forms 12 matched-adjacency pairings
  in any solution.
- The number of pairings is finite. Enumerate them. Each pairing IMPLIES a
  forced piece-pair adjacency (with rotation freedom).

Output: per rare color, the set of FORCED pair candidates.
"""

from __future__ import annotations
import json
import sys
import time
from pathlib import Path
from collections import defaultdict, Counter
from itertools import combinations

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


def main():
    csv_path = REPO.parent / "data/puzzles/size_16_official_eternity.csv"
    size, pieces = load_puzzle_csv(csv_path)
    print(f"Puzzle: {csv_path.name}  pieces={len(pieces)}", flush=True)

    # Color → occurrences
    color_to_occs = defaultdict(list)
    for pid, (N, E, S, W) in enumerate(pieces):
        for side_idx, c in enumerate([N, E, S, W]):
            color_to_occs[c].append((pid, side_idx))

    rare_colors = [c for c, occs in color_to_occs.items() if c != 0 and len(occs) <= 24]
    print(f"\nRare colors: {sorted(rare_colors)} (k={[len(color_to_occs[c]) for c in sorted(rare_colors)]})", flush=True)

    # For each rare color, the 24 occurrences. In a solution, each pair of
    # occurrences gets matched (i.e., sits across a shared edge). So we need
    # to count the number of legal pair-matchings.
    # But "legal" here means: the two (piece, side) participating in a pair
    # must be at neighboring positions in the puzzle, with appropriate side
    # orientations. Without knowing the board layout we can only count
    # piece-pair POSSIBILITIES not POSITIONAL constraints.

    # Step 1: for each rare color, count which pieces have it on which sides.
    print(f"\nPer rare color, piece-side multiset:", flush=True)
    for c in sorted(rare_colors):
        occs = color_to_occs[c]
        # How many pieces have this color on N? on E? on S? on W?
        side_counts = Counter(side for _, side in occs)
        # How many pieces have this color exactly once? twice? three times?
        piece_color_count = Counter()
        for pid, side in occs:
            piece_color_count[pid] += 1
        piece_count_dist = Counter(piece_color_count.values())
        print(f"  c={c}: k={len(occs)}", flush=True)
        print(f"    side distribution: N={side_counts[0]} E={side_counts[1]} S={side_counts[2]} W={side_counts[3]}", flush=True)
        print(f"    piece-color-count distribution: {dict(piece_count_dist)}", flush=True)
        # Pieces with 2+ occurrences of same rare color are special.
        doubles = [pid for pid, cnt in piece_color_count.items() if cnt >= 2]
        if doubles:
            print(f"    {len(doubles)} pieces have color {c} on 2+ sides: {doubles[:10]}", flush=True)

    # Cross-color: pieces with multiple rare colors (any).
    rare_set = set(rare_colors)
    pieces_with_n_rare = defaultdict(list)  # n_rare_sides → list of (pid, sides)
    for pid, sides in enumerate(pieces):
        n_rare = sum(1 for s in sides if s in rare_set)
        if n_rare > 0:
            pieces_with_n_rare[n_rare].append((pid, sides))

    print(f"\nPieces with 1+ rare sides:", flush=True)
    for n in sorted(pieces_with_n_rare.keys()):
        ps = pieces_with_n_rare[n]
        print(f"  {n} rare side(s): {len(ps)} pieces", flush=True)
    # Show the most-rare pieces.
    if 3 in pieces_with_n_rare:
        print(f"\n  3-rare-side pieces:", flush=True)
        for pid, sides in pieces_with_n_rare[3]:
            print(f"    pid={pid} sides={sides}", flush=True)
    if 2 in pieces_with_n_rare:
        print(f"\n  2-rare-side pieces (first 20 of {len(pieces_with_n_rare[2])}):", flush=True)
        for pid, sides in pieces_with_n_rare[2][:20]:
            print(f"    pid={pid} sides={sides}", flush=True)

    # Pairing analysis: a piece P with rare color C on side s pairs ONLY with
    # another (piece, side) carrying color C and at a compatible geometry.
    # The "compatible geometry" is the puzzle's adjacency graph — but without
    # placement, we can only enumerate POTENTIAL pairings: any (p1, s1) with
    # (p2, s2) where colors match and p1 ≠ p2.
    # For rare color C with k=24: each occurrence pairs with one of the other
    # 23 (different piece) → 23×22×... possibilities. But the pair-matching
    # structure is a perfect matching in a graph with 24 vertices.
    # Number of perfect matchings on K24 (the worst case if all pairs were
    # legal): 24! / (12! · 2^12) ≈ 7.9 × 10^9. Too many to enumerate.
    #
    # The cleanest filter: NEIGHBORING SIDES. For a piece with side s carrying
    # color C, the piece at the matching position has the OPPOSITE side
    # (s+2 mod 4 with appropriate rotation) carrying C. So the matching graph
    # is BIPARTITE — split (pid, side) occurrences by which "outward direction"
    # the side points after potential rotation:
    #   - Side N (0) points UP → matches side S (2) pointing DOWN of a piece
    #     placed BELOW (well, above in matrix-row terms).
    # But since pieces can rotate, every side can point in every direction.
    # → the "geometry filter" without rotation freezing doesn't apply.
    #
    # Conclusion: in the CANONICAL E2 piece set, rare-color pairings alone
    # produce TOO MANY candidate matchings for CONCRETION at the piece-pair
    # level. We need to compose rare-color constraints with ROTATION-fixing.

    # Save inventory.
    out_dir = REPO / "output/vol-127"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "rare_pairings_analysis.json"
    with open(out_path, "w") as f:
        json.dump({
            "rare_colors": sorted(rare_colors),
            "color_occs": {str(c): [list(t) for t in color_to_occs[c]] for c in rare_colors},
            "pieces_with_n_rare_sides": {
                str(n): [[pid, list(sides)] for pid, sides in ps]
                for n, ps in pieces_with_n_rare.items()
            },
        }, f, indent=2)
    print(f"\nWrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
