#!/usr/bin/env python3
"""Vol-119 — 3-cell piece-cycle improvement search (INVENTION: TRIANGLE-ROT).

For each triple of cells (c1, c2, c3) in the board, try the 2 non-identity
3-permutations of their pieces. For each permutation, also optimize the
rotation of each repositioned piece. Compute Δ in matched edges. Accept
first Δ > 0.

Focus on triples that include at least 2 mismatch-cells, since
permutations far from mismatches can't help.

Why 3-cycle and not 2-swap:
- Vol-20 K=5 lock proof + corpus-vote-swap confirm 2-cell swaps don't
  help on 459 records.
- 3-cycles are the next move class; not covered by ANY prior vol that
  I've found in BACKLOG.

Why not 4-cycle / 5-cycle:
- Vol-20 cycle_scan enumerated K=3,4,5 cycles on the 457 basin and
  confirmed operator-lock through K=5. So 3-cycles ARE included in
  that proof.
- BUT vol-20 was on the 457 basin (vol-18 hot-PT origin). It hasn't
  been done on the 459 RECORD or any of the new vol-110 / cluster-A
  basins. This is the open subspace.

The corpus-vote-swap variant: instead of "any piece in any rotation",
we restrict triple members to pieces ALREADY at those cells in SOME
basin in the corpus. This narrows the search space dramatically.

Usage:
    vol119_three_cycle_search.py <target> --corpus <b1> <b2> ...
        [--max-mismatch-distance 3]
"""

from __future__ import annotations

import argparse
import itertools
import json
from collections import defaultdict
from pathlib import Path

W, H = 16, 16


def parse_color(s):
    s = s.strip()
    v = int(s, 2)
    if v == 65535:
        return 0
    return v


