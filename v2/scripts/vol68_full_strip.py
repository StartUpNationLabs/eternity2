#!/usr/bin/env python3
"""Vol-68 — Full 16-cell strip enumeration via DFS.

Count distinct interior-placement strips (16 cells in a row) by
enumerating piece-rotation choices with:
- All cells use DIFFERENT pieces (piece-uniqueness in the row).
- Adjacent EW-color match.
- (Optional) frame N constraint: top row's N-color = 0 (border).

Output: total valid strips for top row (with N=0 frame constraint).

This is the partition-function for one row of E2. If feasible (< 10^8),
we have a real combinatorial count.
"""

import collections
import csv
import json
import sys
import time
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


def rotate(edges, k):
    n, e, s, w = edges
    if k == 0: return (n, e, s, w)
    if k == 1: return (w, n, e, s)
    if k == 2: return (s, w, n, e)
    if k == 3: return (e, s, w, n)


def piece_kind(edges):
    nb = sum(1 for c in edges if c == 0)
    return {0: "interior", 1: "edge", 2: "corner"}.get(nb)


def main():
    pieces = load_pieces()
    n_pieces = len(pieces)

    # For E2 row 0 (top): cells (0..15), the LEFTMOST is a corner (border-N AND
    # border-W); rightmost is corner (border-N AND border-E); middle 14 are
    # edge pieces (border-N only).
    # Each cell has constraints: outgoing direction toward frame must be border (0).

    # We need to enumerate top-row strips:
    # 4 cells with corner pieces (only 4 candidates per cell, 2 cells at top-row endpoints)
    # Hmm — top row has 2 corner cells (pos 0, 15) + 14 edge cells (pos 1-14).
    # Let me enumerate.

    # All (piece, rotation) tuples that can sit in row 0 cells:
    # - cell 0: needs N=0 AND W=0. Piece must have 2 border sides (corner) AND
    #   in the right rotation.
    # - cells 1-14: needs N=0. Piece is "edge" (1 border side). Rotation forces W non-0.
    # - cell 15: N=0 AND E=0. Corner.

    # Enumerate cell-0 candidates
    cell0 = []  # (piece, rotation, edges=(N,E,S,W))
    cell14 = []  # for cell 15 (rightmost corner)
    edges_cells = []  # for cells 1-14

    for p in range(n_pieces):
        for k in range(4):
            re = rotate(pieces[p], k)
            n, e, s, w = re
            if piece_kind(pieces[p]) == "corner":
                # 2 border sides facing outward
                if n == 0 and w == 0:
                    cell0.append((p, k, re))
                if n == 0 and e == 0:
                    cell14.append((p, k, re))
            elif piece_kind(pieces[p]) == "edge":
                # 1 border side facing N (since top row)
                if n == 0 and e != 0 and s != 0 and w != 0:
                    edges_cells.append((p, k, re))

    print(f"Top-row candidate counts:")
    print(f"  cell 0 (left corner, N=W=0): {len(cell0)}")
    print(f"  cells 1-14 (edges, N=0): {len(edges_cells)}")
    print(f"  cell 15 (right corner, N=E=0): {len(cell14)}")

    # DFS enumerate top-row strips
    # State: (chosen pieces so far, current cell index, EW-match constraint
    # = previous cell's E)
    # Optimization: index edges_cells by their W-color (to match previous E)
    edges_by_W = collections.defaultdict(list)
    for placement in edges_cells:
        p, k, (n, e, s, w) = placement
        edges_by_W[w].append(placement)

    cell14_by_W = collections.defaultdict(list)
    for placement in cell14:
        p, k, (n, e, s, w) = placement
        cell14_by_W[w].append(placement)

    # Enumerate
    count = [0]
    used_pieces = set()
    t0 = time.time()
    early_exit_count = [0]
    LIMIT = 500_000_000  # high cap; we'll report whatever we hit

    def dfs(cell_idx, prev_E):
        if count[0] >= LIMIT:
            return  # bail
        if cell_idx == 15:
            # Place cell 15 (right corner). Must have W = prev_E.
            for placement in cell14_by_W.get(prev_E, []):
                p, k, (n, e, s, w) = placement
                if p in used_pieces: continue
                count[0] += 1
            return
        # Cells 1-14: edges
        for placement in edges_by_W.get(prev_E, []):
            p, k, (n, e, s, w) = placement
            if p in used_pieces: continue
            used_pieces.add(p)
            dfs(cell_idx + 1, e)
            used_pieces.remove(p)

    # Outer loop: cell 0
    for placement in cell0:
        p0, k0, (n0, e0, s0, w0) = placement
        used_pieces.clear()
        used_pieces.add(p0)
        cell0_start = count[0]
        cell0_t0 = time.time()
        dfs(1, e0)
        print(f"  cell0 corner {p0}: added {count[0] - cell0_start} strips, "
              f"{time.time() - cell0_t0:.1f}s, total {count[0]}")
        if time.time() - t0 > 300:  # 5 min cap
            print(f"  (over 300s wall, stopping)")
            break

    print(f"\nTotal valid top-row strips: {count[0]}")
    print(f"Time: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
