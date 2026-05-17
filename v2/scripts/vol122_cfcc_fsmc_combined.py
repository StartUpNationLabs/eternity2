#!/usr/bin/env python3
"""Vol-122 K4 — CFCC + FSMC PIH Combined.

Both K3 (CFCC) and J6 (FSMC PIH) are orthogonal pruning mechanisms:
- CFCC checks per-color frontier-demand vs unplaced-piece-supply.
- FSMC PIH memoizes (frontier-colors + remaining-color-supply) as state key.

Combined: prune via CFCC first (O(1) incremental check), then check FSMC
PIH cache. Measure compound speedup.
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


def solve(puzzle_path, mode='none', max_nodes=2_000_000, time_secs=60):
    """mode: 'none' | 'cfcc' | 'fsmc' | 'both'"""
    pieces = load_puzzle(puzzle_path)
    n = len(pieces)
    side = int(n ** 0.5)
    assert side * side == n

    pieces_rot = [[rotate(pieces[pid], r) for r in range(4)] for pid in range(n)]
    pos_order = list(range(n))
    board = [None] * n
    used_pids = [False] * n

    color_supply = defaultdict(int)
    for pid in range(n):
        for c in pieces[pid]:
            if c != 0:
                color_supply[c] += 1
    initial_supply = dict(color_supply)

    cache = set()
    stats = {'nodes': 0, 'best_depth': 0, 'cfcc_prunes': 0, 'fsmc_hits': 0}
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

    def frontier_state(depth):
        """Compute (frontier_sig, supply) state for FSMC PIH."""
        sig = []
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
                        sig.append((pos, my_side, edges[my_side]))
        sig.sort()
        supply_tuple = tuple(sorted(color_supply.items()))
        return (tuple(sig), supply_tuple)

    def cfcc_demand():
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
                        c2 = edges[my_side]
                        if c2 != 0:
                            demand[c2] += 1
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

        if mode in ('cfcc', 'both'):
            if not cfcc_demand():
                stats['cfcc_prunes'] += 1
                return False

        if mode in ('fsmc', 'both'):
            key = frontier_state(depth)
            if key in cache:
                stats['fsmc_hits'] += 1
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
        if mode in ('fsmc', 'both'):
            cache.add(frontier_state(depth))
        return False

    solved = recurse(0)
    elapsed = time() - t_start
    return {
        'mode': mode, 'solved': solved,
        'depth': stats['best_depth'], 'n': n,
        'nodes': stats['nodes'], 'elapsed': elapsed,
        'cfcc_prunes': stats['cfcc_prunes'], 'fsmc_hits': stats['fsmc_hits'],
        'cache_size': len(cache),
    }


def main():
    candidates = [
        "../data/generated/size_7_colors_4_9584332a.csv",
        "../data/generated/size_7_colors_5_414f20cb.csv",
        "../data/generated/size_8_colors_5_e6520f51.csv",
    ]
    for path in candidates:
        p = Path(path)
        if not p.exists(): continue
        print(f"\n=== {p.name} ===")
        for mode in ['none', 'cfcc', 'fsmc', 'both']:
            r = solve(p, mode=mode, max_nodes=2_000_000, time_secs=20)
            status = "SOLVED" if r['solved'] else f"d{r['depth']}/{r['n']}"
            extra = ""
            if r['cfcc_prunes']: extra += f" cfcc={r['cfcc_prunes']}"
            if r['fsmc_hits']: extra += f" fsmc_hit={r['fsmc_hits']}"
            print(f"  {mode:6s} {status:10s} nodes={r['nodes']:>9d} elapsed={r['elapsed']:5.1f}s{extra}")


if __name__ == "__main__":
    main()