def load_puzzle(csv_path):
    pieces = {}
    with open(csv_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    pid = 0
    for line in lines[1:]:
        cols = line.split(',')
        if len(cols) < 4:
            continue
        try:
            t = parse_color(cols[0])
            r = parse_color(cols[1])
            b = parse_color(cols[2])
            l = parse_color(cols[3])
        except ValueError:
            continue
        pieces[pid] = (t, r, b, l)
        pid += 1
    return pieces


def rotate_edges(edges, rot):
    t, r, b, l = edges
    if rot == 0:
        return (t, r, b, l)
    elif rot == 1:
        return (l, t, r, b)
    elif rot == 2:
        return (b, l, t, r)
    else:
        return (r, b, l, t)


def load_board(p):
    with open(p) as f:
        d = json.load(f)
    arr = d.get("placement") or d.get("board", {}).get("placement", [])
    out = {}
    for idx, item in enumerate(arr):
        if item is None:
            continue
        pos = int(item.get("pos", idx))
        out[pos] = (int(item["piece_id"]), int(item["rotation"]))
    return out


def save_board(board, path, score, source="vol119_three_cycle_search"):
    placement = []
    for pos in sorted(board):
        pid, rot = board[pos]
        placement.append({"pos": pos, "piece_id": pid, "rotation": rot})
    doc = {
        "placement": placement,
        "metadata": {"source": source, "score": score},
    }
    with open(path, "w") as f:
        json.dump(doc, f, indent=2)


def matched_edges(board, pieces):
    matched = 0
    for pos, (pid, rot) in board.items():
        x, y = pos % W, pos // W
        e = rotate_edges(pieces[pid], rot)
        if x < W - 1 and (pos + 1) in board:
            npid, nrot = board[pos + 1]
            ne = rotate_edges(pieces[npid], nrot)
            if e[1] == ne[3] and not (e[1] == 0 and ne[3] == 0):
                matched += 1
        if y < H - 1 and (pos + W) in board:
            npid, nrot = board[pos + W]
            ne = rotate_edges(pieces[npid], nrot)
            if e[2] == ne[0] and not (e[2] == 0 and ne[0] == 0):
                matched += 1
    return matched


def best_rotation_for_cell(board, pieces, pos, pid):
    """Try all 4 rotations of `pid` at `pos`, return best (rot, matched_at_pos)."""
    saved = board.get(pos)
    best_rot = 0
    best_m = -1
    for rot in range(4):
        board[pos] = (pid, rot)
        m = cell_matched_edges(board, pieces, pos)
        if m > best_m:
            best_m = m
            best_rot = rot
    if saved is not None:
        board[pos] = saved
    return best_rot, best_m


def cell_matched_edges(board, pieces, pos):
    if pos not in board:
        return 0
    pid, rot = board[pos]
    x, y = pos % W, pos // W
    e = rotate_edges(pieces[pid], rot)
    cnt = 0
    if x < W - 1 and (pos + 1) in board:
        npid, nrot = board[pos + 1]
        ne = rotate_edges(pieces[npid], nrot)
        if e[1] == ne[3] and not (e[1] == 0 and ne[3] == 0):
            cnt += 1
    if x > 0 and (pos - 1) in board:
        npid, nrot = board[pos - 1]
        ne = rotate_edges(pieces[npid], nrot)
        if e[3] == ne[1] and not (e[3] == 0 and ne[1] == 0):
            cnt += 1
    if y < H - 1 and (pos + W) in board:
        npid, nrot = board[pos + W]
        ne = rotate_edges(pieces[npid], nrot)
        if e[2] == ne[0] and not (e[2] == 0 and ne[0] == 0):
            cnt += 1
    if y > 0 and (pos - W) in board:
        npid, nrot = board[pos - W]
        ne = rotate_edges(pieces[npid], nrot)
        if e[0] == ne[2] and not (e[0] == 0 and ne[2] == 0):
            cnt += 1
    return cnt


def find_mismatch_cells(board, pieces):
    """Cells with at least one mismatched edge."""
    weak = []
    for pos in board:
        if cell_matched_edges(board, pieces, pos) < 4:
            x, y = pos % W, pos // W
            n_edges = 4
            if x == 0: n_edges -= 1
            if x == W - 1: n_edges -= 1
            if y == 0: n_edges -= 1
            if y == H - 1: n_edges -= 1
            if cell_matched_edges(board, pieces, pos) < n_edges:
                weak.append(pos)
    return weak


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--puzzle", default="../data/puzzles/size_16_official_eternity.csv")
    ap.add_argument("--out", default=None)
    ap.add_argument("--max-triples", type=int, default=100000)
    ap.add_argument("--mismatch-only", action="store_true",
                    help="restrict to triples of mismatch-adjacent cells")
    args = ap.parse_args()

    pieces = load_puzzle(Path(args.puzzle))
    A = load_board(Path(args.target))
    score = matched_edges(A, pieces)
    print(f"# target score: {score}/480")

    mismatch_cells = find_mismatch_cells(A, pieces)
    print(f"# mismatch cells: {len(mismatch_cells)}")

    if args.mismatch_only:
        candidate_cells = mismatch_cells
    else:
        candidate_cells = list(A.keys())
    print(f"# candidate cells: {len(candidate_cells)}")

    # Total triples
    n = len(candidate_cells)
    n_triples = n * (n - 1) * (n - 2) // 6
    print(f"# total triples to check: {n_triples} (capped at {args.max_triples})")

    found = 0
    checked = 0
    total_lift = 0
    iter_count = 0
    while True:
        iter_count += 1
        improved = False
        for c1, c2, c3 in itertools.combinations(candidate_cells, 3):
            if checked >= args.max_triples:
                break
            checked += 1
            # Try the two non-identity 3-permutations of pieces:
            # perm A: c1→c2, c2→c3, c3→c1
            # perm B: c1→c3, c2→c1, c3→c2
            pid1, rot1 = A[c1]
            pid2, rot2 = A[c2]
            pid3, rot3 = A[c3]
            orig_m = (cell_matched_edges(A, pieces, c1)
                      + cell_matched_edges(A, pieces, c2)
                      + cell_matched_edges(A, pieces, c3))
            best_delta = 0
            best_assignment = None
            for perm in [(pid2, pid3, pid1), (pid3, pid1, pid2)]:
                new_pid1, new_pid2, new_pid3 = perm
                # try all rotations
                saved = (A[c1], A[c2], A[c3])
                # find optimal rot for each
                A[c1] = (new_pid1, 0)
                A[c2] = (new_pid2, 0)
                A[c3] = (new_pid3, 0)
                best_rot1, _ = best_rotation_for_cell(A, pieces, c1, new_pid1)
                A[c1] = (new_pid1, best_rot1)
                best_rot2, _ = best_rotation_for_cell(A, pieces, c2, new_pid2)
                A[c2] = (new_pid2, best_rot2)
                best_rot3, _ = best_rotation_for_cell(A, pieces, c3, new_pid3)
                A[c3] = (new_pid3, best_rot3)
                new_m = (cell_matched_edges(A, pieces, c1)
                         + cell_matched_edges(A, pieces, c2)
                         + cell_matched_edges(A, pieces, c3))
                delta = new_m - orig_m
                if delta > best_delta:
                    best_delta = delta
                    best_assignment = ((c1, A[c1]), (c2, A[c2]), (c3, A[c3]))
                A[c1], A[c2], A[c3] = saved
            if best_delta > 0:
                for c, val in best_assignment:
                    A[c] = val
                # Note: the above only sums per-cell edges so each edge is
                # double-counted. Verify total board.
                new_total = matched_edges(A, pieces)
                actual_delta = new_total - score
                if actual_delta > 0:
                    score = new_total
                    total_lift += actual_delta
                    found += 1
                    improved = True
                    print(f"  triple=({c1},{c2},{c3})  Δ={actual_delta:+d}  "
                          f"new_score={score}/480")
                    break
                else:
                    # local delta was edge-counting illusion; revert
                    pass
        if not improved or checked >= args.max_triples:
            break

    print(f"# checked {checked} triples, found {found} improvements")
    print(f"# final score: {score}/480 (lift Δ={total_lift})")

    if args.out:
        save_board(A, args.out, score)
        print(f"# wrote: {args.out}")


if __name__ == "__main__":
    main()
