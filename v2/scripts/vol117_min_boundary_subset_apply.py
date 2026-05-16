#!/usr/bin/env python3
"""Vol-117 T4 — apply greedy min-boundary σ-cycle subset to a source board
and dump the resulting partial.

Math hypothesis (vol-117 T3 finding): the 459→McGavin 154-cycle has a
greedy-grow min-boundary trajectory where at k=42 boundary is only 66
edges (vs ~118 for contiguous subset). Applying such a low-boundary
subset should lose FEWER score edges than a contiguous-subset
application of the same size.

If the score loss is small enough that ALNS can recover (and possibly
exceed 459), we'd have a constructive bridge.

This script:
1. Finds the giant σ-cycle between source and target.
2. Runs greedy min-boundary to get a subset trajectory.
3. For each subset size in a sweep, applies the subset and dumps
   the resulting partial-board JSON.

Output: per-k JSON files at vol-117/min_boundary_subsets/ with the
partial-after-σ-subset-applied board. Each can be fed to ALNS to
test recovery.

Usage: vol117_min_boundary_subset_apply.py <src> <tgt> <out_dir>
"""

import json
import os
import sys
from pathlib import Path

W, H = 16, 16


def load_board(p):
    d = json.load(open(p))
    arr = d.get("placement") or d.get("board", {}).get("placement", [])
    pos_to_p = {}  # pos -> (piece_id, rotation)
    pid_to_pos = {}
    for idx, item in enumerate(arr):
        if item is None: continue
        pos = int(item.get("pos", idx))
        pid = int(item["piece_id"])
        rot = int(item.get("rotation", 0))
        pos_to_p[pos] = (pid, rot)
        pid_to_pos[pid] = pos
    return pos_to_p, pid_to_pos


def sigma_cycles(pos_to_p_a, pid_to_pos_b):
    """σ: pos_in_a -> pos_in_b for each piece-id present in both."""
    s = {}
    for pos, (pid, _) in pos_to_p_a.items():
        bpos = pid_to_pos_b.get(pid)
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
    pool = set(cycle)
    subset = set()
    order = []
    while pool:
        best_cell = None
        best_b = None
        for c in pool:
            new_subset = subset | {c}
            b = boundary_of(new_subset)
            if best_b is None or b < best_b:
                best_b = b
                best_cell = c
        subset.add(best_cell)
        order.append(best_cell)
        pool.remove(best_cell)
    return order


def apply_subset(src_pos_to_p, tgt_pos_to_p, subset_cells):
    """Replace src[c] with tgt[c] for c in subset_cells."""
    new = dict(src_pos_to_p)
    for c in subset_cells:
        if c in tgt_pos_to_p:
            new[c] = tgt_pos_to_p[c]
    return new


def main():
    if len(sys.argv) < 4:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    src_path = Path(sys.argv[1])
    tgt_path = Path(sys.argv[2])
    out_dir = Path(sys.argv[3])
    out_dir.mkdir(parents=True, exist_ok=True)

    src_pos, src_pid = load_board(src_path)
    tgt_pos, tgt_pid = load_board(tgt_path)
    cycles = sigma_cycles(src_pos, tgt_pid)

    if not cycles:
        print("no σ-cycles", file=sys.stderr)
        sys.exit(2)

    giant = cycles[0]
    print(f"giant cycle size: {len(giant)}")
    order = greedy_grow(giant)
    print(f"greedy order computed; len={len(order)}")

    # Sweep subset sizes: 10, 20, 30, ..., up to len(giant) - 5
    sample_sizes = list(range(10, len(giant), 10))
    boundaries = []
    for k in sample_sizes:
        subset = set(order[:k])
        b = boundary_of(subset)
        boundaries.append((k, b))
        new_pos = apply_subset(src_pos, tgt_pos, subset)
        # Dump as placement-array JSON.
        placements = []
        for pos, (pid, rot) in new_pos.items():
            placements.append({"pos": pos, "piece_id": pid, "rotation": rot})
        placements.sort(key=lambda x: x["pos"])
        out_path = out_dir / f"min_boundary_k{k:03d}_b{b:03d}.json"
        with open(out_path, "w") as f:
            json.dump({
                "placement": placements,
                "source": "vol117_min_boundary_subset",
                "src": str(src_path.name),
                "tgt": str(tgt_path.name),
                "k": k,
                "boundary": b,
                "matched": 0,  # to be filled by rescore
            }, f, indent=2)
    print(f"# wrote {len(sample_sizes)} subset boards to {out_dir}")
    for k, b in boundaries:
        print(f"  k={k:4d}  boundary={b}")


if __name__ == "__main__":
    main()
