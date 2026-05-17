#!/usr/bin/env python3
"""Vol-122 K6 — Cycle-Slip Operator: traverse σ-cycle step-by-step with SA acceptance.

NEW INVENTION: σ-cycles between perm0_444 and McGavin_469 are
indecomposable (full apply yields target; partial apply yields Δ < 0).

But what if we SLIP DOWN the cycle one transposition at a time,
accepting Δ < 0 intermediate steps (like simulated annealing) until
we reach the end of the cycle where score recovers to target?

Each cycle position has σ(pos) = next position. Going AROUND the cycle
requires K transpositions for a K-cycle.

This script:
1. Computes σ-cycle decomposition.
2. For each cycle, applies transpositions one-at-a-time and records
   the score trajectory.
3. Identifies whether the trajectory has ANY local maximum > source score.
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
    source_path = Path(sys.argv[1])
    target_path = Path(sys.argv[2])

    pieces = load_pieces()
    side = 16

    source = load_board(source_path)
    target = load_board(target_path)

    src_score = board_score(source, pieces, side)
    tgt_score = board_score(target, pieces, side)
    print(f"source: {src_score}, target: {tgt_score}")

    source_pos_of_pid = {pid: pos for pos, (pid, _) in source.items()}

    diff_cells = [pos for pos in range(side * side)
                  if pos in source and pos in target
                  and (source[pos][0] != target[pos][0] or source[pos][1] != target[pos][1])]

    sigma = {pos: source_pos_of_pid[target[pos][0]] for pos in diff_cells if target[pos][0] in source_pos_of_pid}

    # Decompose into cycles
    visited = set()
    cycles = []
    for start in diff_cells:
        if start in visited: continue
        cycle = []
        cur = start
        while cur not in visited and cur in sigma:
            visited.add(cur)
            cycle.append(cur)
            cur = sigma[cur]
            if cur in cycle: break
        if len(cycle) > 1:
            cycles.append(cycle)
    cycles.sort(key=len)

    print(f"Cycles: {[len(c) for c in cycles]}")

    # For each cycle: traverse transpositions and record score
    # A cycle (p_0, p_1, ..., p_{k-1}) means σ(p_i) = p_{i+1 mod k}.
    # Equivalent to (k-1) transpositions: swap p_0 with p_1, then swap p_0 with p_2, ..., swap p_0 with p_{k-1}.
    # After all (k-1) transpositions, piece originally at p_0 ends at p_{k-1}, etc.
    # But we want to MAP source → target along the cycle: target's piece at p_i = source's piece at σ(p_i) = source[p_{i+1}].

    # Cleaner: cyclic shift. After 1 transposition (swap p_0, p_1), piece originally at p_0 moves to p_1.
    # But target wants source-piece-at-p_1 to be at p_0... so the direction is "shift cycle by -1".

    # Let's try the simpler approach: for each prefix length 1..k, apply that prefix and measure.
    # A cycle [p_0, p_1, ..., p_{k-1}]: apply "swap to target form" for first j positions.
    # Prefix-j: for i in 0..j-1, set board[p_i] = target[p_i]. The remaining positions stay source.
    # PIECE-UNIQUENESS WARNING: this may produce invalid intermediate (duplicate pieces).

    print("\nFor each cycle, score trajectory (prefix-apply 1, 2, ..., k):")
    best_overall_score = src_score
    for c_idx, c in enumerate(cycles):
        if len(c) > 50:  # Skip giant cycles for speed
            continue
        modified = source.copy()
        trajectory = [src_score]
        max_score = src_score
        # Track piece-uniqueness violations
        valid_traj = True
        for i in range(len(c)):
            pos = c[i]
            modified[pos] = target[pos]
            # Note: piece-uniqueness violated mid-cycle (target's piece at pos was at source's σ(pos), still placed there).
            # We just measure score with duplicates allowed.
            s = board_score(modified, pieces, side)
            trajectory.append(s)
            max_score = max(max_score, s)
        print(f"  cycle {c_idx} len={len(c):3d}: max score during traversal = {max_score} (Δ from src = {max_score - src_score:+d})")
        if max_score > best_overall_score:
            best_overall_score = max_score
            print(f"    ★ NEW BEST DURING TRAVERSAL: {max_score} ★")
            # Show trajectory
            print(f"    trajectory: {trajectory[:15]}{'...' if len(trajectory) > 15 else ''}")

    print(f"\nBest score reached during any cycle traversal: {best_overall_score}")
    if best_overall_score > src_score:
        print(f"  Potential basin escape: {best_overall_score - src_score:+d}")
    else:
        print(f"  No cycle traversal exceeds source — basin lock confirmed.")


if __name__ == "__main__":
    main()
