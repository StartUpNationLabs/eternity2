#!/usr/bin/env python3
"""Vol-122 K7 — Interior Sub-Puzzle analysis.

For a given full board, extract the 14×14 interior as a SUB-PUZZLE:
- Interior pieces: 196 pieces.
- Constraint: the OUTWARD-facing colors of border-adjacent interior cells
  must match the inward-facing colors of the border pieces.
- The 56-cell ring at the interior boundary has its colors FIXED by the border.

This is a "puzzle with boundary condition" — solving it independently
of the border gives the maximum achievable interior score for a fixed
border.

Measure on best vol-122 boards (perm0_444, perm3_439, McGavin_469).
"""

from __future__ import annotations
import json
import sys
from collections import Counter
from pathlib import Path


def parse_color(s):
    v = int(s.strip(), 2)
    return 0 if v == 65535 else v

def load_pieces():
    pieces = {}
    with open("../data/puzzles/size_16_official_eternity.csv") as f:
        lines = [l.strip() for l in f if l.strip()]
    pid = 0
    for line in lines[1:]:
        cols = line.split(',')
        if len(cols) >= 4:
            try:
                pieces[pid] = tuple(parse_color(cols[i]) for i in range(4))
                pid += 1
            except ValueError: pass
    return pieces

def rotate(edges, rot):
    return tuple(edges[(i - rot) % 4] for i in range(4))


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} BOARD.json")
        sys.exit(1)
    board_path = Path(sys.argv[1])
    pieces = load_pieces()
    side = 16

    with open(board_path) as f:
        d = json.load(f)
    placed = {e['pos']: (e['piece_id'], e['rotation']) for e in d.get('placement', []) if e is not None}
    print(f"loaded: {board_path.name}, {len(placed)} placed")

    # Border interior-facing colors (= constraint on interior)
    # For each border cell at the inside boundary (row 0/15, col 0/15), record the color it presents to the interior.
    # These become the "boundary condition" for the 14×14 sub-puzzle.

    # 14x14 interior occupies positions where row 1..14, col 1..14.
    # The 14×14's "north boundary" = border cells at row 0, cols 1..14 → their BOTTOM edge.
    # The 14×14's "south boundary" = border cells at row 15, cols 1..14 → their TOP edge.
    # The 14×14's "east boundary" = border cells at row 1..14, col 15 → their LEFT edge.
    # The 14×14's "west boundary" = border cells at row 1..14, col 0 → their RIGHT edge.

    inner_boundary = {}  # (interior_pos, side_facing_boundary) → required_color
    for c in range(1, side - 1):
        # top border cell
        pos = c
        if pos in placed:
            pid, rot = placed[pos]
            edges = rotate(pieces[pid], rot)
            # bottom edge faces interior cell (1, c)
            inner_boundary[(1*side + c, 0)] = edges[2]  # interior cell's TOP side must = border's BOTTOM
    for c in range(1, side - 1):
        # bottom border
        pos = side * (side - 1) + c
        if pos in placed:
            pid, rot = placed[pos]
            edges = rotate(pieces[pid], rot)
            inner_boundary[((side - 2) * side + c, 2)] = edges[0]
    for r in range(1, side - 1):
        # right border
        pos = r * side + (side - 1)
        if pos in placed:
            pid, rot = placed[pos]
            edges = rotate(pieces[pid], rot)
            inner_boundary[(r * side + (side - 2), 1)] = edges[3]
    for r in range(1, side - 1):
        # left border
        pos = r * side
        if pos in placed:
            pid, rot = placed[pos]
            edges = rotate(pieces[pid], rot)
            inner_boundary[(r * side + 1, 3)] = edges[1]

    print(f"\nInterior boundary constraints: {len(inner_boundary)} (cell, side, color)")
    boundary_colors = Counter(c for c in inner_boundary.values())
    print(f"  boundary color distribution: {dict(sorted(boundary_colors.items()))}")

    # Now score the interior:
    # 1. Interior-interior matches (between interior cells).
    # 2. Interior-boundary matches (when interior piece's outward edge matches the boundary color).
    interior_pos = [r * side + c for r in range(1, side - 1) for c in range(1, side - 1)]
    n_interior = len(interior_pos)
    print(f"\nInterior cells: {n_interior} (= 14×14 = 196)")

    # Score interior-interior matches
    ii_matches = 0
    for r in range(1, side - 1):
        for c in range(1, side - 1):
            pos = r * side + c
            if pos not in placed: continue
            pid, rot = placed[pos]
            edges = rotate(pieces[pid], rot)
            # right neighbor
            if c < side - 2 and (npos := pos + 1) in placed:
                npid, nrot = placed[npos]
                nedges = rotate(pieces[npid], nrot)
                if edges[1] == nedges[3] and edges[1] != 0:
                    ii_matches += 1
            # bottom neighbor
            if r < side - 2 and (npos := pos + side) in placed:
                npid, nrot = placed[npos]
                nedges = rotate(pieces[npid], nrot)
                if edges[2] == nedges[0] and edges[2] != 0:
                    ii_matches += 1

    # Score interior-boundary matches
    ib_matches = 0
    for (cell, side_idx), req_color in inner_boundary.items():
        if cell not in placed: continue
        pid, rot = placed[cell]
        edges = rotate(pieces[pid], rot)
        if edges[side_idx] == req_color and edges[side_idx] != 0:
            ib_matches += 1

    bb_matches = 60  # always for valid borders
    print(f"\nMatch decomposition:")
    print(f"  border-border (BB): {bb_matches} (assumed always)")
    print(f"  interior-boundary (IB): {ib_matches} / 56")
    print(f"  interior-interior (II): {ii_matches} / 364")
    total = bb_matches + ib_matches + ii_matches
    print(f"  total: {total}")

    # For comparison, total possible if all matched:
    print(f"\nMax possible: 60 + 56 + 364 = 480")


if __name__ == "__main__":
    main()
