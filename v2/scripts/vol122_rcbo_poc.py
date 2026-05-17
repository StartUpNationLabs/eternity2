#!/usr/bin/env python3
"""Vol-122 K1 — Reverse Construction via Boundary-Out (RCBO) PoC.

NEW INVENTION: start CSP from puzzle CENTER (a 4×4 sub-grid of interior
pieces), build outward in concentric rings until reaching the border.

Why genuinely different:
- Standard CSP starts at corners → propagates border constraints inward.
- RCBO starts at center → propagates interior compatibility outward.
- The center has more rotation freedom; the border forces locking.
- At the meeting point (border), the puzzle has 60 constraints to satisfy.

Algorithm:
1. Pick a 4×4 center sub-grid (rows 6..9, cols 6..9 in a 16×16 board).
2. Enumerate (piece, rotation) placements for those 16 cells (CSP-only).
3. For each feasible center, try ring expansion: rows 5..10, cols 5..10
   = 20 new cells. CSP-fill with constraint matching to center.
4. Continue until ring reaches the border. At the border, the 60-cell
   ring is the puzzle border ring (with piece supply consumed by interior).

This script tests the IDEA on small puzzles: 6×6 center=2×2, 8×8 center=4×4.
Measures whether center-out finds solutions faster than border-out.
"""

from __future__ import annotations
import sys
from collections import defaultdict
from pathlib import Path
from time import time

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


def center_out_order(side):
    """Compute a scan order: start at center, spiral outward."""
    center = side // 2
    cells = []
    visited = set()

    # Start with center 2x2 (or 4x4 for 8x8+)
    if side >= 8:
        # 4x4 center
        r_start = center - 2
        c_start = center - 2
        for r in range(r_start, r_start + 4):
            for c in range(c_start, c_start + 4):
                pos = r * side + c
                cells.append(pos)
                visited.add(pos)
    else:
        # 2x2 center (or single cell)
        r_start = center - 1 if side >= 4 else 0
        c_start = center - 1 if side >= 4 else 0
        for r in range(r_start, min(r_start + 2, side)):
            for c in range(c_start, min(c_start + 2, side)):
                pos = r * side + c
                cells.append(pos)
                visited.add(pos)

    # Expand rings
    while len(cells) < side * side:
        # Find perimeter of current placed region
        new_cells = []
        for pos in cells:
            r, c = pos // side, pos % side
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < side and 0 <= nc < side:
                    npos = nr * side + nc
                    if npos not in visited:
                        new_cells.append(npos)
                        visited.add(npos)
        cells.extend(new_cells)
    return cells


def border_out_order(side):
    """Border-first scan order (corners → edges → interior)."""
    cells = []
    # Corners first
    for pos in [0, side - 1, side * (side - 1), side * side - 1]:
        cells.append(pos)
    visited = set(cells)
    # Border ring
    for r in range(side):
        for c in range(side):
            if r in (0, side - 1) or c in (0, side - 1):
                pos = r * side + c
                if pos not in visited:
                    cells.append(pos)
                    visited.add(pos)
    # Interior row-major
    for r in range(side):
        for c in range(side):
            pos = r * side + c
            if pos not in visited:
                cells.append(pos)
                visited.add(pos)
    return cells


def row_major_order(side):
    return list(range(side * side))


def solve(puzzle_path, pos_order, max_nodes=1_000_000, time_secs=30, label="?"):
    pieces = load_puzzle(puzzle_path)
    n = len(pieces)
    side = int(n ** 0.5)
    assert side * side == n

    pieces_rot = [[rotate(pieces[pid], r) for r in range(4)] for pid in range(n)]

    board = [None] * n  # pos -> (edges, pid, rot)
    used_pids = [False] * n

    stats = {'nodes': 0, 'best_depth': 0}
    t_start = time()

    def valid_border(edges, pos):
        r, c = pos // side, pos % side
        T, R, B, L = edges
        if (r == 0) != (T == 0): return False
        if (r == side - 1) != (B == 0): return False
        if (c == 0) != (L == 0): return False
        if (c == side - 1) != (R == 0): return False
        return True

    def compat(edges, pos):
        r, c = pos // side, pos % side
        T, R, B, L = edges
        if r > 0 and board[(r-1)*side + c] is not None:
            if board[(r-1)*side + c][0][2] != T: return False
        if r < side-1 and board[(r+1)*side + c] is not None:
            if board[(r+1)*side + c][0][0] != B: return False
        if c > 0 and board[r*side + c-1] is not None:
            if board[r*side + c-1][0][1] != L: return False
        if c < side-1 and board[r*side + c+1] is not None:
            if board[r*side + c+1][0][3] != R: return False
        return True

    def recurse(depth):
        stats['nodes'] += 1
        if stats['nodes'] > max_nodes or time() - t_start > time_secs:
            return False
        if depth > stats['best_depth']:
            stats['best_depth'] = depth
        if depth == n:
            return True
        pos = pos_order[depth]
        for pid in range(n):
            if used_pids[pid]: continue
            for rot in range(4):
                e = pieces_rot[pid][rot]
                if not valid_border(e, pos): continue
                if not compat(e, pos): continue
                board[pos] = (e, pid, rot)
                used_pids[pid] = True
                if recurse(depth + 1):
                    return True
                board[pos] = None
                used_pids[pid] = False
        return False

    solved = recurse(0)
    elapsed = time() - t_start
    return {
        'label': label, 'solved': solved,
        'best_depth': stats['best_depth'], 'n': n,
        'nodes': stats['nodes'], 'elapsed': elapsed,
        'nps': stats['nodes'] / elapsed if elapsed > 0 else 0,
    }


def main():
    if len(sys.argv) < 2:
        candidates = [
            "../data/generated/size_5_colors_3_4ab6bb20.csv",
            "../data/generated/size_5_colors_4_3347f2df.csv",
            "../data/generated/size_6_colors_4_9f5c889b.csv",
            "../data/generated/size_6_colors_5_09ed3e44.csv",
            "../data/generated/size_7_colors_4_9584332a.csv",
            "../data/generated/size_8_colors_5_e6520f51.csv",
            "../data/generated/size_8_colors_6_*.csv",
        ]
    else:
        candidates = sys.argv[1:]

    for path_glob in candidates:
        for p in Path('.').glob(path_glob) if '*' in path_glob else [Path(path_glob)]:
            if not p.exists(): continue
            side = int(len(load_puzzle(p)) ** 0.5)
            print(f"\n=== {p.name} ({side}×{side}) ===")
            orders = {
                'row-major': row_major_order(side),
                'border-out': border_out_order(side),
                'center-out (RCBO)': center_out_order(side),
            }
            for name, order in orders.items():
                r = solve(p, order, max_nodes=2_000_000, time_secs=20, label=name)
                status = "SOLVED" if r['solved'] else f"depth {r['best_depth']}/{r['n']}"
                print(f"  {name:25s} {status:18s} nodes={r['nodes']:>10d} elapsed={r['elapsed']:5.1f}s")


if __name__ == "__main__":
    main()
