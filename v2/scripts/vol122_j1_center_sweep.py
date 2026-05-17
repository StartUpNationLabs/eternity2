#!/usr/bin/env python3
"""Vol-122 J1 v5 — CENTER-OUT SWEEP.

Per user suggestion: start chain from the middle band (band 7 for n=16),
expand outward in BOTH directions simultaneously.

Rationale: bidirectional symmetric failure at boundaries suggests
constraints accumulate from each anchor end. Starting in the middle:
- 7 perfect-able bands per direction → covers 14 bands of 15.
- Only outermost band (band 0 or band 14) may fail due to accumulated
  constraints + border constraint.

Algorithm:
1. Solve band 7 (rows 7, 8) with NO fixed top or bottom.
2. Chain UP from band 7 (band 6, 5, 4, 3, 2, 1, 0) using each band's
   top row as the next-upper band's bottom row.
3. Chain DOWN from band 7 (band 8, 9, 10, 11, 12, 13, 14) using each
   band's bottom row as the next-lower band's top row.
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
               fixed_top_pieces=None, fixed_bot_pieces=None,
               used_pieces=None, beam=2000, time_limit=120):
    """Solve band; optionally with fixed top OR bottom row."""
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

    if fixed_top_pieces is not None and 0 in fixed_top_pieces:
        ft_pid, ft_rot, ft_edges = fixed_top_pieces[0]
        top_options_col0 = [(ft_pid, ft_rot, ft_edges)] if valid_top((ft_pid, ft_rot, ft_edges), 0) else []
    else:
        top_options_col0 = [opt for opt in all_options if valid_top(opt, 0)]
    if fixed_bot_pieces is not None and 0 in fixed_bot_pieces:
        fb_pid, fb_rot, fb_edges = fixed_bot_pieces[0]
        bot_options_col0 = [(fb_pid, fb_rot, fb_edges)] if valid_bot((fb_pid, fb_rot, fb_edges), 0) else []
    else:
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
            return 0, None, None
        new_states = []
        if fixed_top_pieces is not None and j in fixed_top_pieces:
            ft_pid, ft_rot, ft_edges = fixed_top_pieces[j]
            valid_top_j = [(ft_pid, ft_rot, ft_edges)] if valid_top((ft_pid, ft_rot, ft_edges), j) else []
        else:
            valid_top_j = [opt for opt in all_options if valid_top(opt, j)]
        if fixed_bot_pieces is not None and j in fixed_bot_pieces:
            fb_pid, fb_rot, fb_edges = fixed_bot_pieces[j]
            valid_bot_j = [(fb_pid, fb_rot, fb_edges)] if valid_bot((fb_pid, fb_rot, fb_edges), j) else []
        else:
            valid_bot_j = [opt for opt in all_options if valid_bot(opt, j)]

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
    center_band = (side - 2) // 2  # = 7 for n=16
    print(f"puzzle: {puzzle_path.name} size={side}x{side}  beam={beam}  time/band={time_per_band}s")
    print(f"center_band: {center_band} (rows {center_band}, {center_band + 1})")

    full_board = {}
    used_pieces = set()
    total_score = 0

    # STEP 1: solve center band (no fixed top/bot)
    print(f"\n=== CENTER BAND {center_band} (rows {center_band}, {center_band + 1}) ===")
    t0 = time()
    score, tr, br = solve_band(
        pieces, side, center_band, center_band + 1,
        beam=beam, time_limit=time_per_band
    )
    print(f"  score: {score} / {3*side-2}  elapsed: {time() - t0:.1f}s")
    if tr is None:
        print(f"  CENTER BAND FAILED. Stopping.")
        return
    for c, (pid, rot) in enumerate(tr):
        full_board[(center_band, c)] = (pid, rot)
        used_pieces.add(pid)
    for c, (pid, rot) in enumerate(br):
        full_board[(center_band + 1, c)] = (pid, rot)
        used_pieces.add(pid)
    total_score += score

    # STEP 2: chain UP from center (band 6, 5, 4, ..., 0)
    fixed_bot = {}
    for col in range(side):
        pid, rot = full_board[(center_band, col)]
        fixed_bot[col] = (pid, rot, rotate(pieces[pid], rot))

    for band_idx in range(center_band - 1, -1, -1):
        top_row_idx = band_idx
        bot_row_idx = band_idx + 1
        print(f"\n=== UP BAND {band_idx} (rows {top_row_idx}, {bot_row_idx}) ===")
        t0 = time()
        score, tr, br = solve_band(
            pieces, side, top_row_idx, bot_row_idx,
            fixed_bot_pieces=fixed_bot,
            used_pieces=frozenset(used_pieces) - set(p for (p, _) in [full_board.get((bot_row_idx, c)) for c in range(side) if (bot_row_idx, c) in full_board] if p is not None),
            beam=beam, time_limit=time_per_band
        )
        print(f"  score: {score} / {3*side-2}  elapsed: {time() - t0:.1f}s")
        if tr is None:
            print(f"  UP BAND FAILED.")
            break
        for c, (pid, rot) in enumerate(tr):
            if (top_row_idx, c) not in full_board:
                full_board[(top_row_idx, c)] = (pid, rot)
                used_pieces.add(pid)
        total_score += score
        fixed_bot = {col: (full_board[(top_row_idx, col)][0], full_board[(top_row_idx, col)][1], rotate(pieces[full_board[(top_row_idx, col)][0]], full_board[(top_row_idx, col)][1])) for col in range(side)}

    # STEP 3: chain DOWN from center (band 8, 9, ..., 14)
    fixed_top = {}
    for col in range(side):
        pid, rot = full_board[(center_band + 1, col)]
        fixed_top[col] = (pid, rot, rotate(pieces[pid], rot))

    for band_idx in range(center_band + 1, side - 1):
        top_row_idx = band_idx
        bot_row_idx = band_idx + 1
        print(f"\n=== DOWN BAND {band_idx} (rows {top_row_idx}, {bot_row_idx}) ===")
        t0 = time()
        score, tr, br = solve_band(
            pieces, side, top_row_idx, bot_row_idx,
            fixed_top_pieces=fixed_top,
            used_pieces=frozenset(used_pieces) - set(p for (p, _) in [full_board.get((top_row_idx, c)) for c in range(side) if (top_row_idx, c) in full_board] if p is not None),
            beam=beam, time_limit=time_per_band
        )
        print(f"  score: {score} / {3*side-2}  elapsed: {time() - t0:.1f}s")
        if tr is None:
            print(f"  DOWN BAND FAILED.")
            break
        for c, (pid, rot) in enumerate(br):
            if (bot_row_idx, c) not in full_board:
                full_board[(bot_row_idx, c)] = (pid, rot)
                used_pieces.add(pid)
        total_score += score
        fixed_top = {col: (full_board[(bot_row_idx, col)][0], full_board[(bot_row_idx, col)][1], rotate(pieces[full_board[(bot_row_idx, col)][0]], full_board[(bot_row_idx, col)][1])) for col in range(side)}

    print(f"\n=== TOTAL ===")
    print(f"sum of band scores: {total_score}")
    print(f"full board placements: {len(full_board)}")

    placement = []
    for (r, c), (pid, rot) in sorted(full_board.items()):
        placement.append({"pos": r * side + c, "piece_id": pid, "rotation": rot})
    out_path = Path("output/vol-122/j1_center_sweep.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump({"source": "vol122_j1_center_sweep", "placement": placement}, f, indent=2)
    print(f"wrote: {out_path}")


if __name__ == "__main__":
    main()
