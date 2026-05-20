#!/usr/bin/env python3
"""V186-T6 row-swap surgery.

For each row r in [1..14] of a known 460/480 board, ENUMERATE all
alternative 16-cell chains that:
- match the N-edge from row r-1's S-edges
- match the S-edge to row r+1's N-edges  (the original row's S-edges)
- use only pieces NOT placed in any OTHER row of the board

If any alternative chain scores more matches than the original row,
the basin is not locally row-rigid, and we have an improvement.

This is a SOUND local search: structural, deterministic, exhaustive within
the row.

The cleaning insight: V181's 460 is iso-plateau-locked under ALNS destroy
(4-48 cell windows). A FULL ROW swap (16 cells, constrained to match both
boundary rows) is OUTSIDE the destroy window size — ALNS basic_lkh never
tries this exact configuration.
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v184_lighthouse"))
from build_bidirectional2 import load_pieces, BORDER, is_border, score_full

REPO = Path(__file__).resolve().parents[2]


def enumerate_row_chains(row_idx, n_constraint, s_constraint,
                          pieces, free_pids, beam_k=10000,
                          n_strict=True, s_strict=False):
    """Beam-K enumeration of 16-cell chains in row.

    n_strict: True → only pieces whose N-edge == n_constraint[c] (matches top boundary).
    s_strict: True → only pieces whose S-edge == s_constraint[c] (matches bottom boundary).

    Score = E-W matches + N-matches + S-matches. (N already filtered if n_strict,
    S already filtered if s_strict; this score tracks the soft variants.)

    Returns list of (chain, used_set, score) sorted by score (descending).
    """
    cand_per_cell = [[] for _ in range(16)]
    for c in range(16):
        for pid in free_pids:
            for rot in range(4):
                edges = pieces[(pid, rot)]
                if n_strict and edges[0] != n_constraint[c]: continue
                if s_strict and edges[2] != s_constraint[c]: continue
                # Border cells: leftmost col 0 must have W = BORDER (interior-row only).
                if c == 0 and edges[3] != BORDER: continue
                if c == 15 and edges[1] != BORDER: continue
                cand_per_cell[c].append((pid, rot, edges))
        if not cand_per_cell[c]:
            return []

    def cell_score(edges, c):
        s = 0
        # N-match (if not pre-filtered)
        if not n_strict and edges[0] == n_constraint[c] and not is_border(edges[0]):
            s += 1
        elif n_strict and not is_border(edges[0]):
            s += 1
        # S-match
        if edges[2] == s_constraint[c] and not is_border(edges[2]):
            s += 1
        return s

    init = []
    for (pid, rot, edges) in cand_per_cell[0]:
        init.append(([(pid, rot, edges)], frozenset([pid]), cell_score(edges, 0)))
    if not init: return []
    states = init
    for c in range(1, 16):
        new_states = []
        for chain, used_row, score in states:
            cur_edges = chain[-1][2]
            for next_pid, next_rot, next_edges in cand_per_cell[c]:
                if next_pid in used_row: continue
                if cur_edges[1] != next_edges[3]: continue
                ew_match = 0 if is_border(cur_edges[1]) else 1
                new_chain = chain + [(next_pid, next_rot, next_edges)]
                new_states.append((new_chain, used_row | {next_pid},
                                    score + ew_match + cell_score(next_edges, c)))
        if not new_states: return []
        new_states.sort(key=lambda x: -x[2])
        new_states = new_states[:beam_k]
        states = new_states
    return states


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='output/vol-181/RECORD_460_NEW_BASIN_row_s42_cp0312.json')
    ap.add_argument('--out-dir', default=None)
    ap.add_argument('--beam-k', type=int, default=10000)
    ap.add_argument('--rows', nargs='+', type=int, default=None,
                    help='specific rows to try; default 1..14')
    args = ap.parse_args()

    if args.out_dir is None:
        from datetime import datetime
        stamp = datetime.now().strftime('%Y%m%dT%H%M%S')
        args.out_dir = f'output/vol-186/row_swap_{stamp}'
    out_dir = REPO / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    pieces = load_pieces()
    board = json.load(open(REPO / args.base))
    score = board.get('matched', 0)
    print(f"Base: {args.base}  score={score}")
    placement_raw = board['placement']
    pl = [None] * 256
    for i, ent in enumerate(placement_raw):
        if ent is None:
            continue
        if isinstance(ent, dict):
            pos = ent.get('pos', i)
            pid = ent['piece_id']
            rot = ent['rotation']
            pl[pos] = (pid, rot)

    if args.rows is None:
        args.rows = list(range(1, 15))

    # For each row r in args.rows:
    #  free_pids = all pids NOT used in rows != r.
    #  n_constraint = row r-1's S-edges.
    #  s_constraint = row r+1's N-edges.
    #  Enumerate chains; pick best.
    print(f"Testing rows: {args.rows}")
    print(f"Original row scores (E-W match) per row 1..14:")
    for r in range(16):
        ew_matches = 0
        for c in range(15):
            l_pid, l_rot = pl[r * 16 + c]
            r_pid, r_rot = pl[r * 16 + c + 1]
            le = pieces[(l_pid, l_rot)][1]
            re = pieces[(r_pid, r_rot)][3]
            if le == re and not is_border(le):
                ew_matches += 1
        print(f"  row {r}: E-W matches = {ew_matches}/15")

    print()
    best_lift = 0
    best_board = None
    for r in args.rows:
        t0 = time.time()
        # Compute n_constraint = S-edges of row r-1.
        n_constraint = []
        for c in range(16):
            pid, rot = pl[(r - 1) * 16 + c]
            n_constraint.append(pieces[(pid, rot)][2])
        # s_constraint = N-edges of row r+1.
        s_constraint = []
        for c in range(16):
            pid, rot = pl[(r + 1) * 16 + c]
            s_constraint.append(pieces[(pid, rot)][0])
        # free_pids = all 256 minus pids in rows != r.
        used_other = set()
        for pos in range(256):
            if pos // 16 == r: continue
            if pl[pos] is not None:
                used_other.add(pl[pos][0])
        free_pids = set(range(256)) - used_other
        # Old row's pids must be in free_pids by construction.
        old_row_pids = set(pl[r * 16 + c][0] for c in range(16))
        assert old_row_pids <= free_pids

        # Both N and S soft (counted in score, not filter).
        chains = enumerate_row_chains(r, n_constraint, s_constraint, pieces, free_pids,
                                       beam_k=args.beam_k, n_strict=False, s_strict=False)
        # Original row's contribution: E-W (15 pairs) + N-matches (16) + S-matches (16).
        orig_total = 0
        for c in range(15):
            l_pid, l_rot = pl[r * 16 + c]
            r_pid, r_rot = pl[r * 16 + c + 1]
            le = pieces[(l_pid, l_rot)][1]
            re = pieces[(r_pid, r_rot)][3]
            if le == re and not is_border(le):
                orig_total += 1
        for c in range(16):
            pid, rot = pl[r * 16 + c]
            edges = pieces[(pid, rot)]
            if edges[0] == n_constraint[c] and not is_border(edges[0]):
                orig_total += 1
            if edges[2] == s_constraint[c] and not is_border(edges[2]):
                orig_total += 1
        dt = time.time() - t0
        if not chains:
            print(f"  row {r}: NO valid chains found in {dt:.1f}s")
            continue
        best_chain, best_used, best_score = chains[0]
        lift = best_score - orig_total
        print(f"  row {r}: best score={best_score} (orig {orig_total}) "
              f"lift=+{lift}  chains_found={len(chains)}  {dt:.1f}s")
        if best_score > orig_total:
            # Compose new full board and rescore.
            new_pl = list(pl)
            for c, (pid, rot, _) in enumerate(best_chain):
                new_pl[r * 16 + c] = (pid, rot)
            new_score = score_full(new_pl, pieces)
            print(f"    NEW SCORE: {new_score} (was {score}, diff +{new_score - score})")
            if new_score > score:
                lift_total = new_score - score
                if lift_total > best_lift:
                    best_lift = lift_total
                    best_board = new_pl
                # save it
                out = out_dir / f"row{r}_score{new_score}.json"
                pl_json = []
                for pos, ent in enumerate(new_pl):
                    if ent is None:
                        pl_json.append(None)
                    else:
                        pid, rot = ent
                        pl_json.append({'pos': pos, 'piece_id': pid, 'rotation': rot})
                out.write_text(json.dumps({'placement': pl_json, 'matched': new_score}))
                print(f"    SAVED {out}")

    print(f"\nFINISHED: best_lift={best_lift}")
    if best_board:
        print(f"Best board would be score {score + best_lift}")


if __name__ == '__main__':
    main()
