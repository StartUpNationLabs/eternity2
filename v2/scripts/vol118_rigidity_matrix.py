#!/usr/bin/env python3
"""Vol-118 — pairwise rigidity matrix across the 459-level set.

For each pair (a, b) in a 459-board corpus, compute:
- Hamming distance (Δ_pieces).
- σ-cycle structure (count, max cycle size, total cells in cycles).
- Min boundary across all σ-cycles' contiguous subsets at k = ⌈N/2⌉
  (a fixed reference fraction).

Output: a CSV + summary stats.

This characterises the GEOMETRY OF THE 459-LEVEL SET as a rigidity
graph. Pairs with small σ-cycles → "near" each other. Pairs with
giant cycles → "distant".

Usage: vol118_rigidity_matrix.py <board1> <board2> ...
"""

import json
import sys
from pathlib import Path

W, H = 16, 16


def load_board(p):
    d = json.load(open(p))
    arr = d.get("placement") or d.get("board", {}).get("placement", [])
    pos_to_p = {}
    pid_to_pos = {}
    for idx, item in enumerate(arr):
        if item is None: continue
        pos = int(item.get("pos", idx))
        pid = int(item["piece_id"])
        rot = int(item.get("rotation", 0))
        pos_to_p[pos] = (pid, rot)
        pid_to_pos[pid] = pos
    return pos_to_p, pid_to_pos


def sigma_cycles(pos_a, pid_b):
    s = {}
    for pos, (pid, _) in pos_a.items():
        bpos = pid_b.get(pid)
        if bpos is not None and bpos != pos:
            s[pos] = bpos
    visited = set()
    cycles = []
    for start in s:
        if start in visited: continue
        cycle = []
        cur = start
        while cur not in visited and cur in s:
            visited.add(cur)
            cycle.append(cur)
            cur = s[cur]
        if cycle:
            cycles.append(cycle)
    cycles.sort(key=len, reverse=True)
    return cycles


def grid_neighbors(p):
    x, y = p % W, p // W
    out = []
    if x > 0: out.append(p - 1)
    if x < W - 1: out.append(p + 1)
    if y > 0: out.append(p - W)
    if y < H - 1: out.append(p + W)
    return out


def boundary_of(subset):
    b = 0
    for p in subset:
        for q in grid_neighbors(p):
            if q not in subset:
                b += 1
    return b


def min_contiguous_boundary_at_half(cycle):
    """Min boundary at k = ⌈N/2⌉ over all rotational starts."""
    N = len(cycle)
    k = (N + 1) // 2
    if k < 1 or k >= N: return None
    min_b = float('inf')
    for start in range(N):
        subset = set()
        for j in range(k):
            subset.add(cycle[(start + j) % N])
        b = boundary_of(subset)
        if b < min_b: min_b = b
    return min_b, k


def hamming(pos_a, pos_b):
    """Count positions where (piece_id) differ — ignore rotation."""
    h = 0
    for pos, (pid, _) in pos_a.items():
        bp = pos_b.get(pos)
        if bp is None or bp[0] != pid:
            h += 1
    return h


def main():
    paths = [Path(p) for p in sys.argv[1:]]
    if len(paths) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    boards = {}
    for p in paths:
        try:
            pos, pid = load_board(p)
            boards[p.name] = (p, pos, pid)
        except Exception as e:
            print(f"# skip {p.name}: {e}", file=sys.stderr)

    names = sorted(boards.keys())
    print("src,tgt,hamming,n_cycles,max_cycle,total_cycle_cells,min_b_at_half,k_at_half")
    for i, ni in enumerate(names):
        _, pos_i, pid_i = boards[ni]
        for j, nj in enumerate(names):
            if i >= j: continue
            _, pos_j, pid_j = boards[nj]
            cycles = sigma_cycles(pos_i, pid_j)
            if not cycles:
                print(f"{ni},{nj},0,0,0,0,,")
                continue
            h = hamming(pos_i, pos_j)
            nc = len(cycles)
            maxc = max(len(c) for c in cycles)
            totc = sum(len(c) for c in cycles)
            res = min_contiguous_boundary_at_half(cycles[0])
            if res is None:
                mb, k = "", ""
            else:
                mb, k = res
            print(f"{ni},{nj},{h},{nc},{maxc},{totc},{mb},{k}")


if __name__ == "__main__":
    main()
