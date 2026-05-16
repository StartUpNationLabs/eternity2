#!/usr/bin/env python3
"""Vol-117 T4 — minimum-boundary non-contiguous σ-cycle subset via greedy.

Follow-up to vol117_sigma_boundary_growth.py. Instead of contiguous
subsets, try greedy minimum-boundary subsets: at each step, add the
cycle-cell whose addition increases boundary the least.

Two procedures:
(a) Greedy-grow from singleton: start with the lowest-degree cell,
    add the cell that minimizes boundary growth.
(b) Greedy-shrink from full cycle: start with all N cells, remove
    the cell whose removal decreases boundary the most.

(b) is most interesting for σ-cycle indecomposability: it tells us
"can we DROP some cells from a full cycle and reduce boundary".

Output: per-cycle, table of boundary at each subset size for the
greedy-grow trajectory.

Usage: vol117_sigma_min_boundary_greedy.py <board_a> <board_b>
"""

import json
import sys
from pathlib import Path

W, H = 16, 16


def load_board(p):
    d = json.load(open(p))
    arr = d.get("placement") or d.get("board", {}).get("placement", [])
    pos_to_pid = {}
    pid_to_pos = {}
    for idx, item in enumerate(arr):
        if item is None: continue
        pos = int(item.get("pos", idx))
        pid = int(item["piece_id"])
        pos_to_pid[pos] = pid
        pid_to_pos[pid] = pos
    return pos_to_pid, pid_to_pos


def sigma_cycles(pos_a, pid_b):
    s = {}
    for pos, pid in pos_a.items():
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


def greedy_grow(cycle):
    """Start empty. Add cells greedily to minimize boundary growth."""
    pool = set(cycle)
    subset = set()
    trajectory = [(0, 0)]
    while pool:
        # pick cell whose addition gives min new boundary
        best_cell = None
        best_b = None
        for c in pool:
            new_subset = subset | {c}
            b = boundary_of(new_subset)
            if best_b is None or b < best_b:
                best_b = b
                best_cell = c
        subset.add(best_cell)
        pool.remove(best_cell)
        trajectory.append((len(subset), best_b))
    return trajectory


def main():
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    a_path = Path(sys.argv[1])
    b_path = Path(sys.argv[2])
    pos_a, _ = load_board(a_path)
    _, pid_b = load_board(b_path)
    cycles = sigma_cycles(pos_a, pid_b)

    print(f"# σ-cycles between {a_path.name} and {b_path.name}")
    print(f"# {len(cycles)} cycles, sizes: {[len(c) for c in cycles]}")
    print()

    for ci, cycle in enumerate(cycles):
        N = len(cycle)
        if N < 4:
            continue
        traj = greedy_grow(cycle)
        print(f"## cycle #{ci} (N={N}) — greedy min-boundary trajectory")
        # Sample evenly
        n_samples = 20
        step = max(1, len(traj) // n_samples)
        for k, b in traj[::step]:
            ratio = b / k if k > 0 else 0
            print(f"  k={k:4d}  boundary={b:6d}  b/k={ratio:.2f}")
        # Min boundary subset
        min_traj = min(traj[1:], key=lambda x: x[1])
        print(f"  >> MIN boundary across greedy trajectory: k={min_traj[0]}, b={min_traj[1]}")
        # Min RATIO subset
        min_ratio = min(traj[1:], key=lambda x: x[1] / max(x[0], 1))
        print(f"  >> MIN ratio b/k: k={min_ratio[0]}, b={min_ratio[1]}, ratio={min_ratio[1]/min_ratio[0]:.2f}")
        print()


if __name__ == "__main__":
    main()
