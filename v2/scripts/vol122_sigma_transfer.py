#!/usr/bin/env python3
"""Vol-122 K5 — σ-Transfer between McGavin 469 and clean-slate basins.

NEW INVENTION: σ-cycle analysis previously assumed vol-60 459 ↔ McGavin 469.
Now apply it to NEW clean-slate basins (vol-122 perm0 444).

Goal:
1. Compute the piece-permutation σ taking perm0_444 → McGavin_469.
2. Decompose σ into cycles.
3. For each cycle, compute the SCORE DELTA if we apply just that cycle.
4. Find any small cycle yielding Δ > 0 — that's a basin escape.

This differs from vol-65 σ analysis because:
- Source basin is vol-122 GENERATED (not vol-60 anchor).
- Different starting σ — totally new cycle structure.
"""

from __future__ import annotations
import json
import sys
from collections import defaultdict
from pathlib import Path


def parse_color(s):
    v = int(s.strip(), 2)
    return 0 if v == 65535 else v

def load_pieces():
    pieces = {}
    with open("../data/puzzles/size_16_official_eternity.csv") as f:
        lines = [l.strip() for l in f if l.strip()]
    pid = 0
    for line in lines[1:]:
        cols = line.split(',')
        if len(cols) >= 4:
            try:
                pieces[pid] = tuple(parse_color(cols[i]) for i in range(4))
                pid += 1
            except ValueError: pass
    return pieces

def rotate(edges, rot):
    return tuple(edges[(i - rot) % 4] for i in range(4))


def load_board(path):
    with open(path) as f:
        d = json.load(f)
    return {e['pos']: (e['piece_id'], e['rotation']) for e in d.get('placement', []) if e is not None}


def board_score(board, pieces, side):
    total = 0
    for r in range(side):
        for c in range(side):
            pos = r * side + c
            if pos not in board: continue
            pid, rot = board[pos]
            edges = rotate(pieces[pid], rot)
            if c < side - 1 and (npos := pos + 1) in board:
                npid, nrot = board[npos]
                nedges = rotate(pieces[npid], nrot)
                if edges[1] == nedges[3] and edges[1] != 0:
                    total += 1
            if r < side - 1 and (npos := pos + side) in board:
                npid, nrot = board[npos]
                nedges = rotate(pieces[npid], nrot)
                if edges[2] == nedges[0] and edges[2] != 0:
                    total += 1
    return total


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} SOURCE.json TARGET.json")
        sys.exit(1)
    source_path = Path(sys.argv[1])  # e.g., perm0 444
    target_path = Path(sys.argv[2])  # e.g., McGavin 469

    pieces = load_pieces()
    side = 16

    source = load_board(source_path)
    target = load_board(target_path)

    src_score = board_score(source, pieces, side)
    tgt_score = board_score(target, pieces, side)
    print(f"source: {src_score} matched ({source_path.name})")
    print(f"target: {tgt_score} matched ({target_path.name})")

    # σ: maps SOURCE piece-at-position to TARGET piece-at-same-position.
    # For each position, what piece moves from there?
    # σ(p_source) = p_target where p_source is at position pos in source, p_target is at pos in target.

    # Build cells where source != target (diff)
    diff_cells = []
    for pos in range(side * side):
        if pos not in source or pos not in target:
            continue
        s_pid, s_rot = source[pos]
        t_pid, t_rot = target[pos]
        if s_pid != t_pid or s_rot != t_rot:
            diff_cells.append(pos)
    print(f"\nDiff cells: {len(diff_cells)} / {side*side}")

    # piece permutation: for each diff cell pos,
    # the source-piece (s_pid) goes WHERE in target? Find position p' where target has s_pid.
    target_pos_of_pid = {pid: pos for pos, (pid, _) in target.items()}
    # σ in piece-space: source_pid → target_pid (the piece that replaced it at the same position)
    # Different way: σ as a permutation of POSITIONS via piece-tracking.
    # If source[pos] = (s_pid, _) and target[pos] = (t_pid, _),
    # then where does t_pid come from in source?
    source_pos_of_pid = {pid: pos for pos, (pid, _) in source.items()}

    # For each diff cell pos: target has t_pid at pos. Where was t_pid in source? source_pos_of_pid[t_pid].
    # So σ : pos → source_pos_of_pid[target[pos][0]].
    # This is the permutation of POSITIONS that "moves the piece that needs to be here in target,
    # from where it was in source".

    sigma = {}
    for pos in diff_cells:
        t_pid = target[pos][0]
        if t_pid in source_pos_of_pid:
            sigma[pos] = source_pos_of_pid[t_pid]
        else:
            sigma[pos] = None  # piece not in source (shouldn't happen if both 256-cell)

    # Decompose into cycles
    visited = set()
    cycles = []
    for start in diff_cells:
        if start in visited: continue
        cycle = []
        cur = start
        while cur not in visited:
            visited.add(cur)
            cycle.append(cur)
            if sigma.get(cur) is None: break
            cur = sigma[cur]
            if cur not in diff_cells: break  # cycle entered an UN-diff cell
        if len(cycle) > 1:
            cycles.append(cycle)
    cycles.sort(key=len, reverse=True)
    print(f"\nCycle decomposition: {len(cycles)} cycles")
    print(f"Cycle lengths: {[len(c) for c in cycles[:15]]}{'...' if len(cycles) > 15 else ''}")
    print(f"Sum of cycle lengths: {sum(len(c) for c in cycles)}")

    # For each cycle, apply ONLY that cycle and measure delta
    print(f"\nApplying each cycle individually (testing first 20 smallest):")
    cycles_by_size = sorted(cycles, key=len)
    n_test = min(20, len(cycles_by_size))
    for c in cycles_by_size[:n_test]:
        # Apply this cycle: at each pos in cycle, replace source's piece with target's piece (and rotation).
        # NOTE: cycle is a PERMUTATION of positions. The pieces at these positions get permuted.
        # In source, pieces at cycle positions are {source[c[0]][0], ..., source[c[-1]][0]}.
        # After applying cycle (in target form), the piece at c[i] should be target[c[i]].
        # That requires picking up source-piece at c[i] and replacing with target-piece (which was at σ(c[i]) in source).
        modified = source.copy()
        for pos in c:
            modified[pos] = target[pos]
        new_score = board_score(modified, pieces, side)
        delta = new_score - src_score
        marker = " ★" if delta > 0 else ""
        print(f"  cycle len {len(c):3d}: Δ = {delta:+4d} → score {new_score}{marker}")

    # Apply ALL cycles = should give target score
    full = source.copy()
    for c in cycles:
        for pos in c:
            full[pos] = target[pos]
    full_score = board_score(full, pieces, side)
    print(f"\nFull apply: {full_score} (target was {tgt_score})")


if __name__ == "__main__":
    main()
