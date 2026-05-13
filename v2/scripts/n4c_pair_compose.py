#!/usr/bin/env python3
"""
N4c: cooperative pair-of-Δ=-1-swaps composition test.

For each pair of Δ=-1 swaps from N4 that share an endpoint:
  Swap1: a↔b (Δ=-1)
  Swap2: b↔c (Δ=-1)
  Composed: cyclic (a→b→c→a) = 3-cycle.

  Compute Δ of the composed move. If Δ ≥ 0, we have a cooperative
  3-cycle that crosses the lock.

But — we already exhaustively tested all 3-cycles on the 38 mismatch
cells in N4b/cycle_scan and found ZERO at Δ ≥ 0. So if these Δ=-1
swaps lie inside the mismatch cells, this test is REDUNDANT.

Actually the Δ=-1 swaps in N4 included edges between mismatch cells
AND mismatch-to-matched. Let's check: are any Δ=-1 swaps from N4 of
the form "mismatch cell ↔ matched cell"? If yes, composition would
give a 3-cycle involving a matched cell — which is OUTSIDE the
N4b/cycle_scan domain.

This is the missing experiment. Let me find such pairs and compose.
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

ROOT = Path("/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2")
PATCH = ROOT / "output/n5_patch/patch_data.json"

sys.path.insert(0, str(ROOT / "scripts"))
from n5_patch_analysis import load_pieces, load_board, rotate_edges, BORDER, SIZE, N_CELLS

# Reuse n3_pair_rotation helpers.
from n3_pair_rotation import piece_border_ok, cell_match_score


def best_rot_score_at(board, pieces, pos, pid):
    best = -1
    best_rot = 0
    for rot in range(4):
        if not piece_border_ok(pid, rot, pieces, pos):
            continue
        edges = rotate_edges(pieces[pid], rot)
        row, col = pos // SIZE, pos % SIZE
        s = 0
        if row > 0:
            np_ = board[pos - SIZE]
            if np_:
                _, _, ns, _ = rotate_edges(pieces[np_[0]], np_[1])
                if edges[0] != BORDER and ns != BORDER and edges[0] == ns: s += 1
        if col < SIZE - 1:
            np_ = board[pos + 1]
            if np_:
                _, _, _, nw = rotate_edges(pieces[np_[0]], np_[1])
                if edges[1] != BORDER and nw != BORDER and edges[1] == nw: s += 1
        if row < SIZE - 1:
            np_ = board[pos + SIZE]
            if np_:
                nn, _, _, _ = rotate_edges(pieces[np_[0]], np_[1])
                if edges[2] != BORDER and nn != BORDER and edges[2] == nn: s += 1
        if col > 0:
            np_ = board[pos - 1]
            if np_:
                _, ne, _, _ = rotate_edges(pieces[np_[0]], np_[1])
                if edges[3] != BORDER and ne != BORDER and edges[3] == ne: s += 1
        if s > best:
            best = s
            best_rot = rot
    return best, best_rot


def evaluate_3cycle(board, pieces, a, b, c):
    """Cyclic perm: piece(a)→b, piece(b)→c, piece(c)→a. Each placed at its
    best rotation. Returns Δ vs current."""
    # Pieces to be placed.
    new_pids = {
        b: board[a][0],
        c: board[b][0],
        a: board[c][0],
    }
    # Build tentative board.
    tentative = list(board)
    # Two-pass.
    for pos, pid in new_pids.items():
        sc, rot = best_rot_score_at(board, pieces, pos, pid)
        if sc < 0:
            return None
        tentative[pos] = (pid, rot)
    for pos, pid in new_pids.items():
        sc, rot = best_rot_score_at(tentative, pieces, pos, pid)
        if sc < 0:
            return None
        tentative[pos] = (pid, rot)

    # Score change.
    def s(brd):
        n = 0
        for pos in range(N_CELLS):
            cell = brd[pos]
            if cell is None:
                continue
            pid, rot = cell
            edges = rotate_edges(pieces[pid], rot)
            row, col = pos // SIZE, pos % SIZE
            if col < SIZE - 1:
                np_ = brd[pos + 1]
                if np_:
                    e2 = rotate_edges(pieces[np_[0]], np_[1])
                    if edges[1] != BORDER and e2[3] != BORDER and edges[1] == e2[3]:
                        n += 1
            if row < SIZE - 1:
                np_ = brd[pos + SIZE]
                if np_:
                    e2 = rotate_edges(pieces[np_[0]], np_[1])
                    if edges[2] != BORDER and e2[0] != BORDER and edges[2] == e2[0]:
                        n += 1
        return n

    s_old = s(board)
    s_new = s(tentative)
    return s_new - s_old


def main():
    pieces = load_pieces()
    board, score = load_board()
    print(f"Board score {score}")

    # Enumerate ALL non-adjacent transpositions, classify by Δ.
    def border_class(pid):
        return sum(1 for c in pieces[pid] if c == BORDER)

    by_class = {0: [], 1: [], 2: []}
    for pos in range(N_CELLS):
        cell = board[pos]
        if cell is None:
            continue
        by_class[border_class(cell[0])].append(pos)

    cur_locals = [
        cell_match_score(board, pieces, pos) for pos in range(N_CELLS)
    ]

    # Get all Δ=-1 swaps from board.
    delta_m1_swaps = []
    for cls, cells in by_class.items():
        for i in range(len(cells)):
            for j in range(i+1, len(cells)):
                a, b = cells[i], cells[j]
                r_a, c_a = a // SIZE, a % SIZE
                r_b, c_b = b // SIZE, b % SIZE
                if abs(r_a-r_b)+abs(c_a-c_b) == 1:
                    continue
                pid_a, _ = board[a]
                pid_b, _ = board[b]
                new_a, _ = best_rot_score_at(board, pieces, a, pid_b)
                new_b, _ = best_rot_score_at(board, pieces, b, pid_a)
                if new_a < 0 or new_b < 0:
                    continue
                d = (new_a - cur_locals[a]) + (new_b - cur_locals[b])
                if d == -1:
                    delta_m1_swaps.append((a, b))
    print(f"Total Δ=-1 swaps: {len(delta_m1_swaps)}")

    # Build adjacency: which Δ=-1 swaps share an endpoint?
    by_pos = {}
    for (a, b) in delta_m1_swaps:
        by_pos.setdefault(a, []).append(b)
        by_pos.setdefault(b, []).append(a)
    n_share = sum(1 for v in by_pos.values() if len(v) >= 2)
    print(f"Cells appearing in 2+ Δ=-1 swaps: {n_share}")

    # For each cell with >=2 swaps, try every triple (a,b,c) where ab and bc are both Δ=-1.
    seen = set()
    n_tried = 0
    n_zero_plus = 0
    best_d = -3
    best_3 = None
    for b in by_pos:
        nbrs = by_pos[b]
        for i in range(len(nbrs)):
            for j in range(len(nbrs)):
                if i == j: continue
                a, c = nbrs[i], nbrs[j]
                if a == c: continue
                key = tuple(sorted([a, b, c]))
                if key in seen: continue
                seen.add(key)
                # 3-cycle a→b→c→a
                d = evaluate_3cycle(board, pieces, a, b, c)
                if d is None: continue
                n_tried += 1
                if d > best_d:
                    best_d = d
                    best_3 = (a, b, c)
                if d >= 0:
                    n_zero_plus += 1
                    ra, ca = a // SIZE, a % SIZE
                    rb, cb = b // SIZE, b % SIZE
                    rc, cc = c // SIZE, c % SIZE
                    print(f"  ★ 3-cycle Δ={d:+}: ({ra},{ca})→({rb},{cb})→({rc},{cc})→")

    print(f"\nTotal 3-cycles tested from Δ=-1 pair compositions: {n_tried}")
    print(f"  Δ ≥ 0: {n_zero_plus}")
    print(f"  Best Δ found: {best_d} on cycle {best_3}")


if __name__ == "__main__":
    sys.exit(main() or 0)
