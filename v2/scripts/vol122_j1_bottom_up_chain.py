#!/usr/bin/env python3
"""Vol-122 J1 v4 — Bottom-Up Chain.

Solve bands in REVERSE order: band 14 first (rows 14, 15 with bottom border),
then band 13 (rows 13, 14 — row 14's TOP edges fixed from band 14), etc.

Hypothesis: bottom-border row-15 has tight color constraints that propagate
upward. Solving bottom-first gives the chain a "spine" of constraints to
follow upward.
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


def solve_band(pieces, side, top_row_idx, bot_row_idx,
               fixed_bot_pieces=None, used_pieces=None,
               beam=2000, time_limit=120):
    """Solve band with BOT row fixed (= bottom-up direction). Returns (score, top_row, bot_row)."""
    n = len(pieces)
    is_top_row = (top_row_idx == 0)
    is_bot_row = (bot_row_idx == side - 1)
    used_pieces = used_pieces or frozenset()

    all_options = []
    for pid in range(n):
        if pid in used_pieces: continue
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

    # Bottom row is fixed in this variant. Top row is free (but must V-match bot at each col).
    if fixed_bot_pieces is not None and 0 in fixed_bot_pieces:
        fb_pid, fb_rot, fb_edges = fixed_bot_pieces[0]
        bot_options_col0 = [(fb_pid, fb_rot, fb_edges)] if valid_bot((fb_pid, fb_rot, fb_edges), 0) else []
    else:
        bot_options_col0 = [opt for opt in all_options if valid_bot(opt, 0)]
    top_options_col0 = [opt for opt in all_options if valid_top(opt, 0)]

    # State per col: (top_pid, top_rot, top_edges, bot_pid, bot_rot, bot_edges, used, score, parent_idx)
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
            return 0, None, None
        new_states = []
        if fixed_bot_pieces is not None and j in fixed_bot_pieces:
            fb_pid, fb_rot, fb_edges = fixed_bot_pieces[j]
            valid_bot_j = [(fb_pid, fb_rot, fb_edges)] if valid_bot((fb_pid, fb_rot, fb_edges), j) else []
        else:
            valid_bot_j = [opt for opt in all_options if valid_bot(opt, j)]
        valid_top_j = [opt for opt in all_options if valid_top(opt, j)]

        top_by_L = defaultdict(list)
        for opt in valid_top_j: top_by_L[opt[2][3]].append(opt)
        bot_by_L = defaultdict(list)
        for opt in valid_bot_j: bot_by_L[opt[2][3]].append(opt)

        for parent_idx, s in enumerate(states_per_col[-1]):
            tp, tr, te, bp, br, be, used, sc, _ = s
            for ot in top_by_L.get(te[1], []):
                if ot[0] in used: continue
                for ob in bot_by_L.get(be[1], []):
                    if ob[0] in used or ob[0] == ot[0]: continue
                    new_sc = sc + (1 if te[1] != 0 else 0) + (1 if be[1] != 0 else 0) \
                           + (1 if (ot[2][2] == ob[2][0] and ot[2][2] != 0) else 0)
                    new_used = used | {ot[0], ob[0]}
                    new_states.append((ot[0], ot[1], ot[2], ob[0], ob[1], ob[2], new_used, new_sc, parent_idx))
        new_states.sort(key=lambda s: -s[7])
        states_per_col.append(new_states[:beam])
        if not states_per_col[-1]:
            return 0, None, None

    best = states_per_col[-1][0]
    top_row = [None] * side
    bot_row = [None] * side
    cur = best
    cur_col = side - 1
    while cur_col >= 0:
        tp, tr, _te, bp, br, _be, _used, _sc, parent_idx = cur
        top_row[cur_col] = (tp, tr)
        bot_row[cur_col] = (bp, br)
        if cur_col == 0: break
        cur = states_per_col[cur_col - 1][parent_idx]
        cur_col -= 1
    return best[7], top_row, bot_row


def main():
    puzzle_path = Path(sys.argv[1] if len(sys.argv) > 1 else "../data/puzzles/size_16_official_eternity.csv")
    beam = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    time_per_band = int(sys.argv[3]) if len(sys.argv) > 3 else 120

    pieces = load_puzzle(puzzle_path)
    side = int(len(pieces) ** 0.5)
    print(f"puzzle: {puzzle_path.name} size={side}x{side}  beam={beam}  time/band={time_per_band}s")

    full_board = {}
    used_pieces = set()
    fixed_bot = None
    total_score = 0

    # Process bands in REVERSE order: band (n-2) down to band 0
    for band_idx in range(side - 2, -1, -1):
        top_row = band_idx
        bot_row = band_idx + 1
        print(f"\n=== BAND {band_idx} (rows {top_row}, {bot_row}) [bottom-up] ===")
        t0 = time()
        score, tr, br = solve_band(
            pieces, side, top_row, bot_row,
            fixed_bot_pieces=fixed_bot,
            used_pieces=frozenset(used_pieces),
            beam=beam, time_limit=time_per_band
        )
        elapsed = time() - t0
        max_band = 3 * side - 2
        print(f"  score: {score} / {max_band}  elapsed: {elapsed:.1f}s")
        if tr is None:
            print(f"  BAND FAILED. Stopping.")
            break

        new_pieces = 0
        for c, (pid, rot) in enumerate(tr):
            if (top_row, c) not in full_board:
                full_board[(top_row, c)] = (pid, rot)
                used_pieces.add(pid)
                new_pieces += 1
        for c, (pid, rot) in enumerate(br):
            if (bot_row, c) not in full_board:
                full_board[(bot_row, c)] = (pid, rot)
                used_pieces.add(pid)
                new_pieces += 1
        total_score += score
        print(f"  added {new_pieces} new pieces (board total: {len(full_board)})")

        # Set fixed_bot for next (upper) band = THIS band's TOP row
        fixed_bot = {}
        for col in range(side):
            if (top_row, col) in full_board:
                pid, rot = full_board[(top_row, col)]
                fixed_bot[col] = (pid, rot, rotate(pieces[pid], rot))

    print(f"\n=== TOTAL ===")
    print(f"sum of band scores: {total_score}")
    print(f"full board placements: {len(full_board)}")

    placement = []
    for (r, c), (pid, rot) in sorted(full_board.items()):
        pos = r * side + c
        placement.append({"pos": pos, "piece_id": pid, "rotation": rot})
    out_path = Path("output/vol-122/j1_bottom_up.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump({"source": "vol122_j1_bottom_up", "placement": placement}, f, indent=2)
    print(f"wrote: {out_path}")


if __name__ == "__main__":
    main()
