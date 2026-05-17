#!/usr/bin/env python3
"""Vol-122 J1 — Double-Row Column-DP with Beam Search PoC.

Per design at vault/concepts/j1-column-dp-design.md.

Solve E2 as 2-row sliding band, column-by-column with beam pruning.
"""

from __future__ import annotations
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


def solve_band(pieces, side, top_row_idx, bot_row_idx, fixed_top=None, beam=10000, time_limit=120):
    """Solve a single 2-row band at rows (top_row_idx, bot_row_idx)."""
    n = len(pieces)
    is_top_row = (top_row_idx == 0)
    is_bot_row = (bot_row_idx == side - 1)

    all_options = []
    for pid in range(n):
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

    top_options_col0 = [opt for opt in all_options if valid_top(opt, 0)]
    bot_options_col0 = [opt for opt in all_options if valid_bot(opt, 0)]

    # State: (top_pid, top_rot, top_edges, bot_pid, bot_rot, bot_edges, used_frozenset, score)
    states = []
    for ot in top_options_col0:
        for ob in bot_options_col0:
            if ot[0] == ob[0]: continue
            score = 0
            if ot[2][2] == ob[2][0] and ot[2][2] != 0:
                score += 1
            states.append((ot[0], ot[1], ot[2], ob[0], ob[1], ob[2], frozenset({ot[0], ob[0]}), score))
    states.sort(key=lambda s: -s[7])
    states = states[:beam]
    print(f"  col 0: {len(states)} states, max score {max(s[7] for s in states) if states else 0}")

    t_start = time()
    for j in range(1, side):
        if time() - t_start > time_limit:
            print(f"  TIME LIMIT at col {j}")
            break
        new_states = []
        valid_top_j = [opt for opt in all_options if valid_top(opt, j)]
        valid_bot_j = [opt for opt in all_options if valid_bot(opt, j)]

        top_by_L = defaultdict(list)
        for opt in valid_top_j:
            top_by_L[opt[2][3]].append(opt)
        bot_by_L = defaultdict(list)
        for opt in valid_bot_j:
            bot_by_L[opt[2][3]].append(opt)

        for s in states:
            tp, tr, te, bp, br, be, used, sc = s
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
                    new_states.append((ot[0], ot[1], ot[2], ob[0], ob[1], ob[2], new_used, new_sc))

        new_states.sort(key=lambda s: -s[7])
        states = new_states[:beam]
        if states:
            print(f"  col {j}: {len(new_states)} expanded -> {len(states)} kept, max score {states[0][7]}")
        else:
            print(f"  col {j}: NO STATES (dead-end)")
            return 0, None

    if not states: return 0, None
    best = states[0]
    return best[7], best


def main():
    if len(sys.argv) < 2:
        candidates = [
            "../data/generated/size_4_colors_2_56adf9a3.csv",
            "../data/generated/size_4_colors_4_e2d68b48.csv",
            "../data/generated/size_5_colors_3_4ab6bb20.csv",
            "../data/generated/size_5_colors_4_3347f2df.csv",
            "../data/generated/size_6_colors_4_9f5c889b.csv",
            "../data/generated/size_6_colors_5_09ed3e44.csv",
            "../data/generated/size_7_colors_4_9584332a.csv",
            "../data/generated/size_8_colors_5_e6520f51.csv",
        ]
    else:
        candidates = sys.argv[1:]
    beam = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    time_limit = int(sys.argv[3]) if len(sys.argv) > 3 else 30

    for path in candidates:
        p = Path(path)
        if not p.exists(): continue
        pieces = load_puzzle(p)
        side = int(len(pieces) ** 0.5)
        if side * side != len(pieces): continue
        print(f"\n=== {p.name} ({side}x{side}) beam={beam} time_limit={time_limit}s ===")
        t0 = time()
        score, best_state = solve_band(pieces, side, 0, 1, beam=beam, time_limit=time_limit)
        elapsed = time() - t0
        max_possible = 3 * side - 2  # 1 vert + 2 * (side-1) horiz at most
        print(f"  band 0 score: {score} / {max_possible} max possible")
        print(f"  elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
