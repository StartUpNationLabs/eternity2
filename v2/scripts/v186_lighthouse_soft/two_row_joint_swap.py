#!/usr/bin/env python3
"""V186-T7 two-row joint swap.

Given a board b and target rows (r_a, r_b) with r_b = r_a + 1, enumerate
joint chains for rows r_a and r_b together. Pieces in rows {r_a, r_b}
are all freed (32 pieces back in pool, plus pieces from OTHER rows
remain placed). The chain DP processes both rows simultaneously,
column by column:

State at column c: (left_a_edges, left_b_edges, used_pieces_in_rows).

Transitions: pick (piece_a, rot_a) for row r_a at column c (with valid N
from r_a-1, valid W matching left_a_edges) AND pick (piece_b, rot_b)
for row r_b at column c (with valid N from r_a (= ow piece_a's S),
valid W matching left_b_edges, valid S from r_b+1).

Score: increment for each matching edge (E-W in row a, E-W in row b,
N-match a, S-match a (= N-match b), S-match b).

Sound: explores the full 16-column chain for both rows; the only
approximation is the beam-K cutoff.
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


def solve_two_row_joint(r_a, n_constraint_a, s_constraint_b,
                         pieces, free_pids, beam_k=20000):
    """Beam-K joint DP over two adjacent rows.

    n_constraint_a: 16-tuple of edge colors row r_a's N must match (from row r_a-1's S).
    s_constraint_b: 16-tuple of edge colors row r_b=r_a+1's S must match (from row r_b+1's N).

    Returns top chains (chain_a, chain_b, used_set, score) sorted desc.
    """
    # Build per-column candidate lists for row a and row b.
    # Row a: cell (r_a, c); row b: cell (r_a+1, c).
    cand_a = [[] for _ in range(16)]
    cand_b = [[] for _ in range(16)]
    for c in range(16):
        for pid in free_pids:
            for rot in range(4):
                edges = pieces[(pid, rot)]
                # Row a candidates: N must match n_constraint_a[c] (soft scoring: skip filter for relaxed match).
                # Border: col 0 W=BORDER, col 15 E=BORDER.
                if c == 0 and edges[3] != BORDER: continue
                if c == 15 and edges[1] != BORDER: continue
                # No interior piece in row a or b should have any BORDER edge except corners,
                # and these rows are interior (r_a in [1..13]); col 0 and 15 are the edge column constraint.
                # For row a: piece must be such that its N could match n_constraint_a[c] OR be a relaxation.
                # We'll use soft scoring; keep the candidate.
                cand_a[c].append((pid, rot, edges))
                cand_b[c].append((pid, rot, edges))

    # Initial: column 0.
    # State: ((pid_a, rot_a), (pid_b, rot_b), used_in_rows, score)
    # used_in_rows starts as frozenset of those two pids (must be distinct).
    init = []
    for (pid_a, rot_a, ea) in cand_a[0]:
        for (pid_b, rot_b, eb) in cand_b[0]:
            if pid_a == pid_b: continue
            # Score: N-match a, S-match a (= N-match b: ea.S == eb.N), S-match b, W-match=0 (border).
            s = 0
            if ea[0] == n_constraint_a[0] and not is_border(ea[0]):
                s += 1
            # Internal seam: a.S vs b.N
            if ea[2] == eb[0] and not is_border(ea[2]):
                s += 1
            # b.S vs s_constraint_b
            if eb[2] == s_constraint_b[0] and not is_border(eb[2]):
                s += 1
            init.append(((pid_a, rot_a, ea), (pid_b, rot_b, eb),
                          frozenset([pid_a, pid_b]), s))

    if not init: return []
    init.sort(key=lambda x: -x[3])
    states = init[:beam_k]

    chain_a = [[] for _ in range(16)]
    chain_b = [[] for _ in range(16)]
    # We'll track the full path via backpointers in next iteration; for simplicity, store chains in state.
    # Re-encode states to include path.
    states = [
        ([(s[0][0], s[0][1])], [(s[1][0], s[1][1])], s[2], s[3])
        for s in states
    ]
    # Each state: (chain_a_so_far, chain_b_so_far, used, score)

    for c in range(1, 16):
        new_states = []
        for ca, cb, used, score in states:
            last_a_pid, last_a_rot = ca[-1]
            last_b_pid, last_b_rot = cb[-1]
            last_a_edges = pieces[(last_a_pid, last_a_rot)]
            last_b_edges = pieces[(last_b_pid, last_b_rot)]
            # For each (cand_a_c, cand_b_c) pair:
            for (pid_a, rot_a, ea) in cand_a[c]:
                if pid_a in used: continue
                if last_a_edges[1] != ea[3]: continue  # E-W in row a
                ewa = 0 if is_border(last_a_edges[1]) else 1
                for (pid_b, rot_b, eb) in cand_b[c]:
                    if pid_b in used: continue
                    if pid_b == pid_a: continue
                    if last_b_edges[1] != eb[3]: continue  # E-W in row b
                    ewb = 0 if is_border(last_b_edges[1]) else 1
                    # N-match a (only at c == 0 actually, but track soft for all interior cells)
                    s_add = ewa + ewb
                    if ea[0] == n_constraint_a[c] and not is_border(ea[0]):
                        s_add += 1
                    if ea[2] == eb[0] and not is_border(ea[2]):
                        s_add += 1
                    if eb[2] == s_constraint_b[c] and not is_border(eb[2]):
                        s_add += 1
                    new_used = used | {pid_a, pid_b}
                    new_ca = ca + [(pid_a, rot_a)]
                    new_cb = cb + [(pid_b, rot_b)]
                    new_states.append((new_ca, new_cb, new_used, score + s_add))
        if not new_states:
            return []
        new_states.sort(key=lambda x: -x[3])
        states = new_states[:beam_k]
    # Return top: (chain_a, chain_b, used, score)
    return states


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='output/vol-181/RECORD_460_NEW_BASIN_row_s42_cp0312.json')
    ap.add_argument('--rows', nargs=2, type=int, default=[12, 13])
    ap.add_argument('--beam-k', type=int, default=20000)
    ap.add_argument('--out-dir', default=None)
    args = ap.parse_args()

    if args.out_dir is None:
        from datetime import datetime
        stamp = datetime.now().strftime('%Y%m%dT%H%M%S')
        args.out_dir = f'output/vol-186/two_row_swap_{args.rows[0]}_{args.rows[1]}_{stamp}'
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

    r_a, r_b = args.rows
    assert r_b == r_a + 1
    n_constraint_a = [pieces[(pl[(r_a - 1) * 16 + c][0], pl[(r_a - 1) * 16 + c][1])][2] for c in range(16)]
    s_constraint_b = [pieces[(pl[(r_b + 1) * 16 + c][0], pl[(r_b + 1) * 16 + c][1])][0] for c in range(16)]
    used_other = set()
    for pos in range(256):
        r = pos // 16
        if r == r_a or r == r_b: continue
        if pl[pos] is not None:
            used_other.add(pl[pos][0])
    free_pids = set(range(256)) - used_other
    print(f"free_pids: {len(free_pids)} (expecting 32)")

    # Original total score for these two rows.
    orig_total = 0
    # E-W in row a, row b
    for c in range(15):
        pa_l, ra_l = pl[r_a * 16 + c]
        pa_r, ra_r = pl[r_a * 16 + c + 1]
        if pieces[(pa_l, ra_l)][1] == pieces[(pa_r, ra_r)][3] and not is_border(pieces[(pa_l, ra_l)][1]):
            orig_total += 1
        pb_l, rb_l = pl[r_b * 16 + c]
        pb_r, rb_r = pl[r_b * 16 + c + 1]
        if pieces[(pb_l, rb_l)][1] == pieces[(pb_r, rb_r)][3] and not is_border(pieces[(pb_l, rb_l)][1]):
            orig_total += 1
    # N-match a (with r_a - 1), seam a-b, S-match b (with r_b + 1)
    for c in range(16):
        pa, ra = pl[r_a * 16 + c]
        pb, rb = pl[r_b * 16 + c]
        ea = pieces[(pa, ra)]; eb = pieces[(pb, rb)]
        if ea[0] == n_constraint_a[c] and not is_border(ea[0]):
            orig_total += 1
        if ea[2] == eb[0] and not is_border(ea[2]):
            orig_total += 1
        if eb[2] == s_constraint_b[c] and not is_border(eb[2]):
            orig_total += 1

    print(f"Original two-row contribution score: {orig_total}")

    t0 = time.time()
    print(f"Solving two-row joint DP (beam_k={args.beam_k})...")
    chains = solve_two_row_joint(r_a, n_constraint_a, s_constraint_b,
                                  pieces, free_pids, beam_k=args.beam_k)
    dt = time.time() - t0
    if not chains:
        print(f"No valid joint chains found in {dt:.1f}s")
        return
    print(f"Found {len(chains)} chains in {dt:.1f}s")
    best_ca, best_cb, best_used, best_score = chains[0]
    lift = best_score - orig_total
    print(f"Best joint score: {best_score} (orig {orig_total}) lift={lift:+}")

    if best_score > orig_total:
        new_pl = list(pl)
        for c in range(16):
            new_pl[r_a * 16 + c] = best_ca[c]
            new_pl[r_b * 16 + c] = best_cb[c]
        new_full_score = score_full(new_pl, pieces)
        print(f"NEW FULL SCORE: {new_full_score} (was {score}, diff +{new_full_score - score})")
        if new_full_score > score:
            out = out_dir / f"row_{r_a}_{r_b}_swap_score{new_full_score}.json"
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
