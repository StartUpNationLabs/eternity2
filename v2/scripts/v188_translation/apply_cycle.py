#!/usr/bin/env python3
"""V188-T2 — apply a piece-permutation cycle to a board.

Given board A and a cycle of pieces [p_0, p_1, ..., p_{k-1}], swap them:
the piece currently at the position of p_i becomes p_{i+1}.

After swap, rescore and report.

If the cycle is a CYCLE in π (where π maps A → B), applying the cycle
to A moves A *toward* B at those positions. If the cycle is bottom-
confined AND B's bottom is higher-scoring, score should increase.

Note: this naive substitution does NOT change rotations. The rotation
in board B at piece p_i's position may differ from board A's rotation at
that position. We have to compute B's rotation for each piece and use
that. The "transport" replaces (piece_A[pos], rot_A[pos]) with
(π(piece_A[pos]), rot_at_pos_in_B_for_π(piece_A[pos])).

Actually simpler: at position p, A has piece a_p. We want to substitute
the piece at p with the piece that B has at p (with B's rotation).
This IS the cycle application restricted to position p.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v184_lighthouse"))
from build_bidirectional2 import load_pieces, BORDER, is_border, score_full

REPO = Path(__file__).resolve().parents[2]


def load_placement(path):
    board = json.load(open(path))
    pl = [None] * 256
    for ent in board['placement']:
        if ent is not None:
            pl[ent['pos']] = (ent['piece_id'], ent['rotation'])
    return pl, board.get('matched', 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--board-a', default='output/vol-181/RECORD_460_NEW_BASIN_row_s42_cp0312.json')
    ap.add_argument('--board-b', default='database-400-480/469_mcgavin_469_6c9a2448.json')
    ap.add_argument('--cycle-pieces', nargs='+', type=int, required=True,
                    help='Piece IDs forming the cycle to apply')
    ap.add_argument('--out-dir', default=None)
    args = ap.parse_args()

    if args.out_dir is None:
        from datetime import datetime
        stamp = datetime.now().strftime('%Y%m%dT%H%M%S')
        args.out_dir = f'output/vol-188/apply_cycle_{stamp}'
    out_dir = REPO / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    pieces = load_pieces()
    pl_a, score_a = load_placement(REPO / args.board_a)
    pl_b, score_b = load_placement(REPO / args.board_b)

    # Build position-of-piece for each board.
    pos_a = {}
    pos_b = {}
    for p in range(256):
        if pl_a[p] is not None: pos_a[pl_a[p][0]] = p
        if pl_b[p] is not None: pos_b[pl_b[p][0]] = p

    cycle = args.cycle_pieces
    print(f"Original A score: {score_a}")
    print(f"Original B score: {score_b}")
    print(f"Cycle pieces: {cycle}")

    # Validate cycle: π(p_i) = ? in B at position pos_a[p_i].
    print("\nCycle position info:")
    for pid in cycle:
        pa = pos_a.get(pid)
        pb_pid_at_pa = pl_b[pa][0] if pa is not None else None
        pa_rot = pl_a[pa][1] if pa is not None else None
        pb_rot_at_pa = pl_b[pa][1] if pa is not None else None
        print(f"  piece {pid}: at A pos {pa} (row {pa//16}, col {pa%16}, rot_A={pa_rot}), "
              f"B has piece {pb_pid_at_pa} (rot_B={pb_rot_at_pa}) at same pos")

    # Apply: at each position pos_a[p] for p in cycle, replace A's (p, rot_A) with
    # (pi(p), rot_B[pos_a[p]]).
    new_pl = list(pl_a)
    for pid in cycle:
        pa = pos_a[pid]
        pb_pid = pl_b[pa][0]
        pb_rot = pl_b[pa][1]
        new_pl[pa] = (pb_pid, pb_rot)
    new_score = score_full(new_pl, pieces)
    print(f"\nAfter cycle application: NEW SCORE = {new_score}/480 (was {score_a})")
    delta = new_score - score_a
    print(f"  Δ = {delta:+}")

    if new_score > score_a:
        print(f"*** RECORD LIFT *** saving...")
        pl_json = []
        for pos, ent in enumerate(new_pl):
            if ent is None:
                pl_json.append(None)
            else:
                pid, rot = ent
                pl_json.append({'pos': pos, 'piece_id': pid, 'rotation': rot})
        out = out_dir / f"LIFT_{new_score}_cycle{'_'.join(map(str,cycle))}.json"
        out.write_text(json.dumps({'placement': pl_json, 'matched': new_score}))
        print(f"SAVED {out}")


if __name__ == '__main__':
    main()
