#!/usr/bin/env python3
"""V186-T3 pool-biased LIGHTHOUSE.

Same bidirectional row-build as build_bidir_soft.py, but the top-down
beam now penalises picking pieces with high β (bottom-row corpus affinity).
This reserves bottom-critical pieces for the bottom-up half.

Penalty: R'(b) = R(b) - γ · Σ_{p in used(b)} β(p).
"""
from __future__ import annotations
import argparse
import json
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v184_lighthouse"))
from build_bidirectional2 import (
    load_pieces, BORDER, is_border, score_full, candidates_for_cell,
)

REPO = Path(__file__).resolve().parents[2]


def solve_row_topk_biased(row_idx, n_constraint, pieces, used_pids,
                           beta, gamma, by_s=False, s_constraint=None,
                           top_k=8, beam_k=300, size=16):
    """Chain-DP with pool-bias score = matched - gamma·β(piece).

    by_s: if True, the row is constrained by S (bottom-up); else by N.
    """
    cand_per_cell = []
    for c in range(size):
        pos = row_idx * size + c
        cs = candidates_for_cell(pos, pieces, used_pids)
        if by_s:
            match = [(pid, rot, edges) for (pid, rot, edges) in cs if edges[2] == s_constraint[c]]
        else:
            match = [(pid, rot, edges) for (pid, rot, edges) in cs if edges[0] == n_constraint[c]]
        cand_per_cell.append(match)
        if not match:
            return []

    def piece_pen(pid):
        return gamma * beta[pid]

    init = []
    for (pid, rot, edges) in cand_per_cell[0]:
        init.append(([(pid, rot, edges)], frozenset([pid]), -piece_pen(pid)))
    if not init: return []
    states = [init]
    for c in range(1, size):
        new_states = []
        for chain, used_row, score in states[-1]:
            cur_edges = chain[-1][2]
            for next_pid, next_rot, next_edges in cand_per_cell[c]:
                if next_pid in used_row: continue
                if cur_edges[1] != next_edges[3]: continue
                ew_match = 0 if is_border(cur_edges[1]) else 1
                new_chain = chain + [(next_pid, next_rot, next_edges)]
                new_states.append((new_chain, used_row | {next_pid},
                                    score + ew_match - piece_pen(next_pid)))
        if not new_states: return []
        new_states.sort(key=lambda x: -x[2])
        new_states = new_states[:beam_k]
        states.append(new_states)
    states[-1].sort(key=lambda x: -x[2])
    return [(chain, used_row) for chain, used_row, _ in states[-1][:top_k]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--meet-row', type=int, default=8)
    ap.add_argument('--row-k', type=int, default=8)
    ap.add_argument('--beam-k', type=int, default=300)
    ap.add_argument('--max-mismatch', type=int, default=4)
    ap.add_argument('--max-time', type=int, default=300)
    ap.add_argument('--score-thresh', type=int, default=100)
    ap.add_argument('--gamma-top', type=float, default=0.5,
                    help='penalty γ on β (top-down avoids bottom-rich pieces)')
    ap.add_argument('--gamma-bot', type=float, default=0.5,
                    help='penalty γ on τ (bottom-up avoids top-rich pieces; usually 0)')
    ap.add_argument('--affinity-file',
                    default='scripts/v186_lighthouse_soft/bottom_affinity.json')
    ap.add_argument('--out-dir', default=None)
    args = ap.parse_args()

    if args.out_dir is None:
        from datetime import datetime
        stamp = datetime.now().strftime('%Y%m%dT%H%M%S')
        args.out_dir = (f'output/vol-186/pool_m{args.meet_row}_mm{args.max_mismatch}'
                        f'_g{args.gamma_top}_{stamp}')
    out_dir = REPO / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    aff = json.load(open(args.affinity_file))
    beta = aff['beta_bottom']
    tau = aff['tau_top']
    print(f"out_dir={out_dir}")
    print(f"meet_row={args.meet_row} row_k={args.row_k} beam_k={args.beam_k} "
          f"max_mismatch={args.max_mismatch} γ_top={args.gamma_top} γ_bot={args.gamma_bot}")

    t0 = time.time()
    pieces = load_pieces()
    M = args.meet_row

    print("=== TOP-DOWN (pool-biased, γ_top={}) ===".format(args.gamma_top))
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
            chains = solve_row_topk_biased(r, n_constraint, pieces, used,
                                            beta, args.gamma_top,
                                            by_s=False,
                                            top_k=args.row_k, beam_k=args.beam_k)
            for chain, used_row in chains:
                new_used = used | used_row
                new_rows = rows_so_far + [chain]
                pl = [None] * 256
                for ri, row in enumerate(new_rows):
                    for ci, (pid, rot, _) in enumerate(row):
                        pl[ri * 16 + ci] = (pid, rot)
                s = score_full(pl, pieces)
                # rerank by RAW score (we used penalty for chain expansion only).
                new_beam.append((new_rows, new_used, s))
        if not new_beam:
            print(f"Top-down row {r}: infeasible")
            break
        new_beam.sort(key=lambda x: -x[2])
        top_beam = new_beam[:args.row_k]
        print(f"  row {r}: beam={len(top_beam)} top_score={top_beam[0][2]} "
              f"used_β_top10={sum(1 for p in list(top_beam[0][1]) if beta[p] > 0.5)}/31")

    print(f"=== PER-STATE BOTTOM-UP (soft mm={args.max_mismatch}, γ_bot={args.gamma_bot}) ===")
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
                chains = solve_row_topk_biased(r, None, pieces, global_used,
                                                tau, args.gamma_bot,
                                                by_s=True, s_constraint=s_constraint,
                                                top_k=args.row_k, beam_k=args.beam_k)
                if r == M:
                    filt = []
                    for chain, used_row in chains:
                        n_edges = [edges[0] for (_, _, edges) in chain]
                        mismatches = sum(1 for a, b in zip(n_edges, top_last_s) if a != b)
                        if mismatches <= args.max_mismatch:
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
                print(f"    row {r}: INFEASIBLE")
                break
            new_beam.sort(key=lambda x: -x[2])
            bot_beam = new_beam[:args.row_k]
            print(f"    row {r}: bot_beam={len(bot_beam)} top_score={bot_beam[0][2]}")
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
                fname = out_dir / f"pool_ti{ti}_score{full_s}_n{saved}.json"
                fname.write_text(json.dumps({'placement': pl_json, 'matched': full_s}))
                saved += 1
            if full_s > best_score:
                best_score = full_s
                best_pl = pl
        print(f"  top state {ti}/{len(top_beam)}: best so far={best_score}, saved={saved}")

    print(f"\nFINISHED: best={best_score}/480, saved={saved} boards >= {args.score_thresh}")
    print(f"out_dir={out_dir}")


if __name__ == '__main__':
    main()
