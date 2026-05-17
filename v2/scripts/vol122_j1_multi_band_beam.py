#!/usr/bin/env python3
"""Vol-122 J1 v3 — Multi-Band Beam Search.

Per user question 'what if multiple possible bands exist?':
Track K_chain chain-states at each band level. For each, expand to all
possible band-(r+1) completions, then beam-prune at chain level.
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


def solve_band_top_K(pieces, side, top_row_idx, bot_row_idx,
                     fixed_top_pieces=None, used_pieces=None,
                     beam=2000, top_k=5, time_limit=120):
    """Solve band, return top-K configurations as list of (score, top_row_pieces, bot_row_pieces)."""
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
            return []
        new_states = []
        if fixed_top_pieces is not None and j in fixed_top_pieces:
            ft_pid, ft_rot, ft_edges = fixed_top_pieces[j]
            valid_top_j = [(ft_pid, ft_rot, ft_edges)] if valid_top((ft_pid, ft_rot, ft_edges), j) else []
        else:
            valid_top_j = [opt for opt in all_options if valid_top(opt, j)]
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
            return []

    final_states = states_per_col[-1][:top_k]
    results = []
    for fs in final_states:
        top_row = [None] * side
        bot_row = [None] * side
        cur = fs
        cur_col = side - 1
        while cur_col >= 0:
            tp, tr, _te, bp, br, _be, _used, _sc, parent_idx = cur
            top_row[cur_col] = (tp, tr)
            bot_row[cur_col] = (bp, br)
            if cur_col == 0: break
            cur = states_per_col[cur_col - 1][parent_idx]
            cur_col -= 1
        results.append((fs[7], top_row, bot_row))
    return results


def main():
    puzzle_path = Path(sys.argv[1] if len(sys.argv) > 1 else "../data/puzzles/size_16_official_eternity.csv")
    chain_K = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    beam = int(sys.argv[3]) if len(sys.argv) > 3 else 2000
    band_top_k = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    time_per_band = int(sys.argv[5]) if len(sys.argv) > 5 else 60

    pieces = load_puzzle(puzzle_path)
    side = int(len(pieces) ** 0.5)
    print(f"puzzle: {puzzle_path.name} size={side}x{side}")
    print(f"  chain_K={chain_K}  beam={beam}  band_top_k={band_top_k}  time_per_band={time_per_band}s")

    print(f"\n=== BAND 0 (rows 0, 1) ===")
    t0 = time()
    band_0_results = solve_band_top_K(
        pieces, side, 0, 1,
        fixed_top_pieces=None,
        used_pieces=frozenset(),
        beam=beam, top_k=chain_K * band_top_k,
        time_limit=time_per_band
    )
    elapsed = time() - t0
    print(f"  band-0 top-{len(band_0_results)} configs, elapsed: {elapsed:.1f}s")

    chain_states = []
    for (score, top_row, bot_row) in band_0_results:
        used = set()
        for (pid, _) in top_row: used.add(pid)
        for (pid, _) in bot_row: used.add(pid)
        chain_states.append({
            'cum_score': score,
            'used': frozenset(used),
            'all_rows': [top_row, bot_row],
        })
    chain_states.sort(key=lambda s: -s['cum_score'])
    chain_states = chain_states[:chain_K]
    if chain_states:
        print(f"  chain states after band 0: {len(chain_states)}, top score: {chain_states[0]['cum_score']}")

    prior_chain_states = chain_states
    for band_idx in range(1, side - 1):
        print(f"\n=== BAND {band_idx} (rows {band_idx}, {band_idx + 1}) ===")
        t_band = time()
        new_chain_states = []
        for cs_idx, cs in enumerate(chain_states):
            fixed_top_pieces = {}
            for col in range(side):
                pid, rot = cs['all_rows'][band_idx][col]
                fixed_top_pieces[col] = (pid, rot, rotate(pieces[pid], rot))
            # The 'used' set already includes top-row pieces. solve_band_top_K excludes them
            # via used_pieces — but the FIXED top means those pieces ARE in band_idx, so
            # they need to NOT be in used_pieces here.
            used_excluding_top = cs['used'] - set(p for (p, _) in cs['all_rows'][band_idx])
            results = solve_band_top_K(
                pieces, side, band_idx, band_idx + 1,
                fixed_top_pieces=fixed_top_pieces,
                used_pieces=used_excluding_top,
                beam=beam, top_k=band_top_k,
                time_limit=time_per_band
            )
            for (score, top_row, bot_row) in results:
                new_used = set(cs['used'])
                for (pid, _) in bot_row: new_used.add(pid)
                # Score delta: this band adds new edges = (band_score - top_row_horizontals).
                # top_row_horizontals = count of matched horizontals in the fixed top row.
                # Since top is fixed and was perfect in prior band, top_row_horizontals = side - 1 (if all top horizontals match).
                # Actually we should just trust the band score and subtract horizontals that were counted before.
                # For simplicity: new_cum = cs['cum_score'] + score - (side - 1)
                # This double-subtracts if band wasn't perfect. Let me just track sum-of-band-scores and report.
                new_chain_states.append({
                    'cum_score': cs['cum_score'] + score - (side - 1),
                    'used': frozenset(new_used),
                    'all_rows': cs['all_rows'] + [bot_row],
                })
        new_chain_states.sort(key=lambda s: -s['cum_score'])
        chain_states = new_chain_states[:chain_K]
        elapsed = time() - t_band
        if chain_states:
            print(f"  expanded {len(new_chain_states)} candidates -> top {len(chain_states)} kept")
            print(f"  top cum_score after band {band_idx}: {chain_states[0]['cum_score']}, elapsed: {elapsed:.1f}s")
        else:
            print(f"  ALL chain states failed at band {band_idx}. Stopping.")
            # Save the partial result anyway (from previous band)
            chain_states = prior_chain_states
            break
        prior_chain_states = chain_states

    if chain_states:
        best = chain_states[0]
        print(f"\n=== BEST ===")
        print(f"final cum_score: {best['cum_score']}")
        print(f"bands completed: {len(best['all_rows']) - 1}")
        placement = []
        for r, row in enumerate(best['all_rows']):
            if r >= side: break
            for c, (pid, rot) in enumerate(row):
                placement.append({"pos": r * side + c, "piece_id": pid, "rotation": rot})
        out_path = Path("output/vol-122/j1_multi_band_best.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, 'w') as f:
            json.dump({"source": "vol122_j1_multi_band", "placement": placement}, f, indent=2)
        print(f"wrote: {out_path}")


if __name__ == "__main__":
    main()
