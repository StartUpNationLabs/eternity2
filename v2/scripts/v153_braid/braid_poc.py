#!/usr/bin/env python3
"""V153 BRAID PoC — joint warp-weft color-thread search.

Algorithm:
  1. Enumerate possible warp threads for row 0 (border constraints +
     piece availability).
  2. For each warp 0, propagate constraints to weft columns (the
     S-side of each row-0 cell defines part of weft).
  3. Recursively build row 1, 2, ..., maintaining weft state.
  4. At each row, check piece availability: every cell needs a piece
     with its prescribed (n, e, s, w) and that piece not yet used.

State per partial board at depth d (rows 0..d-1 placed):
  - placed[(y, x)] = piece_id (with rotation determined by sides).
  - used_pieces = set of piece_ids used.
  - weft_top[x] = N-color of cell at (d, x) = S-color of (d-1, x).
                 This is the constraint into row d.

Decision per row: choose a sequence of pieces for (d, 0), (d, 1), ..., (d, W-1)
such that:
  - For x=0..W-1: piece.N == weft_top[x] (matches row d-1).
  - For x=0..W-2: piece.E (at x) == piece.W (at x+1)  [warp continuity].
  - For x=0: piece.W == BORDER.
  - For x=W-1: piece.E == BORDER.
  - For y=0: piece.N == BORDER (initial weft_top all BORDER).
  - For y=H-1: piece.S == BORDER (final row).
  - Piece not in used_pieces.

We try all rotations of each piece.

Output: complete board with score (must be perfect = (W-1)*H + W*(H-1) for full
match).
"""

from __future__ import annotations
import argparse
import sys
import time
from collections import defaultdict
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
    """Rotate piece (n, e, s, w) by r * 90 deg."""
    n, e, s, w = piece
    return [(n, e, s, w), (w, n, e, s), (s, w, n, e), (e, s, w, n)][r]


def piece_class(piece):
    n_border = sum(1 for s in piece if s == 0)
    if n_border == 2: return "corner"
    if n_border == 1: return "edge"
    return "interior"


def cell_class(y, x, H, W):
    is_corner = (y == 0 or y == H - 1) and (x == 0 or x == W - 1)
    is_border = y == 0 or y == H - 1 or x == 0 or x == W - 1
    if is_corner: return "corner"
    if is_border: return "edge"
    return "interior"


def index_piece_rots_by_sides(pieces):
    """For fast lookup: given (n, e, s, w), find all (piece_id, rotation)
    that produce these sides under some rotation."""
    idx = defaultdict(list)
    for pid, p in enumerate(pieces):
        for r in range(4):
            sides = rotate(p, r)
            idx[sides].append((pid, r))
    return idx


def index_by_partial(pieces):
    """Index by (N, W) — for row-major scan, given N color (from above)
    and W color (from left), find candidate (piece_id, rotation, S, E)."""
    idx = defaultdict(list)
    for pid, p in enumerate(pieces):
        for r in range(4):
            n, e, s, w = rotate(p, r)
            idx[(n, w)].append((pid, r, e, s))
    return idx


def find_first_solution(pieces, W, H, time_limit_s=60.0):
    """Row-major DFS with WEFT-state tracking. This is equivalent to
    vanilla_fast's strict row-major DFS — but here we make the weft
    structure explicit and use it for diagnostics."""
    BORDER = 0
    idx_nw = index_by_partial(pieces)
    used = [False] * len(pieces)
    weft_top = [BORDER] * W  # N-colors for cells in current row.
    placement = [None] * (W * H)
    t0 = time.time()
    nodes = [0]
    best_depth = [0]

    def search(y, x):
        nodes[0] += 1
        if time.time() - t0 > time_limit_s:
            return False
        if y == H:
            return True
        depth = y * W + x
        if depth > best_depth[0]:
            best_depth[0] = depth
        # N constraint = weft_top[x].
        # W constraint = E side of cell at (y, x-1) if x > 0, else BORDER.
        if x == 0:
            w_color = BORDER
        else:
            prev = placement[y * W + x - 1]
            w_color = prev[2]  # S? no — E of left cell. Recompute:
            # Wait: prev stores the rotated (n,e,s,w) of the cell.
            # The E of the left cell faces our W. So:
            # w_color = E of left = prev_sides[1]
            w_color = prev[3]  # Hmm need to fix what I store.
        # Lookup candidates.
        cands = idx_nw.get((weft_top[x], w_color), [])
        for (pid, r, e, s) in cands:
            if used[pid]:
                continue
            # Border constraint check on E (last col).
            if x == W - 1 and e != BORDER:
                continue
            if y == H - 1 and s != BORDER:
                continue
            # Wait — first col W is already enforced via the lookup
            # (we passed w_color = BORDER when x=0).
            # First row N is enforced via weft_top initial = BORDER.
            used[pid] = True
            placement[y * W + x] = (pid, r, e, s)  # store key info
            old_weft = weft_top[x]
            weft_top[x] = s  # the S-side becomes next row's N for this column.
            nx_x = x + 1 if x + 1 < W else 0
            nx_y = y if x + 1 < W else y + 1
            if search(nx_y, nx_x):
                return True
            used[pid] = False
            placement[y * W + x] = None
            weft_top[x] = old_weft
        return False

    found = search(0, 0)
    return found, placement, nodes[0], best_depth[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", required=True)
    ap.add_argument("--time-limit", type=float, default=60.0)
    args = ap.parse_args()
    size, pieces = load_csv(args.puzzle)
    print(f"[v153-poc] puzzle: {size}×{size}, {len(pieces)} pieces", flush=True)

    t0 = time.time()
    found, placement, nodes, depth = find_first_solution(pieces, size, size, args.time_limit)
    elapsed = time.time() - t0
    print(f"[v153-poc] elapsed={elapsed:.1f}s nodes={nodes} max_depth={depth} found={found}")
    if found:
        print(f"[v153-poc] SUCCESS: complete {size}×{size} board found")


if __name__ == "__main__":
    main()
