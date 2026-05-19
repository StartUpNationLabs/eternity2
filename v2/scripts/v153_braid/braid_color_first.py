#!/usr/bin/env python3
"""V153 BRAID — color-first search.

Branch on EDGE COLORS, not pieces. For each edge of the 16x16 grid:
- Internal edges: assign a color from 1..22.
- Boundary edges: BORDER (0).

Total edges: 480 internal + 64 boundary = 544.
Variables to assign: 480 internal colors.
Domain: 22 colors each.
Raw search: 22^480 — astronomical.

Pruning: at any partial assignment, check that the pieces required to
fill cells with assigned-on-all-4-sides are available in the inventory.

Algorithm:
  1. Assign internal edges in some order (e.g., row-major edges).
  2. After each assignment, check feasibility:
     a. For each cell whose 4 sides are now assigned, check that
        SOME piece has those 4 sides (under some rotation).
     b. Maintain piece-supply counts; ensure each piece is used at most once.
  3. Branch on next edge.

This branches the search on colors (22-way) rather than pieces (256-way).
The piece-supply pruning is what gives BRAID power.
"""

from __future__ import annotations
import argparse
import sys
import time
from collections import defaultdict, Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load_csv(p):
    BORDER_RAW = 65535
    pieces = []
    with open(p) as f:
        size = int(f.readline().strip())
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            sides = [int(s.strip(), 2) for s in parts[:4]]
            sides = [0 if v == BORDER_RAW else v for v in sides]
            pieces.append(tuple(sides))
    return size, pieces


def rotate(piece, r):
    n, e, s, w = piece
    return [(n, e, s, w), (w, n, e, s), (s, w, n, e), (e, s, w, n)][r]


def build_piece_signature_index(pieces):
    """For each (n, e, s, w) tuple, list of (piece_id, rotation) producing it."""
    idx = defaultdict(list)
    for pid, p in enumerate(pieces):
        for r in range(4):
            sides = rotate(p, r)
            idx[sides].append((pid, r))
    return idx


def find_solution(pieces, W, H, time_limit_s=60.0):
    """Color-first search for a complete board.

    Edge variables in row-major order:
      For each row y in 0..H-1, then each col x in 0..W-1:
        Assign N edge (between (y, x) and (y-1, x)) if y > 0.
        Assign W edge (between (y, x) and (y, x-1)) if x > 0.
      Bottom row's S edges and rightmost col's E edges = BORDER.

    Actually a simpler order: assign cells row-major. When at cell (y, x),
    its N and W edges may already be assigned (from above/left).
    Assign:
      - N edge if y == 0 (BORDER).
      - W edge if x == 0 (BORDER).
      - S edge: new variable. Branch on color 1..22 (or BORDER if y==H-1).
      - E edge: new variable. Branch on color 1..22 (or BORDER if x==W-1).
    Now the cell (y, x) has all 4 sides assigned (n, e, s, w).
    Check: some piece can fill this cell. Reserve it.
    Recurse to (y, x+1).
    """
    BORDER = 0
    sig_idx = build_piece_signature_index(pieces)
    used = [False] * len(pieces)
    # n_edge[y][x] = N color of cell (y, x). h_edge has same dimension as cells.
    n_edge = [[BORDER] * W for _ in range(H + 1)]  # n_edge[H][*] is the bottom boundary (never used directly)
    w_edge = [[BORDER] * (W + 1) for _ in range(H)]  # w_edge[*][W] is the right boundary

    placement = [None] * (W * H)
    nodes = [0]
    best_depth = [0]
    t0 = time.time()

    # Initialize boundaries.
    # Top row's N = BORDER (n_edge[0][x] = BORDER) — already.
    # Bottom row's S = BORDER (n_edge[H][x] = BORDER for cell (H-1, x)'s S edge).
    # Leftmost col's W = BORDER (w_edge[y][0] = BORDER) — already.
    # Rightmost col's E = BORDER (w_edge[y][W] = BORDER).

    # Color domain: 1..22 for canonical (we'll inspect from pieces).
    all_colors = set()
    for p in pieces:
        for c in p:
            if c != 0:
                all_colors.add(c)
    color_domain = sorted(all_colors)

    def cell_n(y, x): return n_edge[y][x]
    def cell_w(y, x): return w_edge[y][x]
    def cell_s(y, x): return n_edge[y + 1][x]
    def cell_e(y, x): return w_edge[y][x + 1]

    def search(y, x):
        nodes[0] += 1
        depth = y * W + x
        if depth > best_depth[0]:
            best_depth[0] = depth
        if nodes[0] % 100000 == 0:
            elapsed = time.time() - t0
            print(f"  [search] nodes={nodes[0]} depth={depth} elapsed={elapsed:.1f}s", flush=True)
        if time.time() - t0 > time_limit_s:
            return False
        if y == H:
            return True  # done
        # Determine valid S domain.
        if y == H - 1:
            s_domain = [BORDER]
        else:
            s_domain = color_domain
        # Determine valid E domain.
        if x == W - 1:
            e_domain = [BORDER]
        else:
            e_domain = color_domain

        n = cell_n(y, x)
        w = cell_w(y, x)
        # Try each (s, e) pair.
        for s_c in s_domain:
            # Tentatively assign S.
            n_edge[y + 1][x] = s_c
            for e_c in e_domain:
                w_edge[y][x + 1] = e_c
                # Check feasibility: does any piece have signature (n, e, s, w)?
                sig = (n, e_c, s_c, w)
                cands = sig_idx.get(sig, [])
                for (pid, r) in cands:
                    if used[pid]:
                        continue
                    used[pid] = True
                    placement[y * W + x] = (pid, r)
                    # Recurse.
                    nx_x = x + 1 if x + 1 < W else 0
                    nx_y = y if x + 1 < W else y + 1
                    if search(nx_y, nx_x):
                        return True
                    used[pid] = False
                    placement[y * W + x] = None
            w_edge[y][x + 1] = BORDER  # reset
        n_edge[y + 1][x] = BORDER  # reset
        return False

    found = search(0, 0)
    return found, placement, nodes[0], best_depth[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", required=True)
    ap.add_argument("--time-limit", type=float, default=60.0)
    args = ap.parse_args()
    size, pieces = load_csv(args.puzzle)
    print(f"[v153-cf] puzzle: {size}×{size}, {len(pieces)} pieces", flush=True)

    t0 = time.time()
    found, placement, nodes, depth = find_solution(pieces, size, size, args.time_limit)
    elapsed = time.time() - t0
    print(f"[v153-cf] elapsed={elapsed:.1f}s nodes={nodes} max_depth={depth} found={found}")
    if found:
        print(f"[v153-cf] SUCCESS: complete {size}×{size} board found from scratch")


if __name__ == "__main__":
    main()
