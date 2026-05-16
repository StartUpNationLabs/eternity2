#!/usr/bin/env python3
"""Vol-118 — apply a SINGLE σ-cycle from source to target board, score result.

For each cycle in the σ-decomposition, apply it in isolation and
report the resulting score. Tests whether individual cycles
contribute additively to the δ between source and target.

Usage: vol118_apply_single_cycle.py <src> <tgt> <out_dir>
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
        if cycle: cycles.append(cycle)
    cycles.sort(key=len, reverse=True)
    return cycles


def apply_cycle(src_pos, tgt_pos, cycle_cells):
    new = dict(src_pos)
    for c in cycle_cells:
        if c in tgt_pos:
            new[c] = tgt_pos[c]
    return new


def dump_board(pos_to_p, path, src_path, tgt_path, cycle_idx, cycle_size):
    placements = [{"pos": pos, "piece_id": pid, "rotation": rot}
                  for pos, (pid, rot) in pos_to_p.items()]
    placements.sort(key=lambda x: x["pos"])
    with open(path, "w") as f:
        json.dump({
            "placement": placements,
            "source": "vol118_single_cycle",
            "src": str(src_path.name),
            "tgt": str(tgt_path.name),
            "cycle_idx": cycle_idx,
            "cycle_size": cycle_size,
            "matched": 0,
        }, f, indent=2)


def main():
    if len(sys.argv) < 4:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    src_path = Path(sys.argv[1])
    tgt_path = Path(sys.argv[2])
    out_dir = Path(sys.argv[3])
    out_dir.mkdir(parents=True, exist_ok=True)

    src_pos, _ = load_board(src_path)
    tgt_pos, tgt_pid = load_board(tgt_path)
    cycles = sigma_cycles(src_pos, tgt_pid)
    print(f"σ-cycles: {[len(c) for c in cycles]}")

    # Apply each cycle alone.
    for ci, cycle in enumerate(cycles):
        N = len(cycle)
        new_pos = apply_cycle(src_pos, tgt_pos, cycle)
        out_path = out_dir / f"cycle_{ci:02d}_size{N:03d}.json"
        dump_board(new_pos, out_path, src_path, tgt_path, ci, N)
        print(f"  wrote cycle #{ci} (size {N}) -> {out_path}")

    # Also: pairwise combos
    if len(cycles) >= 2:
        for i in range(len(cycles)):
            for j in range(i+1, len(cycles)):
                combo = list(cycles[i]) + list(cycles[j])
                new_pos = apply_cycle(src_pos, tgt_pos, combo)
                out_path = out_dir / f"cycles_{i:02d}+{j:02d}_size{len(combo):03d}.json"
                dump_board(new_pos, out_path, src_path, tgt_path, f"{i}+{j}", len(combo))
                print(f"  wrote cycles #{i}+{j} (combined size {len(combo)}) -> {out_path}")


if __name__ == "__main__":
    main()
