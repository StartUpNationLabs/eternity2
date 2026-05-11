#!/usr/bin/env python3
"""Random sampling of 4-cycle moves on a board.

Each "4-cycle" picks 4 cells (a, b, c, d) from mismatch-incident
interior cells and tries the 6 cyclic permutations of pieces among
these 4 cells, with all 4⁴=256 rotation combos. Accept any
improvement.

For exhaustive coverage of moat-depth-4 hypothesis, we'd need
C(47,4) × 6 × 256 = ~274M trials. We sample N=1000 random
quadruples for a feasibility test.
"""

import argparse
import json
import sys
import time
from itertools import permutations
from pathlib import Path

import random


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
            pieces.append(tuple(parse_csv_piece_word(cols[i]) for i in range(4)))
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
        if pid < 0: out.append((BORDER,)*4)
        else: out.append(rotate_quad(pieces[pid], rot))
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
    ap.add_argument("--n-samples", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    pieces = load_pieces(args.puzzle)
    j = json.load(open(args.board_json))
    placement = j['placement']
    board_pid = [(c['piece_id'], c['rotation']) if c else (-1, 0) for c in placement]

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
                              and cell_class_pos(c) == 2])
    print(f"# {len(candidate_cells)} candidate interior mismatch-incident cells", file=sys.stderr)

    rng = random.Random(args.seed)
    best_score = initial_score
    best_board = list(board_pid)
    n_improvements = 0

    # 6 cyclic permutations of (a,b,c,d):
    # (a,b,c,d) → (b,c,d,a), (c,d,a,b), (d,a,b,c) are rotations.
    # Plus mirror cycles. For "4-cycle moves" (not full permutations),
    # try all 4!-2 = 22 NON-identity permutations? Actually 4! = 24,
    # minus identity = 23 non-trivial. Of these, the 2-element-fixed
    # permutations are 2-swaps already tested. To get NEW moves, we
    # want permutations where ALL 4 cells get different pieces.
    # These are the 9 derangements of 4 elements.
    pids_indices = list(permutations(range(4)))
    # Filter to derangements (no i s.t. perm[i] == i).
    derangements = [p for p in pids_indices if all(p[i] != i for i in range(4))]
    print(f"# {len(derangements)} derangements of 4 elements", file=sys.stderr)

    t0 = time.time()
    for trial_i in range(args.n_samples):
        # Sample 4 distinct cells.
        sample = rng.sample(candidate_cells, 4)
        p0, p1, p2, p3 = sample
        old_pids = [board_pid[p][0] for p in sample]
        old_rots = [board_pid[p][1] for p in sample]
        # Skip if any piece is not interior.
        if any(piece_class(pieces[pid]) != 2 for pid in old_pids):
            continue
        for deran in derangements:
            new_pids = [old_pids[deran[i]] for i in range(4)]
            # Try 4^4 = 256 rotation combos.
            for r0 in range(4):
                for r1 in range(4):
                    for r2 in range(4):
                        for r3 in range(4):
                            tmp_board = list(board_pid)
                            tmp_board[p0] = (new_pids[0], r0)
                            tmp_board[p1] = (new_pids[1], r1)
                            tmp_board[p2] = (new_pids[2], r2)
                            tmp_board[p3] = (new_pids[3], r3)
                            tmp_quads = quads_from_board(tmp_board, pieces)
                            s = score_quads(tmp_quads)
                            if s > best_score:
                                best_score = s
                                best_board = tmp_board
                                n_improvements += 1
                                print(f"# IMPROVEMENT trial {trial_i}: cells "
                                      f"{[f'({p%W},{p//W})' for p in sample]} "
                                      f"deran {deran} rots ({r0},{r1},{r2},{r3}) → {s}",
                                      file=sys.stderr)
                                board_pid = best_board  # accept and continue
                                old_pids = [board_pid[p][0] for p in sample]
                                old_rots = [board_pid[p][1] for p in sample]
                                if n_improvements >= 5:
                                    break
                        if n_improvements >= 5: break
                    if n_improvements >= 5: break
                if n_improvements >= 5: break
            if n_improvements >= 5: break
        if n_improvements >= 5: break
        if (trial_i + 1) % 50 == 0:
            elapsed = time.time() - t0
            print(f"# {trial_i+1}/{args.n_samples}, best={best_score}, "
                  f"imp={n_improvements}, t={elapsed:.0f}s", file=sys.stderr)

    print(f"\n=== DONE ===")
    print(f"initial: {initial_score}/480")
    print(f"final:   {best_score}/480 (delta +{best_score - initial_score})")
    print(f"trials: {args.n_samples} × {len(derangements)} derangements × 256 rotations")
    print(f"improvements: {n_improvements}")

    if args.out and best_score > initial_score:
        out_placement = [{"piece_id": int(p), "rotation": int(r)} if p >= 0 else None
                         for p, r in best_board]
        out = dict(j)
        out['placement'] = out_placement
        out['score'] = {"matched_edges": int(best_score), "total_edges": 480,
                        "percent": 100.0 * best_score / 480,
                        "placed_cells": sum(1 for p in best_board if p[0] >= 0),
                        "total_cells": W*H}
        with open(args.out, "w") as f:
            json.dump(out, f, indent=2)
        print(f"output: {args.out}")


if __name__ == "__main__":
    main()
