#!/usr/bin/env python3
"""V186-T8 three-row joint swap.

Joint DP over rows (r, r+1, r+2). 48 free pieces (16x3).
State per column: ((piece_a, rot_a), (piece_b, rot_b), (piece_c, rot_c), used, score).

This is 30^3 candidates per column step in the worst case — needs careful
beam-K and possibly pruning.
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


def solve_three_row_joint(r_a, n_constraint_a, s_constraint_c,
                           pieces, free_pids, beam_k=5000):
    """Beam-K joint DP over three adjacent rows (r_a, r_a+1, r_a+2)."""
    cand = [[] for _ in range(16)]
    for c in range(16):
        for pid in free_pids:
            for rot in range(4):
                edges = pieces[(pid, rot)]
                if c == 0 and edges[3] != BORDER: continue
                if c == 15 and edges[1] != BORDER: continue
                cand[c].append((pid, rot, edges))

    # Initial column 0: try (a, b, c) with all distinct pids.
    init = []
    for (pa, ra, ea) in cand[0]:
        for (pb, rb, eb) in cand[0]:
            if pa == pb: continue
            for (pc, rc, ec) in cand[0]:
                if pc == pa or pc == pb: continue
                # Score: N a, seam a-b, seam b-c, S c.
                s = 0
                if ea[0] == n_constraint_a[0] and not is_border(ea[0]):
                    s += 1
                if ea[2] == eb[0] and not is_border(ea[2]):
                    s += 1
                if eb[2] == ec[0] and not is_border(eb[2]):
                    s += 1
                if ec[2] == s_constraint_c[0] and not is_border(ec[2]):
                    s += 1
                init.append((
                    [(pa, ra)], [(pb, rb)], [(pc, rc)],
                    frozenset([pa, pb, pc]), s
                ))

    if not init: return []
    init.sort(key=lambda x: -x[4])
    states = init[:beam_k]

    for col in range(1, 16):
        new_states = []
        for ca, cb, cc, used, score in states:
            la_pid, la_rot = ca[-1]; ea_prev = pieces[(la_pid, la_rot)]
            lb_pid, lb_rot = cb[-1]; eb_prev = pieces[(lb_pid, lb_rot)]
            lc_pid, lc_rot = cc[-1]; ec_prev = pieces[(lc_pid, lc_rot)]
            for (pa, ra, ea) in cand[col]:
                if pa in used: continue
                if ea_prev[1] != ea[3]: continue
                ewa = 0 if is_border(ea_prev[1]) else 1
                for (pb, rb, eb) in cand[col]:
                    if pb in used or pb == pa: continue
                    if eb_prev[1] != eb[3]: continue
                    ewb = 0 if is_border(eb_prev[1]) else 1
                    for (pc, rc, ec) in cand[col]:
                        if pc in used or pc == pa or pc == pb: continue
                        if ec_prev[1] != ec[3]: continue
                        ewc = 0 if is_border(ec_prev[1]) else 1
                        s_add = ewa + ewb + ewc
                        if ea[0] == n_constraint_a[col] and not is_border(ea[0]):
                            s_add += 1
                        if ea[2] == eb[0] and not is_border(ea[2]):
                            s_add += 1
                        if eb[2] == ec[0] and not is_border(eb[2]):
                            s_add += 1
                        if ec[2] == s_constraint_c[col] and not is_border(ec[2]):
                            s_add += 1
                        new_used = used | {pa, pb, pc}
                        new_states.append((
                            ca + [(pa, ra)], cb + [(pb, rb)], cc + [(pc, rc)],
                            new_used, score + s_add
                        ))
        if not new_states: return []
        new_states.sort(key=lambda x: -x[4])
        states = new_states[:beam_k]
    return states


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='output/vol-181/RECORD_460_NEW_BASIN_row_s42_cp0312.json')
    ap.add_argument('--rows', nargs=3, type=int, default=[11, 12, 13])
    ap.add_argument('--beam-k', type=int, default=3000)
    ap.add_argument('--out-dir', default=None)
    args = ap.parse_args()

    if args.out_dir is None:
        from datetime import datetime
        stamp = datetime.now().strftime('%Y%m%dT%H%M%S')
        args.out_dir = f'output/vol-186/three_row_swap_{args.rows[0]}_{stamp}'
    out_dir = REPO / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    pieces = load_pieces()
    board = json.load(open(REPO / args.base))
    score = board.get('matched', 0)
    print(f"Base: {args.base}  score={score}")
    pl = [None] * 256
    for ent in board['placement']:
        if ent is not None:
            pl[ent['pos']] = (ent['piece_id'], ent['rotation'])

    r_a, r_b, r_c = args.rows
    assert r_b == r_a + 1 and r_c == r_b + 1
    n_constraint_a = [pieces[(pl[(r_a - 1) * 16 + c][0], pl[(r_a - 1) * 16 + c][1])][2] for c in range(16)]
    s_constraint_c = [pieces[(pl[(r_c + 1) * 16 + c][0], pl[(r_c + 1) * 16 + c][1])][0] for c in range(16)]
    used_other = set()
    for pos in range(256):
        r = pos // 16
        if r in (r_a, r_b, r_c): continue
        if pl[pos] is not None:
            used_other.add(pl[pos][0])
    free_pids = set(range(256)) - used_other
    print(f"free_pids: {len(free_pids)} (expecting 48)")

    # Original contribution score over these 3 rows.
    orig_total = 0
    # E-W in each row
    for r in (r_a, r_b, r_c):
        for c in range(15):
            l_pid, l_rot = pl[r * 16 + c]
            r_pid, r_rot = pl[r * 16 + c + 1]
            if pieces[(l_pid, l_rot)][1] == pieces[(r_pid, r_rot)][3] and not is_border(pieces[(l_pid, l_rot)][1]):
                orig_total += 1
    # N a + seam a-b + seam b-c + S c (4 edges per column)
    for c in range(16):
        pa, ra = pl[r_a * 16 + c]; ea = pieces[(pa, ra)]
        pb, rb = pl[r_b * 16 + c]; eb = pieces[(pb, rb)]
        pc, rc = pl[r_c * 16 + c]; ec = pieces[(pc, rc)]
        if ea[0] == n_constraint_a[c] and not is_border(ea[0]):
            orig_total += 1
        if ea[2] == eb[0] and not is_border(ea[2]):
            orig_total += 1
        if eb[2] == ec[0] and not is_border(eb[2]):
            orig_total += 1
        if ec[2] == s_constraint_c[c] and not is_border(ec[2]):
            orig_total += 1

    print(f"Original three-row contribution score: {orig_total}")

    t0 = time.time()
    print(f"Solving three-row joint DP (beam_k={args.beam_k})...")
    chains = solve_three_row_joint(r_a, n_constraint_a, s_constraint_c,
                                    pieces, free_pids, beam_k=args.beam_k)
    dt = time.time() - t0
    if not chains:
        print(f"No valid joint chains found in {dt:.1f}s")
        return
    print(f"Found {len(chains)} chains in {dt:.1f}s")
    best_ca, best_cb, best_cc, best_used, best_score = chains[0]
    lift = best_score - orig_total
    print(f"Best joint score: {best_score} (orig {orig_total}) lift={lift:+}")

    if best_score > orig_total:
        new_pl = list(pl)
        for c in range(16):
            new_pl[r_a * 16 + c] = best_ca[c]
            new_pl[r_b * 16 + c] = best_cb[c]
            new_pl[r_c * 16 + c] = best_cc[c]
        new_full_score = score_full(new_pl, pieces)
        print(f"NEW FULL SCORE: {new_full_score} (was {score}, diff +{new_full_score - score})")
        if new_full_score > score:
            out = out_dir / f"row_{r_a}_{r_b}_{r_c}_score{new_full_score}.json"
            pl_json = []
            for pos, ent in enumerate(new_pl):
                if ent is None:
                    pl_json.append(None)
                else:
                    pid, rot = ent
                    pl_json.append({'pos': pos, 'piece_id': pid, 'rotation': rot})
            out.write_text(json.dumps({'placement': pl_json, 'matched': new_full_score}))
            print(f"SAVED {out}")


if __name__ == '__main__':
    main()
