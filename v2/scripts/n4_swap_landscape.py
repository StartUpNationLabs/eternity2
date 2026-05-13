#!/usr/bin/env python3
"""
N4 step 1: characterise the 2-cell-swap landscape from the 457 board.

For every pair (a, b) of cells on the board:
- swap pieces at a and b
- try all 16 (rot_a', rot_b') combinations for the new positions
- compute Δ = score(swapped) - 457 at the best of 16

Report:
- distribution of best-Δ across all 32k pairs
- count of pairs with Δ >= 0 (the SA-acceptable moves)
- count with Δ = -1, -2, ... (the cooperative-but-uphill moves)

This is the energy landscape of single-transposition SA. If the
distribution shows non-zero acceptance at any T, the operator-lock
is temperature-relaxable. If even at large T everything's deep
uphill, we need cooperative moves.
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2")
sys.path.insert(0, str(ROOT / "scripts"))
from n5_patch_analysis import (
    load_pieces,
    load_board,
    rotate_edges,
    BORDER,
    SIZE,
    N_CELLS,
)


def piece_border_ok(pid, rot, pieces, pos):
    row, col = pos // SIZE, pos % SIZE
    edges = rotate_edges(pieces[pid], rot)
    if row == 0 and edges[0] != BORDER: return False
    if row != 0 and edges[0] == BORDER: return False
    if col == SIZE - 1 and edges[1] != BORDER: return False
    if col != SIZE - 1 and edges[1] == BORDER: return False
    if row == SIZE - 1 and edges[2] != BORDER: return False
    if row != SIZE - 1 and edges[2] == BORDER: return False
    if col == 0 and edges[3] != BORDER: return False
    if col != 0 and edges[3] == BORDER: return False
    return True


def cell_local_score(board, pieces, pos):
    """Score of pos: count of matched edges with its 4 neighbours."""
    cell = board[pos]
    if cell is None:
        return 0
    pid, rot = cell
    edges = rotate_edges(pieces[pid], rot)
    row, col = pos // SIZE, pos % SIZE
    s = 0
    if row > 0:
        np = board[pos - SIZE]
        if np:
            _, _, ns, _ = rotate_edges(pieces[np[0]], np[1])
            if edges[0] != BORDER and ns != BORDER and edges[0] == ns: s += 1
    if col < SIZE - 1:
        np = board[pos + 1]
        if np:
            _, _, _, nw = rotate_edges(pieces[np[0]], np[1])
            if edges[1] != BORDER and nw != BORDER and edges[1] == nw: s += 1
    if row < SIZE - 1:
        np = board[pos + SIZE]
        if np:
            nn, _, _, _ = rotate_edges(pieces[np[0]], np[1])
            if edges[2] != BORDER and nn != BORDER and edges[2] == nn: s += 1
    if col > 0:
        np = board[pos - 1]
        if np:
            _, ne, _, _ = rotate_edges(pieces[np[0]], np[1])
            if edges[3] != BORDER and ne != BORDER and edges[3] == ne: s += 1
    return s


def best_rotation_score(board, pieces, pos, candidate_pid):
    """Given piece candidate_pid newly placed at pos, the best score over 4 rotations."""
    best = -1
    best_rot = 0
    for rot in range(4):
        if not piece_border_ok(candidate_pid, rot, pieces, pos):
            continue
        # Score that piece at pos
        edges = rotate_edges(pieces[candidate_pid], rot)
        row, col = pos // SIZE, pos % SIZE
        s = 0
        if row > 0:
            np = board[pos - SIZE]
            if np:
                _, _, ns, _ = rotate_edges(pieces[np[0]], np[1])
                if edges[0] != BORDER and ns != BORDER and edges[0] == ns: s += 1
        if col < SIZE - 1:
            np = board[pos + 1]
            if np:
                _, _, _, nw = rotate_edges(pieces[np[0]], np[1])
                if edges[1] != BORDER and nw != BORDER and edges[1] == nw: s += 1
        if row < SIZE - 1:
            np = board[pos + SIZE]
            if np:
                nn, _, _, _ = rotate_edges(pieces[np[0]], np[1])
                if edges[2] != BORDER and nn != BORDER and edges[2] == nn: s += 1
        if col > 0:
            np = board[pos - 1]
            if np:
                _, ne, _, _ = rotate_edges(pieces[np[0]], np[1])
                if edges[3] != BORDER and ne != BORDER and edges[3] == ne: s += 1
        if s > best:
            best = s
            best_rot = rot
    return best, best_rot


def main():
    pieces = load_pieces()
    board, score = load_board()
    print(f"Board score: {score}")

    # CLASSIFY pieces by border class:
    # corner = 2 BORDER edges; edge = 1 BORDER; interior = 0.
    def border_class(pid):
        n_b = sum(1 for c in pieces[pid] if c == BORDER)
        return n_b
    # Pairs swappable: same border class.

    # For efficiency: compute "neighbour-induced constraint sums" — i.e., for
    # each pair (a, b), evaluate the delta in roughly O(8) operations.
    # NOTE: when a and b are adjacent, the edge between them counts ONCE
    # and changes in both rotations; we handle by recomputing the affected
    # ~8 cells' local scores before/after swap.

    print(f"\nPiece-class counts: corners={sum(1 for p in range(256) if border_class(p)==2)}, "
          f"edges={sum(1 for p in range(256) if border_class(p)==1)}, "
          f"interior={sum(1 for p in range(256) if border_class(p)==0)}")

    # Pre-compute cells' "current local score".
    cur_local = [cell_local_score(board, pieces, pos) for pos in range(N_CELLS)]

    # For each cell, also compute "best alternative-piece score" — if a different
    # piece comes in, what is the max score under its 4 rotations?

    # Iterate pairs. For each (a, b), only consider if border_class match.
    # Compute delta = (best_at_a_with_pid_b - cur_local[a]) +
    #                 (best_at_b_with_pid_a - cur_local[b])
    # But this DOUBLE-COUNTS the edge between a and b if adjacent.

    pair_deltas = Counter()
    improvers_list = []
    t0 = time.time()
    n_pairs_tested = 0
    n_pairs_skipped = 0

    # Group cells by border class.
    cells_by_class = {0: [], 1: [], 2: []}
    for pos in range(N_CELLS):
        cell = board[pos]
        if cell is None:
            continue
        bc = border_class(cell[0])
        cells_by_class[bc].append(pos)

    print(f"\nCells by border-class: corners={len(cells_by_class[2])}, "
          f"edges={len(cells_by_class[1])}, interior={len(cells_by_class[0])}")

    for cls in (0, 1, 2):
        cells = cells_by_class[cls]
        for i in range(len(cells)):
            for j in range(i + 1, len(cells)):
                a, b = cells[i], cells[j]
                pid_a, _ = board[a]
                pid_b, _ = board[b]
                # Swap pieces (use 4-rot best).
                # Compute new local at a (with piece pid_b) and at b (with piece pid_a).
                # Subtle: if a and b are adjacent, the in-between edge gets counted by both.
                # To avoid that, after swap we must recompute the affected cells' contributions.
                # For now, approximate: skip adjacent pairs (small fraction).
                row_a, col_a = a // SIZE, a % SIZE
                row_b, col_b = b // SIZE, b % SIZE
                if abs(row_a - row_b) + abs(col_a - col_b) == 1:
                    n_pairs_skipped += 1
                    continue
                # Score at a with piece pid_b (rotation best).
                new_a, rot_a = best_rotation_score(board, pieces, a, pid_b)
                new_b, rot_b = best_rotation_score(board, pieces, b, pid_a)
                if new_a < 0 or new_b < 0:
                    continue
                delta = (new_a - cur_local[a]) + (new_b - cur_local[b])
                pair_deltas[delta] += 1
                n_pairs_tested += 1
                if delta > 0:
                    improvers_list.append((a, b, delta, new_a, new_b, cur_local[a], cur_local[b], rot_a, rot_b))

        elapsed = time.time() - t0
        print(f"  class {cls}: done at {elapsed:.1f}s, tested {n_pairs_tested}, skipped(adj) {n_pairs_skipped}")

    elapsed = time.time() - t0
    print(f"\nTotal pairs tested: {n_pairs_tested}, skipped(adj): {n_pairs_skipped}")
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"\nΔ-distribution (single-transposition + best-rotation, non-adjacent pairs):")
    for delta in sorted(pair_deltas):
        print(f"  Δ = {delta:+3d}: {pair_deltas[delta]:6d}")

    if improvers_list:
        improvers_list.sort(key=lambda x: -x[2])
        print(f"\nIMPROVERS (top 20):")
        for (a, b, d, na, nb, la, lb, ra, rb) in improvers_list[:20]:
            r1, c1 = a // SIZE, a % SIZE
            r2, c2 = b // SIZE, b % SIZE
            pa = board[a][0]
            pb = board[b][0]
            print(f"  Δ={d:+d}: swap ({r1},{c1}) piece {pa} <-> ({r2},{c2}) piece {pb}  rot ({ra},{rb})  local {la}->{na}, {lb}->{nb}")
    else:
        print(f"\nNo improving non-adjacent transposition found.")

    # Now: list the 2 Δ=0 transpositions and 23 Δ=-1 transpositions.
    # These are the candidates for SA-acceptable moves that *may* compose
    # into improvements via a 3- or 4-cycle.
    print(f"\nNeutral and near-neutral non-adjacent transpositions:")
    # Re-collect them.
    neutrals = []
    near_neutrals = []
    # We need to iterate again. Re-do but only collect interesting deltas.
    print(f"\nRe-iterating to record interesting transpositions ...")
    n_done = 0
    for cls in (0, 1, 2):
        cells = cells_by_class[cls]
        for i in range(len(cells)):
            for j in range(i + 1, len(cells)):
                a, b = cells[i], cells[j]
                row_a, col_a = a // SIZE, a % SIZE
                row_b, col_b = b // SIZE, b % SIZE
                if abs(row_a - row_b) + abs(col_a - col_b) == 1:
                    continue
                pid_a, _ = board[a]
                pid_b, _ = board[b]
                new_a, rot_a = best_rotation_score(board, pieces, a, pid_b)
                new_b, rot_b = best_rotation_score(board, pieces, b, pid_a)
                if new_a < 0 or new_b < 0:
                    continue
                delta = (new_a - cur_local[a]) + (new_b - cur_local[b])
                if delta == 0:
                    neutrals.append((a, b, rot_a, rot_b, new_a, new_b, cur_local[a], cur_local[b]))
                elif delta == -1:
                    near_neutrals.append((a, b, rot_a, rot_b, new_a, new_b, cur_local[a], cur_local[b]))
                n_done += 1

    print(f"\nΔ=0 transpositions ({len(neutrals)}):")
    for (a, b, ra, rb, na, nb, la, lb) in neutrals:
        r1, c1 = a // SIZE, a % SIZE
        r2, c2 = b // SIZE, b % SIZE
        pa = board[a][0]; pb = board[b][0]
        print(f"  swap ({r1:2d},{c1:2d})[p{pa}] <-> ({r2:2d},{c2:2d})[p{pb}]  rot ({ra},{rb})  local {la}+{lb}={la+lb} -> {na}+{nb}={na+nb}")

    print(f"\nΔ=-1 transpositions ({len(near_neutrals)}):")
    for (a, b, ra, rb, na, nb, la, lb) in near_neutrals:
        r1, c1 = a // SIZE, a % SIZE
        r2, c2 = b // SIZE, b % SIZE
        pa = board[a][0]; pb = board[b][0]
        print(f"  swap ({r1:2d},{c1:2d})[p{pa}] <-> ({r2:2d},{c2:2d})[p{pb}]  rot ({ra},{rb})  {la}+{lb}={la+lb} -> {na}+{nb}={na+nb}")

    # Calibration: minimal Δ implies T to accept.
    if pair_deltas:
        min_delta = min(d for d in pair_deltas if d <= 0)
        accept_at_T = lambda T: sum(
            pair_deltas[d] * (1.0 if d >= 0 else __import__('math').exp(d / T))
            for d in pair_deltas
        )
        total = sum(pair_deltas.values())
        for T in (1, 5, 10, 30, 50, 100, 300):
            acc = accept_at_T(T)
            print(f"  Expected acceptance rate at T={T:3d}: {acc / total:.4%}")


if __name__ == "__main__":
    sys.exit(main() or 0)
