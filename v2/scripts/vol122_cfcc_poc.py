#!/usr/bin/env python3
"""Vol-122 K3 — Color Flow Capacity Constraint (CFCC) PoC.

NEW INVENTION: at each CSP search node, compute color-supply-vs-demand
on the FRONTIER:

  For each color k:
    demand_k = # frontier slots (placed-cell-side facing unplaced cell)
              that show color k
    supply_k = total color-k edges across UNPLACED pieces

  If demand_k > supply_k for any k → INFEASIBLE → backtrack immediately

This is LIVE during search (vs vol-44 start-of-search LP-UB) and is
a CARDINALITY propagator on top of AC-3.

Compare CSP with vs without CFCC on small puzzles.
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


def solve(puzzle_path, use_cfcc=False, max_nodes=2_000_000, time_secs=60):
    pieces = load_puzzle(puzzle_path)
    n = len(pieces)
    side = int(n ** 0.5)
    assert side * side == n

    pieces_rot = [[rotate(pieces[pid], r) for r in range(4)] for pid in range(n)]

    # Precompute: per piece, color count (summed across all 4 sides)
    piece_color_count = [defaultdict(int) for _ in range(n)]
    for pid in range(n):
        for c in pieces[pid]:
            if c != 0:
                piece_color_count[pid][c] += 1

    pos_order = list(range(n))  # row-major

    board = [None] * n  # pos -> (edges, pid, rot)
    used_pids = [False] * n

    # CFCC tracking: remaining color supply
    color_supply = defaultdict(int)
    for pid in range(n):
        for c in pieces[pid]:
            if c != 0:
                color_supply[c] += 1

    stats = {'nodes': 0, 'best_depth': 0, 'cfcc_prunes': 0}
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

    def cfcc_feasible():
        """Compute frontier color demand vs remaining piece supply."""
        if not use_cfcc:
            return True
        demand = defaultdict(int)
        for pos in range(n):
            if board[pos] is None: continue
            r, c = pos // side, pos % side
            edges = board[pos][0]
            for (dr, dc, my_side, _) in [
                (-1, 0, 0, 2), (0, 1, 1, 3), (1, 0, 2, 0), (0, -1, 3, 1)
            ]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < side and 0 <= nc < side:
                    npos = nr * side + nc
                    if board[npos] is None:
                        color = edges[my_side]
                        if color != 0:
                            demand[color] += 1
        # supply_k = # color-k edges across UNPLACED pieces
        # color_supply tracks this (decremented as we place)
        for k, d in demand.items():
            if d > color_supply[k]:
                return False
        return True

    def recurse(depth):
        stats['nodes'] += 1
        if stats['nodes'] > max_nodes or time() - t_start > time_secs:
            return False
        if depth > stats['best_depth']:
            stats['best_depth'] = depth
        if depth == n:
            return True
        # CFCC check
        if not cfcc_feasible():
            stats['cfcc_prunes'] += 1
            return False
        pos = pos_order[depth]
        for pid in range(n):
            if used_pids[pid]: continue
            for rot in range(4):
                e = pieces_rot[pid][rot]
                if not valid_border(e, pos): continue
                if not compat(e, pos): continue
                board[pos] = (e, pid, rot)
                used_pids[pid] = True
                # Update color supply (deduct this piece's colors)
                for c in pieces[pid]:
                    if c != 0:
                        color_supply[c] -= 1
                if recurse(depth + 1):
                    return True
                board[pos] = None
                used_pids[pid] = False
                for c in pieces[pid]:
                    if c != 0:
                        color_supply[c] += 1
        return False

    solved = recurse(0)
    elapsed = time() - t_start
    return {
        'solved': solved,
        'best_depth': stats['best_depth'], 'n': n,
        'nodes': stats['nodes'], 'elapsed': elapsed,
        'cfcc_prunes': stats['cfcc_prunes'],
    }


def main():
    candidates = [
        "../data/generated/size_5_colors_4_3347f2df.csv",
        "../data/generated/size_6_colors_4_9f5c889b.csv",
        "../data/generated/size_6_colors_5_09ed3e44.csv",
        "../data/generated/size_7_colors_4_9584332a.csv",
        "../data/generated/size_7_colors_5_414f20cb.csv",
        "../data/generated/size_8_colors_5_e6520f51.csv",
    ]
    for path in candidates:
        p = Path(path)
        if not p.exists(): continue
        print(f"\n=== {p.name} ===")
        # Without CFCC
        r1 = solve(p, use_cfcc=False, max_nodes=2_000_000, time_secs=30)
        # With CFCC
        r2 = solve(p, use_cfcc=True, max_nodes=2_000_000, time_secs=30)
        print(f"  NO CFCC: solved={r1['solved']} depth={r1['best_depth']}/{r1['n']} nodes={r1['nodes']:>10d} elapsed={r1['elapsed']:5.1f}s")
        print(f"  CFCC   : solved={r2['solved']} depth={r2['best_depth']}/{r2['n']} nodes={r2['nodes']:>10d} elapsed={r2['elapsed']:5.1f}s  prunes={r2['cfcc_prunes']}")
        if r1['nodes'] > 0:
            print(f"  speedup (nodes): {r1['nodes'] / max(1, r2['nodes']):.2f}×")


if __name__ == "__main__":
    main()
