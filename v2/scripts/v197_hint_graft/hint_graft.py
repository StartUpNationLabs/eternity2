#!/usr/bin/env python3
"""V197 HINT-GRAFT: take a 0/5-hint 460 board, force the 5 canonical
hints by piece-swap, output a 5/5-hint board (with degraded score) for
ALNS to re-lift.

Mechanic:
1. For each hint h = (pos_h, piece_h, rot_h):
   - Find where piece_h currently is on the board (some pos_x).
   - Find what's at pos_h (piece_y at some rot_y).
   - Swap: put piece_h at pos_h with rot_h, put piece_y at pos_x with rot_y.
2. Result has 5/5 hints. Score may have dropped 5-30 points from the swaps.
3. Save for ALNS lift.
"""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v184_lighthouse"))
from build_bidirectional2 import load_pieces, BORDER, is_border

REPO = Path(__file__).resolve().parents[2]

# Canonical hints: pos -> (piece_id, rotation)
HINTS = {
    34:  (207, 1),
    45:  (254, 1),
    135: (138, 0),
    210: (180, 1),
    221: (248, 2),
}


def board_to_pl(board):
    pl_raw = board['placement']
    pl = [None] * 256
    for ent in pl_raw:
        pos = ent.get('pos')
        if pos is None: continue
        pl[pos] = (ent['piece_id'], ent.get('rotation', 0))
    return pl


def pl_to_board(pl, score=0):
    out = []
    for pos, ent in enumerate(pl):
        if ent is not None:
            pid, rot = ent
            out.append({'pos': pos, 'piece_id': pid, 'rotation': rot})
    return {'placement': out, 'placed': len(out), 'matched': score, 'score': score}


def score_pl(pl, pieces):
    sc = 0
    for pos in range(256):
        if pl[pos] is None: continue
        r, c = pos // 16, pos % 16
        pid, rot = pl[pos]
        edges = pieces[(pid, rot)]
        if c < 15 and pl[pos+1] is not None:
            r_pid, r_rot = pl[pos+1]
            if edges[1] == pieces[(r_pid, r_rot)][3] and not is_border(edges[1]):
                sc += 1
        if r < 15 and pl[pos+16] is not None:
            b_pid, b_rot = pl[pos+16]
            if edges[2] == pieces[(b_pid, b_rot)][0] and not is_border(edges[2]):
                sc += 1
    return sc


def hint_graft(pl):
    pl = list(pl)
    # Build piece -> position map
    piece_to_pos = {}
    for pos in range(256):
        if pl[pos] is not None:
            piece_to_pos[pl[pos][0]] = pos

    for hpos, (hpid, hrot) in HINTS.items():
        if hpid not in piece_to_pos:
            # Hint piece is missing? Just place it.
            current_at_hpos = pl[hpos]
            pl[hpos] = (hpid, hrot)
            continue
        current_pos_of_hpid = piece_to_pos[hpid]
        if current_pos_of_hpid == hpos:
            # Already in place; check rotation
            if pl[hpos][1] != hrot:
                pl[hpos] = (hpid, hrot)
            continue
        # Swap: pl[hpos] and pl[current_pos_of_hpid]
        what_at_hpos = pl[hpos]
        pl[hpos] = (hpid, hrot)
        pl[current_pos_of_hpid] = what_at_hpos  # keep its current rotation
        piece_to_pos[hpid] = hpos
        if what_at_hpos is not None:
            piece_to_pos[what_at_hpos[0]] = current_pos_of_hpid
    return pl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    pieces = load_pieces()
    b = json.load(open(args.inp))
    pl = board_to_pl(b)
    score_before = b.get('matched', b.get('score', 0))
    hints_before = sum(1 for hp, (hpid, _) in HINTS.items() if pl[hp] and pl[hp][0] == hpid)
    pl_grafted = hint_graft(pl)
    score_after = score_pl(pl_grafted, pieces)
    hints_after = sum(1 for hp, (hpid, _) in HINTS.items() if pl_grafted[hp] and pl_grafted[hp][0] == hpid)
    print(f"Before: matched={score_before} hints={hints_before}/5")
    print(f"After:  matched={score_after} hints={hints_after}/5")
    with open(args.out, 'w') as f:
        json.dump(pl_to_board(pl_grafted, score=score_after), f)
    print(f"Saved to {args.out}")


if __name__ == '__main__':
    main()
