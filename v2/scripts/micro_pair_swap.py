#!/usr/bin/env python3
"""For a board with multi-pair-scarce mismatched edges, try ALL swaps
of (pair-providing pieces) into (mismatch cells), with all rotations,
and report any improvement.

For each multi-pair (a,b) with N >= 2 mismatches:
  - Identify the K candidate pieces with both colors a, b.
  - Identify the M cells incident to those mismatches.
  - For each (candidate_piece × current_cell pair × target_cell × all rotations),
    compute hypothetical 2-piece swap, score the result.
  - Accept any swap with positive delta.
  - Iterate until no improvement.
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


W = 16
H = 16
BORDER = 0


def parse_csv_piece_word(s):
    v = int(s.strip(), 2)
    if v == 65535:
        return 0
    return v


def load_pieces(path):
    pieces = []
    with open(path) as f:
        size = int(f.readline().strip())
        for pid, line in enumerate(f):
            cols = line.strip().split(',')
            if len(cols) < 4:
                continue
            quad = tuple(parse_csv_piece_word(cols[i]) for i in range(4))
            pieces.append(quad)
    return pieces


def piece_class(quad):
    n = sum(1 for c in quad if c == BORDER)
    return 0 if n >= 2 else (1 if n == 1 else 2)


def cell_class_pos(pos):
    x, y = pos % W, pos // W
    n = (x == 0) + (x == W-1) + (y == 0) + (y == H-1)
    return 0 if n >= 2 else (1 if n == 1 else 2)


def rotate_quad(q, rot):
    t, r, b, l = q
    if rot == 0: return (t, r, b, l)
    if rot == 1: return (l, t, r, b)
    if rot == 2: return (b, l, t, r)
    if rot == 3: return (r, b, l, t)


def quads_from_board(board_pid, pieces):
    out = []
    for pid, rot in board_pid:
        if pid < 0:
            out.append((BORDER, BORDER, BORDER, BORDER))
        else:
            out.append(rotate_quad(pieces[pid], rot))
    return out


def score_quads(quads):
    s = 0
    for y in range(H):
        for x in range(W):
            pos = y*W+x
            if x+1<W:
                if quads[pos][1] == quads[pos+1][3] and quads[pos][1] != BORDER:
                    s += 1
            if y+1<H:
                if quads[pos][2] == quads[pos+W][0] and quads[pos][2] != BORDER:
                    s += 1
    return s


def find_mismatches(quads):
    out = []
    for y in range(H):
        for x in range(W):
            pos = y*W+x
            if x+1<W:
                a, b = quads[pos][1], quads[pos+1][3]
                if a!=BORDER and b!=BORDER and a!=b:
                    out.append(('h', pos, a, b))
            if y+1<H:
                a, b = quads[pos][2], quads[pos+W][0]
                if a!=BORDER and b!=BORDER and a!=b:
                    out.append(('v', pos, a, b))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board_json")
    ap.add_argument("--puzzle", default="../data/puzzles/size_16_official_eternity.csv")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    pieces = load_pieces(args.puzzle)
    j = json.load(open(args.board_json))
    placement = j['placement']
    board_pid = [(c['piece_id'], c['rotation']) if c else (-1, 0) for c in placement]
    quads = quads_from_board(board_pid, pieces)
    initial_score = score_quads(quads)
    print(f"# initial: {initial_score}/480", file=sys.stderr)

    # Hint pieces (pinned).
    hints = {}
    with open(args.puzzle) as f:
        size = int(f.readline().strip())
        for pid, line in enumerate(f):
            cols = line.strip().split(',')
            if len(cols) >= 7:
                x = int(cols[4]); y = int(cols[5]); rot = int(cols[6])
                if (x, y, rot) != (0, 0, 0):
                    hints[y*W+x] = pid
    pinned_cells = set(hints.keys())

    # piece_color_index: color -> set of piece ids
    color_in_pieces = defaultdict(set)
    for pid, q in enumerate(pieces):
        for c in q:
            color_in_pieces[c].add(pid)

    # Find mismatches grouped by sorted color pair.
    pair_to_mismatches = defaultdict(list)
    for m in find_mismatches(quads):
        typ, pos, a, b = m
        pair = tuple(sorted([a, b]))
        pair_to_mismatches[pair].append(m)

    multi_pairs = sorted([(p, len(ms)) for p, ms in pair_to_mismatches.items() if len(ms) >= 2],
                         key=lambda x: -x[1])
    print(f"# multi-pairs: {multi_pairs}", file=sys.stderr)

    best_board_pid = list(board_pid)
    best_score = initial_score
    n_improvements = 0

    # Outer loop: try improvements from each multi-pair.
    # Then also ALL pieces with EITHER color a or b; not just the "both colors"
    # pieces, because the joint-resolution may cascade.
    for outer in range(5):
        outer_start = best_score
        for pair, _ in multi_pairs:
            a, b = pair
            # Candidate pieces with BOTH colors.
            candidate_pids = sorted(color_in_pieces[a] & color_in_pieces[b])
            # Restrict to interior pieces (since target cells are interior).
            candidate_pids = [p for p in candidate_pids if piece_class(pieces[p]) == 2]
            if not candidate_pids:
                continue
            ms = pair_to_mismatches[pair]
            mismatch_cells = set()
            for typ, pos, _, _ in ms:
                if typ == 'h':
                    mismatch_cells.add(pos)
                    mismatch_cells.add(pos + 1)
                else:
                    mismatch_cells.add(pos)
                    mismatch_cells.add(pos + W)
            mismatch_cells = sorted(mismatch_cells - pinned_cells)
            if not mismatch_cells:
                continue

            # For each (candidate piece, target cell, target rotation):
            # find current location of candidate piece (call it source_cell);
            # do the swap (source<->target with both rotations enumerated).
            # Score and check if improved.
            for cand_pid in candidate_pids:
                # Find current location.
                src_cell = None
                src_rot = None
                for cell in range(W*H):
                    if best_board_pid[cell][0] == cand_pid:
                        src_cell = cell
                        src_rot = best_board_pid[cell][1]
                        break
                if src_cell is None:
                    continue
                if src_cell in pinned_cells:
                    continue
                # Get the piece currently at the source cell (it's the candidate).
                # We swap with each target.
                for tgt_cell in mismatch_cells:
                    if tgt_cell == src_cell:
                        continue
                    if tgt_cell in pinned_cells:
                        continue
                    # The piece currently at the target cell.
                    tgt_pid, tgt_rot = best_board_pid[tgt_cell]
                    # Both pieces must be interior.
                    if piece_class(pieces[tgt_pid]) != 2:
                        continue
                    # Try all 4x4 rotation combos.
                    best_pair_delta = 0
                    best_pair_swap = None
                    for r_t in range(4):  # rotation of cand at target
                        for r_s in range(4):  # rotation of tgt at source
                            new_board = list(best_board_pid)
                            new_board[tgt_cell] = (cand_pid, r_t)
                            new_board[src_cell] = (tgt_pid, r_s)
                            new_quads = quads_from_board(new_board, pieces)
                            new_score = score_quads(new_quads)
                            delta = new_score - best_score
                            if delta > best_pair_delta:
                                best_pair_delta = delta
                                best_pair_swap = (r_t, r_s)
                    if best_pair_delta > 0:
                        r_t, r_s = best_pair_swap
                        best_board_pid[tgt_cell] = (cand_pid, r_t)
                        best_board_pid[src_cell] = (tgt_pid, r_s)
                        best_score += best_pair_delta
                        n_improvements += 1
                        print(f"# IMPROVEMENT: pair {pair}, "
                              f"swap pid={cand_pid} ({src_cell%W},{src_cell//W}) ↔ "
                              f"pid={tgt_pid} ({tgt_cell%W},{tgt_cell//W}), "
                              f"rots ({r_t},{r_s}), delta=+{best_pair_delta}, "
                              f"new score={best_score}", file=sys.stderr)
        if best_score == outer_start:
            print(f"# outer {outer+1}: no further improvement, stopping", file=sys.stderr)
            break
        # Recompute multi_pairs based on NEW board.
        quads = quads_from_board(best_board_pid, pieces)
        pair_to_mismatches = defaultdict(list)
        for m in find_mismatches(quads):
            typ, pos, a, b = m
            pair = tuple(sorted([a, b]))
            pair_to_mismatches[pair].append(m)
        multi_pairs = sorted([(p, len(ms)) for p, ms in pair_to_mismatches.items() if len(ms) >= 2],
                              key=lambda x: -x[1])

    print(f"\n=== DONE ===")
    print(f"initial: {initial_score}/480")
    print(f"final:   {best_score}/480 (delta +{best_score - initial_score})")
    print(f"improvements found: {n_improvements}")

    if args.out and best_score > initial_score:
        out_placement = []
        for cell in range(W*H):
            pid, rot = best_board_pid[cell]
            if pid < 0:
                out_placement.append(None)
            else:
                out_placement.append({"piece_id": int(pid), "rotation": int(rot)})
        out = dict(j)
        out['placement'] = out_placement
        out['score'] = {
            "matched_edges": int(best_score),
            "total_edges": 480,
            "percent": 100.0 * best_score / 480,
            "placed_cells": int(sum(1 for p in best_board_pid if p[0] >= 0)),
            "total_cells": W*H,
        }
        with open(args.out, "w") as f:
            json.dump(out, f, indent=2)
        print(f"output: {args.out}")


if __name__ == "__main__":
    main()
