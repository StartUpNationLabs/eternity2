#!/usr/bin/env python3
"""
N3a: Pair-rotation sweep on a 457 board.

For every adjacent cell pair (a, b) on the board:
- Jointly try all 16 (rot_a, rot_b) combinations.
- Compute the total matched-edge count for the modified board.
- Track the best (rot_a*, rot_b*) that does NOT decrease the score.

If any pair admits a strict improvement, output it. Else: confirms 457
is fixed under degree-2 rotation moves too.

If no degree-2 improvement: extend to 3-cycles and 4-cycles of rotations
(pick a small set of cells, try all 4^k rotation tuples).
"""

from __future__ import annotations

import json
import sys
import time
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


def board_score(board, pieces):
    s = 0
    for pos in range(N_CELLS):
        cell = board[pos]
        if cell is None:
            continue
        pid, rot = cell
        edges = rotate_edges(pieces[pid], rot)
        row, col = pos // SIZE, pos % SIZE
        # East neighbour (count once)
        if col < SIZE - 1:
            np = board[pos + 1]
            if np:
                e2 = rotate_edges(pieces[np[0]], np[1])
                if edges[1] != BORDER and e2[3] != BORDER and edges[1] == e2[3]:
                    s += 1
        # South neighbour (count once)
        if row < SIZE - 1:
            np = board[pos + SIZE]
            if np:
                e2 = rotate_edges(pieces[np[0]], np[1])
                if edges[2] != BORDER and e2[0] != BORDER and edges[2] == e2[0]:
                    s += 1
    return s


def cell_match_score(board, pieces, pos):
    """Edges matched at the 4 neighbours of `pos`."""
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
            if edges[0] != BORDER and ns != BORDER and edges[0] == ns:
                s += 1
    if col < SIZE - 1:
        np = board[pos + 1]
        if np:
            _, _, _, nw = rotate_edges(pieces[np[0]], np[1])
            if edges[1] != BORDER and nw != BORDER and edges[1] == nw:
                s += 1
    if row < SIZE - 1:
        np = board[pos + SIZE]
        if np:
            nn, _, _, _ = rotate_edges(pieces[np[0]], np[1])
            if edges[2] != BORDER and nn != BORDER and edges[2] == nn:
                s += 1
    if col > 0:
        np = board[pos - 1]
        if np:
            _, ne, _, _ = rotate_edges(pieces[np[0]], np[1])
            if edges[3] != BORDER and ne != BORDER and edges[3] == ne:
                s += 1
    return s


def piece_border_ok(pid, rot, pieces, pos):
    """Whether (pid, rot) at pos has BORDER on outside-board edges and
    non-BORDER on interior edges."""
    row, col = pos // SIZE, pos % SIZE
    edges = rotate_edges(pieces[pid], rot)
    if row == 0:
        if edges[0] != BORDER: return False
    else:
        if edges[0] == BORDER: return False
    if col == SIZE - 1:
        if edges[1] != BORDER: return False
    else:
        if edges[1] == BORDER: return False
    if row == SIZE - 1:
        if edges[2] != BORDER: return False
    else:
        if edges[2] == BORDER: return False
    if col == 0:
        if edges[3] != BORDER: return False
    else:
        if edges[3] == BORDER: return False
    return True


