#!/usr/bin/env python3
"""V184 LIGHTHOUSE v3 — top-down then per-state bottom-up.

V184 v2 ran independent top and bottom beams, then MERGED with
disjointness constraint — 0/1024 valid pairs.

v3: for each top-half state, run a dedicated bottom-up search using
ONLY pieces NOT in top.used. Guaranteed disjoint.

Trade-off: 8× slower (top_k bottom-up runs) but every output is valid.
"""
from __future__ import annotations
import argparse
import json
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
from build_bidirectional2 import (
    load_pieces, BORDER, is_border, score_full,
    solve_row_topk, solve_row_topk_by_s,
)

REPO = Path(__file__).resolve().parents[2]


def main():
    ap = __import__('argparse').ArgumentParser()
    ap.add_argument('--meet-row', type=int, default=8)
    ap.add_argument('--row-k', type=int, default=8)
    ap.add_argument('--beam-k', type=int, default=300)
    ap.add_argument('--max-time', type=int, default=300)
    ap.add_argument('--out', default='output/vol-184/build_bidir_v3.json')
    args = ap.parse_args()

    t0 = time.time()
    pieces = load_pieces()
    M = args.meet_row

    # === Top-down ===
    print("=== TOP-DOWN ===")
    top_beam = [([], frozenset(), 0)]
    for r in range(M):
        if time.time() - t0 > args.max_time / 3: break
        new_beam = []
        for rows_so_far, used, _ in top_beam:
            row_above = rows_so_far[-1] if rows_so_far else None
            if row_above is None:
                n_constraint = [BORDER] * 16
            else:
                n_constraint = [edges[2] for (_, _, edges) in row_above]
            chains = solve_row_topk(r, n_constraint, pieces, used,
                                     top_k=args.row_k, beam_k=args.beam_k)
            for chain, used_row in chains:
                new_used = used | used_row
                new_rows = rows_so_far + [chain]
                pl = [None] * 256
                for ri, row in enumerate(new_rows):
                    for ci, (pid, rot, _) in enumerate(row):
                        pl[ri * 16 + ci] = (pid, rot)
                s = score_full(pl, pieces)
                new_beam.append((new_rows, new_used, s))
        if not new_beam:
            print(f"Top-down row {r}: infeasible")
            break
        new_beam.sort(key=lambda x: -x[2])
        top_beam = new_beam[:args.row_k]
        print(f"  row {r}: beam={len(top_beam)} top_score={top_beam[0][2]}")

    # === For each top-state, dedicated bottom-up ===
    print("=== PER-STATE BOTTOM-UP ===")
    best = None
    for ti, (top_rows, top_used, top_score) in enumerate(top_beam):
        if time.time() - t0 > args.max_time: break
        if len(top_rows) != M: continue
        # Interface constraint: bottom's row M N-edges must match top's row M-1 S-edges
        top_last_s = [edges[2] for (_, _, edges) in top_rows[-1]]
        # Bottom-up using ONLY pieces not in top_used.
        # We need bottom row 8 (= M) to have specific N-edges (matching top_last_s).
        # Then continue bottom-up rows 9, 10, ..., 15 each constrained by N from row above (already-placed).
        # Wait — bottom-up from row 15 to row 8 means we build rows 15, 14, ..., 8 with S-constraint each.
        # But the FIRST row we build (15) has free S = BORDER, then row 14's S = row 15's N, etc.
        # Finally row 8's S = row 9's N. But row 8's N must match top_last_s.
        # So we need to verify, AFTER bottom-up build, that row 8's N-edges == top_last_s.

        bot_beam = [([], frozenset(), 0)]
        feasible_at_8 = []  # bot_states whose row 8 N-edges match top_last_s

        for r in range(15, M - 1, -1):
            new_beam = []
            for rows_below, used_in_bot, _ in bot_beam:
                global_used = top_used | used_in_bot
                if not rows_below:
                    s_constraint = [BORDER] * 16
                else:
                    row_below = rows_below[-1]
                    s_constraint = [edges[0] for (_, _, edges) in row_below]
                # Special: at row 8 (=M), additionally constrain N to match top_last_s.
                # We do this AFTER row 8 chain candidates are generated.
                chains = solve_row_topk_by_s(r, s_constraint, pieces, global_used,
                                              top_k=args.row_k, beam_k=args.beam_k)
                if r == M:
                    # filter chains where row's N-edges match top_last_s
                    filt = []
                    for chain, used_row in chains:
                        n_edges = [edges[0] for (_, _, edges) in chain]
                        if n_edges == top_last_s:
                            filt.append((chain, used_row))
                    chains = filt
                for chain, used_row in chains:
                    new_used_in_bot = used_in_bot | used_row
                    new_rows = rows_below + [chain]
                    pl = [None] * 256
                    for ri, row in enumerate(top_rows):
                        for ci, (pid, rot, _) in enumerate(row):
                            pl[ri * 16 + ci] = (pid, rot)
                    for i, row in enumerate(new_rows):
                        real_row = 15 - i
                        for ci, (pid, rot, _) in enumerate(row):
                            pl[real_row * 16 + ci] = (pid, rot)
                    s = score_full(pl, pieces)
                    new_beam.append((new_rows, new_used_in_bot, s))
            if not new_beam:
                break
            new_beam.sort(key=lambda x: -x[2])
            bot_beam = new_beam[:args.row_k]

        # After bottom-up: bot_beam has rows 15..M with M=row 8 at the end.
        for rows_below, used_in_bot, s in bot_beam:
            if len(rows_below) != 16 - M: continue
            # Top last_s already matched in r == M filter.
            # Compose full placement
            pl = [None] * 256
            for ri, row in enumerate(top_rows):
                for ci, (pid, rot, _) in enumerate(row):
                    pl[ri * 16 + ci] = (pid, rot)
            for i, row in enumerate(rows_below):
                real_row = 15 - i
                for ci, (pid, rot, _) in enumerate(row):
                    pl[real_row * 16 + ci] = (pid, rot)
            full_s = score_full(pl, pieces)
            if best is None or full_s > best[0]:
                best = (full_s, pl)
        print(f"  top state {ti}/{len(top_beam)}: bot_beam={len(bot_beam)}, best so far={best[0] if best else 'none'}")

    if best is None:
        print("No valid bidirectional board.")
        return
    score, placement = best
    n_placed = sum(1 for p in placement if p is not None)
    print(f"\nBEST: score={score}/480, placed={n_placed}/256")
    out_path = Path(REPO / args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pl_json = []
    for pos, ent in enumerate(placement):
        if ent is None:
            pl_json.append(None)
        else:
            pid, rot = ent
            pl_json.append({'pos': pos, 'piece_id': pid, 'rotation': rot})
    out_path.write_text(json.dumps({'placement': pl_json, 'matched': score}))
    print(f"saved {out_path}")


if __name__ == '__main__':
    main()
