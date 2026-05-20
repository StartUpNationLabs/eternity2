#!/usr/bin/env python3
"""V186 LIGHTHOUSE-SOFT — relaxed interface bidirectional row-build.

Three-basin-iso-plateau (vol-181) showed local ALNS exhausted on 458-460
bases. V184 LIGHTHOUSE refuted as record-mover because the row-M
interface constraint (16-edge exact match) yielded 0 valid pairs.

V186 SOFT: allow up to `max_mismatch` N-edge mismatches at row M.
Compose any (top, bot) pair that meets the disjointness + soft-interface
constraints, then write the joint board to disk for ALNS-repair.

The hypothesis: a board with ~5 forced row-M mismatches still scores
~455 and is structurally different from the locked 458-460 basins.
ALNS-repair from a structurally-novel 455 base might reach 460+ on a
NEW basin family.

Approach:
- Top-down beam to row M-1 (M = meet-row).
- For each top-state, per-state bottom-up beam using pieces NOT in top.used.
- At row M, accept chains whose N-edges match top's row M-1 S-edges in
  >= (16 - max_mismatch) positions.
- Write all merged boards above a score threshold to disk.
"""
from __future__ import annotations
import argparse
import json
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v184_lighthouse"))
from build_bidirectional2 import (
    load_pieces, BORDER, is_border, score_full,
    solve_row_topk, solve_row_topk_by_s,
)

REPO = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--meet-row', type=int, default=8)
    ap.add_argument('--row-k', type=int, default=8)
    ap.add_argument('--beam-k', type=int, default=300)
    ap.add_argument('--max-mismatch', type=int, default=4,
                    help='allowed N-edge mismatches at row M (interface softness)')
    ap.add_argument('--max-time', type=int, default=600)
    ap.add_argument('--score-thresh', type=int, default=400,
                    help='only save boards scoring >= this')
    ap.add_argument('--out-dir', default=None)
    args = ap.parse_args()

    if args.out_dir is None:
        from datetime import datetime
        stamp = datetime.now().strftime('%Y%m%dT%H%M%S')
        args.out_dir = f'output/vol-186/soft_m{args.meet_row}_mm{args.max_mismatch}_{stamp}'

    out_dir = REPO / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"out_dir={out_dir}")
    print(f"meet_row={args.meet_row} row_k={args.row_k} beam_k={args.beam_k} "
          f"max_mismatch={args.max_mismatch} score_thresh={args.score_thresh}")

    t0 = time.time()
    pieces = load_pieces()
    M = args.meet_row

    # === TOP-DOWN ===
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

    # === PER-STATE BOTTOM-UP WITH SOFT INTERFACE ===
    print(f"=== PER-STATE BOTTOM-UP (soft, max_mismatch={args.max_mismatch}) ===")
    saved = 0
    best_score = 0
    best_pl = None
    for ti, (top_rows, top_used, top_score) in enumerate(top_beam):
        if time.time() - t0 > args.max_time: break
        if len(top_rows) != M: continue
        top_last_s = [edges[2] for (_, _, edges) in top_rows[-1]]

        bot_beam = [([], frozenset(), 0)]
        for r in range(15, M - 1, -1):
            new_beam = []
            for rows_below, used_in_bot, _ in bot_beam:
                global_used = top_used | used_in_bot
                if not rows_below:
                    s_constraint = [BORDER] * 16
                else:
                    row_below = rows_below[-1]
                    s_constraint = [edges[0] for (_, _, edges) in row_below]
                chains = solve_row_topk_by_s(r, s_constraint, pieces, global_used,
                                              top_k=args.row_k, beam_k=args.beam_k)
                if r == M:
                    # SOFT FILTER: keep chains with N-edge mismatches <= max_mismatch.
                    filt = []
                    for chain, used_row in chains:
                        n_edges = [edges[0] for (_, _, edges) in chain]
                        mismatches = sum(1 for a, b in zip(n_edges, top_last_s) if a != b)
                        if mismatches <= args.max_mismatch:
                            filt.append((chain, used_row, mismatches))
                    # extend new_beam with mismatch info as a side-channel
                    for chain, used_row, mm in filt:
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
                else:
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
                print(f"    row {r}: bot_beam INFEASIBLE")
                break
            new_beam.sort(key=lambda x: -x[2])
            bot_beam = new_beam[:args.row_k]
            print(f"    row {r}: bot_beam={len(bot_beam)} top_score={bot_beam[0][2]}")

        # Save all full boards above thresh.
        for rows_below, used_in_bot, s in bot_beam:
            if len(rows_below) != 16 - M: continue
            pl = [None] * 256
            for ri, row in enumerate(top_rows):
                for ci, (pid, rot, _) in enumerate(row):
                    pl[ri * 16 + ci] = (pid, rot)
            for i, row in enumerate(rows_below):
                real_row = 15 - i
                for ci, (pid, rot, _) in enumerate(row):
                    pl[real_row * 16 + ci] = (pid, rot)
            full_s = score_full(pl, pieces)
            if full_s >= args.score_thresh:
                pl_json = []
                for pos, ent in enumerate(pl):
                    if ent is None:
                        pl_json.append(None)
                    else:
                        pid, rot = ent
                        pl_json.append({'pos': pos, 'piece_id': pid, 'rotation': rot})
                fname = out_dir / f"soft_ti{ti}_score{full_s}_n{saved}.json"
                fname.write_text(json.dumps({'placement': pl_json, 'matched': full_s}))
                saved += 1
            if full_s > best_score:
                best_score = full_s
                best_pl = pl
        print(f"  top state {ti}/{len(top_beam)}: bot_beam={len(bot_beam)}, "
              f"best so far={best_score}, saved={saved}")

    print(f"\nFINISHED: best={best_score}/480, saved={saved} boards >= {args.score_thresh}")
    print(f"out_dir={out_dir}")
    if best_pl is not None:
        best_path = out_dir / 'BEST.json'
        pl_json = []
        for pos, ent in enumerate(best_pl):
            if ent is None:
                pl_json.append(None)
            else:
                pid, rot = ent
                pl_json.append({'pos': pos, 'piece_id': pid, 'rotation': rot})
        best_path.write_text(json.dumps({'placement': pl_json, 'matched': best_score}))
        print(f"BEST saved to {best_path}")


if __name__ == '__main__':
    main()
