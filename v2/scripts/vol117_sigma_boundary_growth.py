#!/usr/bin/env python3
"""Vol-117 T3 — σ-cycle boundary growth measurement.

Math question: For a σ-cycle C between two 459 basins, how does the
edge-boundary cardinality grow with subset size?

Define:
- C = ordered cycle of N cells [c_0, c_1, ..., c_{N-1}].
- For a subset S = {c_i, c_{i+1}, ..., c_{i+k-1}} (contiguous in the
  cycle order), the boundary B(S) = edges between cells in S and
  cells NOT in S.
- Sequential boundary growth: |B(S)| as function of k.

Two views:
(a) "cycle topology" — boundary in the cycle graph (always 2 for
    any proper contiguous subset; trivial). Skip.
(b) "geometric topology" — boundary in the 16×16 grid: count of
    (cell-in-S, cell-NOT-in-S) edges where the two cells are
    orthogonally adjacent on the board.

This is the geometric boundary cardinality. It governs how many
score-edges the partial-cycle-application breaks at its physical
interface with the unchanged board.

If boundary grows linearly with k: cycle is "spaghetti" through the
grid; partial applications always lose ~boundary edges proportional
to size.

If boundary stays bounded (or grows sublinearly): the cycle has
contiguous geometric structure. Some partial applications could
have very small boundary, opening up Δ ≥ 0 possibilities (the
classic "find a 0-boundary subset" subproblem).

Usage:
    vol117_sigma_boundary_growth.py <board_a.json> <board_b.json>
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

W, H = 16, 16


def load_board(p):
    with open(p) as f:
        d = json.load(f)
    arr = d.get("placement") or d.get("board", {}).get("placement", [])
    pos_to_pid = {}
    pid_to_pos = {}
    for idx, item in enumerate(arr):
        if item is None:
            continue
        pos = int(item.get("pos", idx))
        pid = int(item["piece_id"])
        pos_to_pid[pos] = pid
        pid_to_pos[pid] = pos
    return pos_to_pid, pid_to_pos


def sigma_cycles(pos_to_pid_a, pid_to_pos_b):
    s = {}
    for pos, pid in pos_to_pid_a.items():
        bpos = pid_to_pos_b.get(pid)
        if bpos is not None and bpos != pos:
            s[pos] = bpos
    visited = set()
    cycles = []
    for start in s:
        if start in visited:
            continue
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


def boundary_cardinality(subset_set, all_in_cycle_set):
    """Count edges (s, n) where s in subset_set, n NOT in subset_set,
    counted once per unordered pair. n may or may not be in cycle.
    """
    b = 0
    for p in subset_set:
        for q in grid_neighbors(p):
            if q not in subset_set:
                b += 1
    # Each boundary edge counted once (we iterate from subset_set side).
    return b


def main():
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    a_path = Path(sys.argv[1])
    b_path = Path(sys.argv[2])

    pos_a, pid_a = load_board(a_path)
    pos_b, pid_b = load_board(b_path)
    cycles = sigma_cycles(pos_a, pid_b)

    if not cycles:
        print("no σ-cycles (boards may be identical or no pieces in common)")
        return

    all_in_cycle = set()
    for c in cycles:
        all_in_cycle.update(c)

    print(f"# σ-cycles between {a_path.name} and {b_path.name}")
    print(f"# {len(cycles)} cycles, total cells in cycles: {len(all_in_cycle)}")
    print(f"# cycle sizes: {[len(c) for c in cycles]}")
    print()

    for ci, cycle in enumerate(cycles):
        N = len(cycle)
        if N < 4:
            continue
        print(f"## cycle #{ci}  (N={N})")
        print(f"# k  |  contiguous-subset boundary (min over rotations)")
        # For each k in 1..N-1, compute min boundary over the N
        # rotational starting positions for a contiguous subset of size k.
        records = []
        for k in range(1, N):
            min_b = float('inf')
            best_start = -1
            for start in range(N):
                subset = set()
                for j in range(k):
                    subset.add(cycle[(start + j) % N])
                b = boundary_cardinality(subset, all_in_cycle)
                if b < min_b:
                    min_b = b
                    best_start = start
            records.append((k, min_b, best_start))
        # Print sparse: every 10th + the minimum-ratio point
        for k, b, _ in records[::max(1, N // 20)]:
            print(f"  {k:4d}    {b:6.0f}    (ratio b/k = {b/k:.2f})")
        min_ratio = min(records, key=lambda x: x[1] / x[0])
        print(f"  >> MIN ratio: k={min_ratio[0]}, b={min_ratio[1]}, ratio={min_ratio[1]/min_ratio[0]:.2f}, start={min_ratio[2]}")
        print()


if __name__ == "__main__":
    main()
