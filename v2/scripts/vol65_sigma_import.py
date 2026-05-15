#!/usr/bin/env python3
"""Vol-65 — σ-cycle import from oracle (McGavin 469) to current board.

For each cycle C in the σ-decomposition of (current → oracle):
1. Apply only C: at positions in C, place the oracle's (piece, rotation).
2. Score the resulting board. Report score delta.

Variants:
- Single cycle (test each independently)
- Cumulative cycles (apply smallest first, then 2nd, ...)
- Cycle subset combinations (2^|cycles| possibilities — limit if too many)

Goal: find a cycle subset whose application moves the board to a
DIFFERENT score-level set, ideally HIGHER. If yes, we've discovered
a cycle-subset that crosses orbit boundaries.

CAVEAT: a cycle from σ_AB (A → B) applied alone often produces a
piece-uniqueness violation (a piece may end up duplicated) because
the cycle removes pieces from their A-positions and places oracle's
pieces, possibly creating duplicates with pieces NOT in any cycle.

For correctness, applying cycle C requires:
- Remove the current pieces at positions in C
- Place oracle's pieces at positions in C
This is OK only if the pieces moved IN (oracle's) don't ALREADY
appear OUTSIDE the cycle in the current board. Need to check.

A "safe cycle" is one where the set of pieces moved in == set of
pieces moved out (i.e., the cycle is closed within itself).
By definition, σ-cycles ARE closed in this sense — the cycle
permutes a fixed set of piece-IDs among themselves.
"""

import collections
import json
import urllib.parse
from pathlib import Path

PUZZLE_CSV = "../data/puzzles/size_16_official_eternity.csv"


def load_canonical_pieces():
    BORDER_RAW = 65535
    pieces = []
    with open(PUZZLE_CSV) as f:
        size = int(f.readline().strip())
        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            def col(s):
                v = int(s.strip(), 2)
                return 0 if v == BORDER_RAW else v
            top = col(parts[0])
            right = col(parts[1])
            bottom = col(parts[2])
            left = col(parts[3])
            pieces.append((top, right, bottom, left))
    return pieces


def rotate(edges, k):
    n, e, s, w = edges
    if k == 0: return (n, e, s, w)
    if k == 1: return (w, n, e, s)
    if k == 2: return (s, w, n, e)
    if k == 3: return (e, s, w, n)


def load_placement(path):
    with open(path) as f:
        d = json.load(f)
    arr = d.get("placement", [])
    pos_to_pid_rot = {}
    pid_to_pos = {}
    for idx, item in enumerate(arr):
        if item is None: continue
        pos = item.get("pos", idx)
        pid = item["piece_id"]
        rot = item["rotation"]
        pos_to_pid_rot[pos] = (pid, rot)
        pid_to_pos[pid] = pos
    return pos_to_pid_rot, pid_to_pos


def score_board(pos_to_pid_rot, pieces):
    """Compute matched-edges score from placement."""
    grid = [[None] * 16 for _ in range(16)]
    for pos, (pid, rot) in pos_to_pid_rot.items():
        r, c = divmod(pos, 16)
        grid[r][c] = rotate(pieces[pid], rot)
    matched = 0
    for r in range(16):
        for c in range(15):
            if grid[r][c] is None or grid[r][c + 1] is None:
                continue
            if grid[r][c][1] == grid[r][c + 1][3]:
                matched += 1
    for r in range(15):
        for c in range(16):
            if grid[r][c] is None or grid[r + 1][c] is None:
                continue
            if grid[r][c][2] == grid[r + 1][c][0]:
                matched += 1
    return matched


def sigma_cycles(p1_pid_to_pos, p2_pid_to_pos):
    """Compute σ-cycles between board1 (current) and board2 (oracle).

    Returns list of cycles, each cycle = list of positions in cyclic order
    such that position[i]'s piece in board1 == position[(i+1) % k]'s piece
    in board2.

    Actually: σ at POSITION level. σ(pos) = oracle's position of the piece
    currently at pos. Trace cycles by following σ.
    """
    # Build piece-id at position for current
    p1_pos_to_pid = {pos: pid for pid, pos in p1_pid_to_pos.items()}
    sigma = {}
    for pos, pid in p1_pos_to_pid.items():
        oracle_pos = p2_pid_to_pos.get(pid)
        if oracle_pos is not None and oracle_pos != pos:
            sigma[pos] = oracle_pos
    visited = set()
    cycles = []
    for start in sigma:
        if start in visited: continue
        c = []
        cur = start
        while cur in sigma and cur not in visited:
            visited.add(cur); c.append(cur); cur = sigma[cur]
        if len(c) >= 2:
            cycles.append(c)
    return cycles


def apply_cycle(pos_to_pid_rot, cycle_positions, oracle_pos_to_pid_rot):
    """Return a new placement where positions in cycle take oracle values."""
    new = dict(pos_to_pid_rot)
    for pos in cycle_positions:
        new[pos] = oracle_pos_to_pid_rot[pos]
    return new


def validate_placement(pos_to_pid_rot):
    """Return (is_valid, n_unique_pieces, n_total)."""
    pids = [pid for pid, _ in pos_to_pid_rot.values()]
    return (len(set(pids)) == len(pids), len(set(pids)), len(pids))


def main():
    pieces = load_canonical_pieces()

    current_path = "output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json"
    oracle_path = "output/vol-65/mcgavin_469.json"

    cur_pos, cur_pid = load_placement(current_path)
    or_pos, or_pid = load_placement(oracle_path)
    cur_score = score_board(cur_pos, pieces)
    or_score = score_board(or_pos, pieces)
    print(f"Current: {current_path} → score {cur_score}")
    print(f"Oracle:  {oracle_path} → score {or_score}")

    cycles = sigma_cycles(cur_pid, or_pid)
    cycles.sort(key=len)
    print(f"\n{len(cycles)} σ-cycles, lengths: {[len(c) for c in cycles]}")
    print()

    # Apply each cycle alone
    print(f"{'cycle':<6} | {'len':>4} | {'valid':>5} | {'score':>5} | {'Δ':>4} | positions (first 6)")
    print("-" * 80)
    for i, cycle in enumerate(cycles):
        new_pos = apply_cycle(cur_pos, cycle, or_pos)
        valid, unique, total = validate_placement(new_pos)
        score = score_board(new_pos, pieces) if valid else 0
        delta = score - cur_score if valid else 0
        sign = "+" if delta > 0 else ""
        valid_str = "✓" if valid else "✗"
        print(f"C{i:<5} | {len(cycle):>4} | {valid_str:>5} | "
              f"{score if valid else '?':>5} | {sign+str(delta) if valid else 'inv':>4} | {cycle[:6]}")

    # Cumulative (apply cycles smallest → largest)
    print()
    print(f"=== CUMULATIVE (smallest cycle first) ===")
    print(f"{'step':<5} | {'+cyc-len':>9} | {'total-cells':>11} | {'score':>5} | {'Δ':>4}")
    new_pos = dict(cur_pos)
    cumul_cells = 0
    for i, cycle in enumerate(cycles):
        new_pos = apply_cycle(new_pos, cycle, or_pos)
        cumul_cells += len(cycle)
        valid, _, _ = validate_placement(new_pos)
        score = score_board(new_pos, pieces) if valid else 0
        delta = score - cur_score if valid else 0
        sign = "+" if delta > 0 else ""
        print(f"after-C{i:<3} | {len(cycle):>9} | {cumul_cells:>11} | "
              f"{score if valid else '?':>5} | {sign+str(delta) if valid else 'inv':>4}")


if __name__ == "__main__":
    main()
