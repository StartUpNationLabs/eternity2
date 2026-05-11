#!/usr/bin/env python3
"""Brute-force 3-cycle search on a board: pick 3 cells (preferring
those incident to mismatched edges), cycle the pieces A→B→C→A, try
all 4³=64 rotation combos, accept best improvement.

Goal: empirically test whether 3-swap CAN improve the 450 board (or
449 boards), since 2-swap exhaustively cannot.

For computational feasibility, restrict to cells incident to ≥1
mismatched edge (~49 cells on 450 board). C(49, 3) = 18,424 triples
× 64 rot combos = 1.2M trials.
"""

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from itertools import combinations
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


def local_score_at(quads, pos):
    """Number of matched edges incident to cell pos."""
    x, y = pos % W, pos // W
    e = quads[pos]
    m = 0
    if y > 0:
        ne = quads[(y-1)*W+x]
        if e[0] == ne[2] and e[0] != BORDER: m += 1
    if x + 1 < W:
        ne = quads[y*W+x+1]
        if e[1] == ne[3] and e[1] != BORDER: m += 1
    if y + 1 < H:
        ne = quads[(y+1)*W+x]
        if e[2] == ne[0] and e[2] != BORDER: m += 1
    if x > 0:
        ne = quads[y*W+x-1]
        if e[3] == ne[1] and e[3] != BORDER: m += 1
    return m


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


def mismatch_incident_cells(quads):
    out = set()
    for y in range(H):
        for x in range(W):
            pos = y*W+x
            if x+1<W:
                a, b = quads[pos][1], quads[pos+1][3]
                if a!=BORDER and b!=BORDER and a!=b:
                    out.add(pos); out.add(pos+1)
            if y+1<H:
                a, b = quads[pos][2], quads[pos+W][0]
                if a!=BORDER and b!=BORDER and a!=b:
                    out.add(pos); out.add(pos+W)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board_json")
    ap.add_argument("--puzzle", default="../data/puzzles/size_16_official_eternity.csv")
    ap.add_argument("--max-trials", type=int, default=500_000,
                    help="cap on cell-triples to try")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    pieces = load_pieces(args.puzzle)
    j = json.load(open(args.board_json))
    placement = j['placement']
    board_pid = [(c['piece_id'], c['rotation']) if c else (-1, 0) for c in placement]

    # Hints (pinned).
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

    quads = quads_from_board(board_pid, pieces)
    initial_score = score_quads(quads)
    print(f"# initial: {initial_score}/480", file=sys.stderr)

    candidate_cells = sorted([c for c in mismatch_incident_cells(quads)
                              if c not in pinned_cells
                              and cell_class_pos(c) == 2])  # interior only for now
    print(f"# {len(candidate_cells)} candidate interior cells (mismatch-incident, not pinned)",
          file=sys.stderr)

    # All 3-tuples.
    triples = list(combinations(candidate_cells, 3))
    print(f"# {len(triples)} triples, * 6 cycle orderings * 64 rotations = {len(triples) * 6 * 64} trials",
          file=sys.stderr)
    triples = triples[:args.max_trials]

    best_score = initial_score
    best_board = list(board_pid)
    best_quads = list(quads)
    n_improvements = 0

    t0 = time.time()
    for trial_i, (p_a, p_b, p_c) in enumerate(triples):
        pid_a, rot_a = board_pid[p_a]
        pid_b, rot_b = board_pid[p_b]
        pid_c, rot_c = board_pid[p_c]
        # All pieces must be interior.
        if piece_class(pieces[pid_a]) != 2: continue
        if piece_class(pieces[pid_b]) != 2: continue
        if piece_class(pieces[pid_c]) != 2: continue

        # The 6 cyclic permutations (which piece goes to which cell, all rotations).
        # (A→A, B→B, C→C) = identity (skip)
        # (A→B, B→C, C→A): pid_a goes to B, pid_b to C, pid_c to A.
        # (A→C, B→A, C→B): mirror cycle.
        # (A→A, B→C, C→B): swap B↔C.
        # (A→C, B→B, C→A): swap A↔C.
        # (A→B, B→A, C→C): swap A↔B.
        # Skip 2-swap permutations (already exhaustively tested in NE10).
        # Only test the two 3-cycles.
        permutations_to_try = [
            # (cell_a_gets, cell_b_gets, cell_c_gets)
            (pid_c, pid_a, pid_b),  # A→B→C→A: A gets C, B gets A, C gets B
            (pid_b, pid_c, pid_a),  # A→C→B→A: A gets B, B gets C, C gets A
        ]
        for (new_a, new_b, new_c) in permutations_to_try:
            # Try all 4³ = 64 rotation combos.
            for r_a in range(4):
                for r_b in range(4):
                    for r_c in range(4):
                        # Apply hypothetically.
                        tmp_board = list(board_pid)
                        tmp_board[p_a] = (new_a, r_a)
                        tmp_board[p_b] = (new_b, r_b)
                        tmp_board[p_c] = (new_c, r_c)
                        tmp_quads = quads_from_board(tmp_board, pieces)
                        s = score_quads(tmp_quads)
                        if s > best_score:
                            best_score = s
                            best_board = tmp_board
                            best_quads = tmp_quads
                            n_improvements += 1
                            print(f"# IMPROVEMENT trial {trial_i}: cells ({p_a%W},{p_a//W})↔"
                                  f"({p_b%W},{p_b//W})↔({p_c%W},{p_c//W})  "
                                  f"rotations ({r_a},{r_b},{r_c}) → score={s}",
                                  file=sys.stderr)
        if (trial_i + 1) % 500 == 0:
            elapsed = time.time() - t0
            print(f"# {trial_i+1}/{len(triples)} triples, best={best_score}, "
                  f"improvements={n_improvements}, t={elapsed:.0f}s", file=sys.stderr)

    print(f"\n=== DONE ===")
    print(f"initial: {initial_score}/480")
    print(f"final:   {best_score}/480 (delta +{best_score - initial_score})")
    print(f"trials tested: {len(triples)} × 2 perms × 64 rots = {len(triples)*128}")
    print(f"improvements: {n_improvements}")

    if args.out and best_score > initial_score:
        out_placement = []
        for pos in range(W*H):
            pid, rot = best_board[pos]
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
            "placed_cells": int(sum(1 for p in best_board if p[0] >= 0)),
            "total_cells": W*H,
        }
        with open(args.out, "w") as f:
            json.dump(out, f, indent=2)
        print(f"output: {args.out}")


if __name__ == "__main__":
    main()
