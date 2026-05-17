#!/usr/bin/env python3
"""Vol-122 J7 — Hint-Free Forced-Move detection (HFFM) PoC.

NEW INVENTION: discover FORCED MOVES that the engine's local AC-3 misses.

Logic: for each (color_a, color_b) adjacency-color-pair the puzzle solution
needs, count:
- N_pieces_supporting = number of pieces (with some rotation) that can
  provide BOTH colors on adjacent sides of the piece.
- N_demand = expected number of (color_a, color_b) adjacencies in a
  perfect solution.

If N_pieces_supporting == N_demand for some (a, b), then EVERY piece
supporting (a, b) MUST be used to provide (a, b). The piece's placement
is constrained.

If N_pieces_supporting < N_demand → puzzle is UNSOLVABLE (which we know
isn't the case).

Stronger: for each piece, look at which color-pairs it uniquely provides.
A piece whose UNIQUELY-PROVIDED pair has demand > 0 = FORCED to provide
that pair (= certain rotations/positions are mandatory).

This PoC just measures the structure to see if there's exploitable
forced-move information.
"""

from __future__ import annotations
import sys
from collections import defaultdict, Counter
from pathlib import Path


def parse_color(s):
    v = int(s.strip(), 2)
    return 0 if v == 65535 else v

def load_puzzle(csv_path):
    pieces = []
    with open(csv_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    for line in lines[1:]:
        cols = line.split(',')
        if len(cols) >= 4:
            try:
                pieces.append((parse_color(cols[0]), parse_color(cols[1]),
                               parse_color(cols[2]), parse_color(cols[3])))
            except ValueError: pass
    return pieces

def rotate(edges, rot):
    return tuple(edges[(i - rot) % 4] for i in range(4))


def main():
    puzzle_path = Path(sys.argv[1] if len(sys.argv) > 1 else "../data/puzzles/size_16_official_eternity.csv")
    pieces = load_puzzle(puzzle_path)
    n = len(pieces)
    side = int(n ** 0.5)
    print(f"loaded puzzle: {n} pieces, {side}x{side}")

    # For each piece, all 4 rotations, all 4 sides → (color, opposite_color) on adjacent sides of piece
    # An "L-shape": piece presents color C1 on side S, color C2 on side S+1 (clockwise).
    # The L-shape (C1, C2) can match TWO adjacency:
    #   - With a horizontal neighbor, the piece's "right side" (e.g., S=1) shows C1;
    #     and the piece's "bottom side" (S=2) shows C2 to the cell below.
    # So when we count L-shapes, we count (color on side, color on next-clockwise side).

    # For each ordered (C1, C2), supply = # (piece, rotation, side) yielding C1 on side, C2 on next.
    pair_supply = defaultdict(set)  # (C1, C2) -> set of (pid, rot, side)
    for pid in range(n):
        for rot in range(4):
            e = rotate(pieces[pid], rot)
            for s in range(4):
                c1 = e[s]
                c2 = e[(s + 1) % 4]
                if c1 != 0 and c2 != 0:  # only count interior-interior pairs
                    pair_supply[(c1, c2)].add((pid, rot, s))

    # Demand: count actual (c1, c2) pairs in a TARGET solution... but we don't have a perfect solution.
    # Instead: count THEORETICAL demand = # adjacent-pair slots on the 16x16 board.
    # Each interior cell has 4 (Ci, Ci+1) adjacency pairs of itself (top-right corner,
    # right-bottom corner, etc.). For each cell with 4 sides, there are 4 (corner) pairs.
    # The 256 cells contribute 256*4 = 1024 corner-pairs.
    # But this counts each "L-shape" once per cell. The PUZZLE needs a perfect assignment.

    # For a UNIQUE forced-move analysis, we want pairs (c1, c2) such that
    # supply_p (= len(pair_supply[(c1, c2)])) is SMALL.

    # Count distribution
    print("\nDistribution of pair_supply sizes:")
    sizes = Counter(len(v) for v in pair_supply.values())
    print(f"  total distinct pairs: {len(pair_supply)}")
    for sz in sorted(sizes):
        print(f"  supply = {sz}: {sizes[sz]} pairs")

    # Find pairs with smallest supply (= most constrained)
    print("\nMost-constrained color pairs (smallest supply):")
    sorted_pairs = sorted(pair_supply.items(), key=lambda kv: len(kv[1]))
    for (c1, c2), supporters in sorted_pairs[:10]:
        sup_pids = sorted(set(p for (p, r, s) in supporters))
        print(f"  pair ({c1:2d}, {c2:2d}): {len(supporters)} (piece, rot, side) → {len(sup_pids)} distinct pieces: {sup_pids[:5]}{'...' if len(sup_pids)>5 else ''}")

    # Look at SINGLETON pieces: pieces that uniquely provide some color pair (in any rotation)
    piece_provides = defaultdict(set)  # pid -> set of (c1, c2) it can provide
    for (c1, c2), supporters in pair_supply.items():
        for (pid, rot, s) in supporters:
            piece_provides[pid].add((c1, c2))

    # For each pid, find color pairs that ONLY THIS PIECE provides
    print("\nPieces with UNIQUE (cannot be replaced) color-pair provision:")
    unique_provision = defaultdict(list)
    pair_to_pieces = defaultdict(set)
    for (c1, c2), supporters in pair_supply.items():
        for (pid, _, _) in supporters:
            pair_to_pieces[(c1, c2)].add(pid)

    forced_pieces = 0
    for pid in range(n):
        unique_pairs = [pair for pair in piece_provides[pid] if len(pair_to_pieces[pair]) == 1]
        if unique_pairs:
            forced_pieces += 1
            if forced_pieces <= 10:
                print(f"  piece {pid}: edges={pieces[pid]}, unique pairs: {unique_pairs[:5]}")
    print(f"\nTotal pieces with at least one uniquely-provided color pair: {forced_pieces}/{n}")

    # Pairs with supply==1 means: only one (piece, rot, side) can provide that pair.
    # That's a HARD constraint if the pair is REQUIRED by the puzzle.
    singleton_pairs = [p for p, v in pair_supply.items() if len(v) == 1]
    print(f"Singleton (supply==1) color pairs: {len(singleton_pairs)}")

    # Check what these singletons demand: we don't know the exact perfect solution, but
    # ANY perfect-tiling solution must use some of these pairs. The question is
    # whether ALL of them must be used.
    # For canonical E2: 480 internal adjacencies. Average pair_supply ~ 11.7 (per K3).
    # 269 distinct pairs. demand ~ 480 - 56 (border-interior) = 424 interior-interior pairs.


if __name__ == "__main__":
    main()
