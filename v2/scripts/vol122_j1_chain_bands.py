#!/usr/bin/env python3
"""Vol-122 J1 v2 — Chain bands across full canonical board.

Extends the column-DP PoC to:
1. Reconstruct full band assignment via backtrack pointers.
2. Chain band 0 -> band 1 -> ... -> band (n-2) using each band's bottom
   row as the next band's fixed top.
3. Output a full board JSON and score it.
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from time import time
from collections import defaultdict


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


def solve_band_with_trace(pieces, side, top_row_idx, bot_row_idx, fixed_top_pieces=None,
                          used_pieces=None, beam=10000, time_limit=120):
    """Solve a single 2-row band with backtrack pointers.

    fixed_top_pieces: dict {col: (pid, rot, edges)} — top row already determined.
    used_pieces: frozenset of pieces already used (e.g., by prior bands).
    Returns: (best_score, assignment) where assignment is dict {(row, col): (pid, rot)}.
    """
    n = len(pieces)
    is_top_row = (top_row_idx == 0)
    is_bot_row = (bot_row_idx == side - 1)
    used_pieces = used_pieces or frozenset()

    all_options = []
    for pid in range(n):
        if pid in used_pieces:
            continue
        for rot in range(4):
            e = rotate(pieces[pid], rot)
            all_options.append((pid, rot, e))

    def valid_top(opt, col):
        pid, rot, e = opt
        if is_top_row and e[0] != 0: return False
        if not is_top_row and e[0] == 0: return False
        if col == 0 and e[3] != 0: return False
        if col != 0 and e[3] == 0: return False
        if col == side - 1 and e[1] != 0: return False
        if col != side - 1 and e[1] == 0: return False
        return True

    def valid_bot(opt, col):
        pid, rot, e = opt
        if is_bot_row and e[2] != 0: return False
        if not is_bot_row and e[2] == 0: return False
        if col == 0 and e[3] != 0: return False
        if col != 0 and e[3] == 0: return False
        if col == side - 1 and e[1] != 0: return False
        if col != side - 1 and e[1] == 0: return False
        return True

    # State at column j: ((tp, tr, te, bp, br, be), used_added_set, score, parent_state_idx)
    # We store all states across columns + parent pointers for backtrack.
    # all_states: list of lists [column → list of state tuples]
    # Each state: (tp, tr, te, bp, br, be, used_added, score, parent_idx)
    # parent_idx = index into previous column's states (None for col 0)

    # Initial column
    if fixed_top_pieces is not None and 0 in fixed_top_pieces:
        ft_pid, ft_rot, ft_edges = fixed_top_pieces[0]
        top_options_col0 = [(ft_pid, ft_rot, ft_edges)] if valid_top((ft_pid, ft_rot, ft_edges), 0) else []
    else:
        top_options_col0 = [opt for opt in all_options if valid_top(opt, 0)]
    bot_options_col0 = [opt for opt in all_options if valid_bot(opt, 0)]

    states_per_col = [[]]
    for ot in top_options_col0:
        for ob in bot_options_col0:
            if ot[0] == ob[0]: continue
            score = 0
            if ot[2][2] == ob[2][0] and ot[2][2] != 0:
                score += 1
            used_added = frozenset({ot[0], ob[0]})
            states_per_col[0].append((ot[0], ot[1], ot[2], ob[0], ob[1], ob[2], used_added, score, None))

    states_per_col[0].sort(key=lambda s: -s[7])
    states_per_col[0] = states_per_col[0][:beam]

    t_start = time()
    for j in range(1, side):
        if time() - t_start > time_limit:
            print(f"  TIME LIMIT at col {j}")
            return 0, None
        new_states = []

        if fixed_top_pieces is not None and j in fixed_top_pieces:
            ft_pid, ft_rot, ft_edges = fixed_top_pieces[j]
            valid_top_j = [(ft_pid, ft_rot, ft_edges)] if valid_top((ft_pid, ft_rot, ft_edges), j) else []
        else:
            valid_top_j = [opt for opt in all_options if valid_top(opt, j)]
        valid_bot_j = [opt for opt in all_options if valid_bot(opt, j)]

        top_by_L = defaultdict(list)
        for opt in valid_top_j:
            top_by_L[opt[2][3]].append(opt)
        bot_by_L = defaultdict(list)
        for opt in valid_bot_j:
            bot_by_L[opt[2][3]].append(opt)

        for parent_idx, s in enumerate(states_per_col[-1]):
            tp, tr, te, bp, br, be, used, sc, _parent = s
            required_top_L = te[1]
            required_bot_L = be[1]
            for ot in top_by_L.get(required_top_L, []):
                if ot[0] in used: continue
                for ob in bot_by_L.get(required_bot_L, []):
                    if ob[0] in used or ob[0] == ot[0]: continue
                    new_sc = sc
                    if required_top_L != 0:
                        new_sc += 1
                    if required_bot_L != 0:
                        new_sc += 1
                    if ot[2][2] == ob[2][0] and ot[2][2] != 0:
                        new_sc += 1
                    new_used = used | {ot[0], ob[0]}
                    new_states.append((ot[0], ot[1], ot[2], ob[0], ob[1], ob[2], new_used, new_sc, parent_idx))

        new_states.sort(key=lambda s: -s[7])
        states_per_col.append(new_states[:beam])
        if states_per_col[-1]:
            print(f"  col {j}: {len(new_states)} expanded -> {len(states_per_col[-1])} kept, max score {states_per_col[-1][0][7]}")
        else:
            print(f"  col {j}: NO STATES")
            return 0, None

    if not states_per_col[-1]:
        return 0, None
    best = states_per_col[-1][0]
    final_score = best[7]

    # Backtrack to reconstruct assignment
    assignment = {}  # (row, col) -> (pid, rot)
    cur_state = best
    cur_col = side - 1
    while cur_col >= 0:
        tp, tr, _te, bp, br, _be, _used, _sc, parent_idx = cur_state
        assignment[(top_row_idx, cur_col)] = (tp, tr)
        assignment[(bot_row_idx, cur_col)] = (bp, br)
        if cur_col == 0:
            break
        cur_state = states_per_col[cur_col - 1][parent_idx]
        cur_col -= 1

    return final_score, assignment


def main():
    puzzle_path = Path(sys.argv[1] if len(sys.argv) > 1 else "../data/puzzles/size_16_official_eternity.csv")
    beam = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    time_per_band = int(sys.argv[3]) if len(sys.argv) > 3 else 90

    pieces = load_puzzle(puzzle_path)
    side = int(len(pieces) ** 0.5)
    print(f"puzzle: {puzzle_path.name} size={side}x{side}  beam={beam}  time_per_band={time_per_band}s")

    full_board = {}  # (row, col) -> (pid, rot)
    used_pieces = set()
    fixed_top = None

    total_score = 0
    for band_idx in range(side - 1):
        top_row = band_idx
        bot_row = band_idx + 1
        print(f"\n=== BAND {band_idx} (rows {top_row}, {bot_row}) ===")
        t0 = time()
        score, assignment = solve_band_with_trace(
            pieces, side, top_row, bot_row,
            fixed_top_pieces=fixed_top,
            used_pieces=frozenset(used_pieces),
            beam=beam,
            time_limit=time_per_band
        )
        elapsed = time() - t0
        max_band = 3 * side - 2
        print(f"  score: {score} / {max_band}  elapsed: {elapsed:.1f}s")

        if assignment is None:
            print(f"  BAND FAILED. Stopping.")
            break

        # Add to full board (overwrite top row if already set from prior band)
        new_pieces_count = 0
        for (r, c), (pid, rot) in assignment.items():
            if (r, c) not in full_board:
                full_board[(r, c)] = (pid, rot)
                used_pieces.add(pid)
                new_pieces_count += 1
            else:
                # Should match the fixed_top row from prior band
                if full_board[(r, c)] != (pid, rot):
                    print(f"  WARNING: conflicting placement at ({r}, {c}): prior={full_board[(r,c)]} new={(pid, rot)}")

        print(f"  added {new_pieces_count} new pieces (total board: {len(full_board)})")
        total_score += score

        # Set fixed_top for next band = THIS band's bottom row
        fixed_top = {}
        for col in range(side):
            if (bot_row, col) in full_board:
                pid, rot = full_board[(bot_row, col)]
                fixed_top[col] = (pid, rot, rotate(pieces[pid], rot))

    print(f"\n=== TOTAL ===")
    print(f"sum of band scores: {total_score}")
    print(f"full board placements: {len(full_board)}")

    # Save board
    out_path = Path("output/vol-122/j1_chain_full_board.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    placement = []
    for (r, c), (pid, rot) in sorted(full_board.items()):
        pos = r * side + c
        placement.append({"pos": pos, "piece_id": pid, "rotation": rot})
    with open(out_path, 'w') as f:
        json.dump({
            "source": "vol122_j1_column_dp_chain",
            "n_placed": len(placement),
            "placement": placement,
        }, f, indent=2)
    print(f"wrote: {out_path}")


if __name__ == "__main__":
    main()