def pair_score_change(board, pieces, a, b, rot_a, rot_b):
    """Effect on TOTAL board score if we set board[a].rotation = rot_a
    and board[b].rotation = rot_b. Returns delta (new - old)."""
    # Cells in scope: a, b, and their 4 neighbours each (some overlap).
    affected = {a, b}
    row_a, col_a = a // SIZE, a % SIZE
    row_b, col_b = b // SIZE, b % SIZE
    for r, c in [(row_a, col_a), (row_b, col_b)]:
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < SIZE and 0 <= nc < SIZE:
                affected.add(nr * SIZE + nc)

    # Original score over affected edges.
    def affected_score(brd):
        s = 0
        seen_edges = set()
        for pos in affected:
            cell = brd[pos]
            if cell is None:
                continue
            pid, rot = cell
            edges = rotate_edges(pieces[pid], rot)
            row, col = pos // SIZE, pos % SIZE
            # East
            if col < SIZE - 1:
                op = pos + 1
                if op in affected:
                    ekey = ("h", pos)  # horizontal edge between pos and pos+1
                    if ekey in seen_edges:
                        pass
                    else:
                        seen_edges.add(ekey)
                        np = brd[op]
                        if np:
                            e2 = rotate_edges(pieces[np[0]], np[1])
                            if edges[1] != BORDER and e2[3] != BORDER and edges[1] == e2[3]:
                                s += 1
                else:
                    # neighbour outside affected: counted from this side
                    np = brd[op]
                    if np:
                        e2 = rotate_edges(pieces[np[0]], np[1])
                        if edges[1] != BORDER and e2[3] != BORDER and edges[1] == e2[3]:
                            s += 1
            elif col == SIZE - 1:
                pass  # no east
            # South
            if row < SIZE - 1:
                op = pos + SIZE
                if op in affected:
                    ekey = ("v", pos)
                    if ekey in seen_edges:
                        pass
                    else:
                        seen_edges.add(ekey)
                        np = brd[op]
                        if np:
                            e2 = rotate_edges(pieces[np[0]], np[1])
                            if edges[2] != BORDER and e2[0] != BORDER and edges[2] == e2[0]:
                                s += 1
                else:
                    np = brd[op]
                    if np:
                        e2 = rotate_edges(pieces[np[0]], np[1])
                        if edges[2] != BORDER and e2[0] != BORDER and edges[2] == e2[0]:
                            s += 1
        return s

    # Don't go down that road — it's error prone. Just recompute board scores.
    s_old = board_score(board, pieces)
    pid_a, _ = board[a]
    pid_b, _ = board[b]
    new_board = list(board)
    new_board[a] = (pid_a, rot_a)
    new_board[b] = (pid_b, rot_b)
    s_new = board_score(new_board, pieces)
    return s_new - s_old


def main():
    pieces = load_pieces()
    board, score = load_board()
    cur = board_score(board, pieces)
    print(f"Loaded board, reported score {score}, recomputed {cur}")
    assert cur == score, "score mismatch"

    # Build list of adjacent cell pairs.
    pairs = []
    for pos in range(N_CELLS):
        row, col = pos // SIZE, pos % SIZE
        if col < SIZE - 1:
            pairs.append((pos, pos + 1))
        if row < SIZE - 1:
            pairs.append((pos, pos + SIZE))
    print(f"Adjacent cell pairs: {len(pairs)}")

    # Pre-filter: only pairs where at least one cell has rotation flexibility
    # (i.e., piece has 4 distinct rotations, not a 1-color rotsym piece).
    # For now: try all pairs.

    print(f"\nPair-rotation sweep starting ({len(pairs)} pairs × 16 rot combos)...")
    t0 = time.time()
    improvers = []
    no_op_alts = []  # pairs where a rotation tuple ties current (no improvement, no loss)
    for pi, (a, b) in enumerate(pairs):
        cur_a = board[a][1]
        cur_b = board[b][1]
        # Filter rot_a candidates: must keep border-piece-class compatibility.
        valid_rots_a = [r for r in range(4) if piece_border_ok(board[a][0], r, pieces, a)]
        valid_rots_b = [r for r in range(4) if piece_border_ok(board[b][0], r, pieces, b)]
        for ra in valid_rots_a:
            for rb in valid_rots_b:
                if ra == cur_a and rb == cur_b:
                    continue
                delta = pair_score_change(board, pieces, a, b, ra, rb)
                if delta > 0:
                    improvers.append((a, b, ra, rb, delta))
                elif delta == 0:
                    no_op_alts.append((a, b, ra, rb))
        if pi % 50 == 49:
            elapsed = time.time() - t0
            print(f"  {pi+1}/{len(pairs)} pairs done in {elapsed:.1f}s; "
                  f"improvers={len(improvers)}, no-ops={len(no_op_alts)}")

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s. Improvers: {len(improvers)}, zero-delta tuples: {len(no_op_alts)}")
    if improvers:
        # Show top.
        improvers.sort(key=lambda x: -x[4])
        for (a, b, ra, rb, d) in improvers[:20]:
            row_a, col_a = a // SIZE, a % SIZE
            row_b, col_b = b // SIZE, b % SIZE
            print(f"  Δ={d:+d}: pair ({row_a},{col_a})↔({row_b},{col_b})  rot ({board[a][1]},{board[b][1]}) -> ({ra},{rb})")
    else:
        print(f"\nNo improving pair-rotation move found. The 457 board is rotation-degree-2-stable.")
        # Just to be thorough, sample some larger rotation perturbations.


if __name__ == "__main__":
    sys.exit(main() or 0)
