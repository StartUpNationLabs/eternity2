#!/usr/bin/env python3
"""
N4b: 3-cycle and 4-cycle landscape on the 38 mismatch cells.

For each 3-cycle (a,b,c) and 4-cycle (a,b,c,d) of mismatch cells:
- the cyclic permutation moves piece(a) -> b, piece(b) -> c, piece(c) -> a
  (3-cycle) or analogous 4-cycle
- best-rotation per receiving cell, max over 4
- compute Δ = score(new board) - 457

If any cycle has Δ ≥ 0, we have a NON-LOCAL operator that breaks the
operator-lock. Such an op is invisible to ALNS-destroy-then-CP-repair
because CP doesn't restrict to a *permutation* (it can put any piece
in the freed cells).

Tiny search:
- C(38, 3) × 2 (ABC vs ACB) = 14k 3-cycles
- C(38, 4) × 6 perms = 451k 4-cycles
- Each cycle eval ~O(8 cells × 4 rotations) = microseconds
"""

from __future__ import annotations

import itertools
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2")
PATCH = ROOT / "output/n5_patch/patch_data.json"

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


def best_rot_at_pos(board, pieces, pos, pid):
    """Max score across 4 rotations of placing pid at pos, given current
    board. Returns (best_score, best_rot) or (-1, 0) if no valid rotation."""
    best = -1
    best_rot = 0
    for rot in range(4):
        if not piece_border_ok(pid, rot, pieces, pos):
            continue
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
        if s > best:
            best = s
            best_rot = rot
    return best, best_rot


def cell_local(board, pieces, pos):
    cell = board[pos]
    if cell is None: return 0
    return best_rot_at_pos(board, pieces, pos, cell[0])[0]


def evaluate_cycle(board, pieces, cycle, cur_locals_map):
    """Evaluate the cyclic permutation defined by `cycle = [pos0, pos1, ..., posK]`:
    place piece(pos_i) at pos_{(i+1)%K}, best rotation.

    CAREFUL: when cycle cells are adjacent on the grid, the rotation of one
    affects the best rot for its neighbor. So a TRULY accurate evaluation
    requires joint enumeration over rotations. For now, we use a TWO-PASS
    APPROXIMATION:
    1. Pass 1: place all pieces with rotation = best vs current (still-old) neighbours.
    2. Pass 2: re-pick rotations now that all positions have new pieces.

    Returns delta = sum_of_new_local - sum_of_old_local on cycle cells only.
    BIAS: edges between two cycle cells get counted TWICE in this. We'll handle.
    """
    K = len(cycle)
    # Build a new_board with pieces placed but rotation = best_rot_at_pos with
    # respect to the still-original neighbors.
    new_pieces = {}
    for i in range(K):
        src = cycle[i]
        dst = cycle[(i + 1) % K]
        new_pieces[dst] = board[src][0]  # pid only; rot determined below

    # Make a tentative board: for cycle cells, swap in new pieces with best rot
    # against ORIGINAL neighbors (this isn't quite right for cycles that touch each other).
    tentative = list(board)
    new_rots = {}
    for dst, new_pid in new_pieces.items():
        sc, rot = best_rot_at_pos(board, pieces, dst, new_pid)  # against ORIGINAL board
        if sc < 0:
            return None, None  # invalid placement (border-class mismatch)
        new_rots[dst] = rot
        tentative[dst] = (new_pid, rot)

    # Second pass: re-pick rotations, now against the tentative board.
    for dst, new_pid in new_pieces.items():
        sc, rot = best_rot_at_pos(tentative, pieces, dst, new_pid)
        if sc < 0:
            return None, None
        new_rots[dst] = rot
        tentative[dst] = (new_pid, rot)

    # Now compute exact score over the cycle's affected cells + their original neighbours.
    # Affected cells = cycle cells.
    # Edges to count: edges incident to any cycle cell.
    # Score delta = score(tentative, those edges) - score(board, those edges).
    affected = set(cycle)
    seen_edges = set()
    def affected_score(brd):
        s = 0
        for pos in affected:
            cell = brd[pos]
            if cell is None: continue
            pid, rot = cell
            edges = rotate_edges(pieces[pid], rot)
            row, col = pos // SIZE, pos % SIZE
            # East
            if col < SIZE - 1:
                op = pos + 1
                ekey = ("h", pos)
                if ekey in seen_edges: continue
                seen_edges.add(ekey)
                np = brd[op]
                if np:
                    e2 = rotate_edges(pieces[np[0]], np[1])
                    if edges[1] != BORDER and e2[3] != BORDER and edges[1] == e2[3]: s += 1
            # South
            if row < SIZE - 1:
                op = pos + SIZE
                ekey = ("v", pos)
                if ekey in seen_edges: continue
                seen_edges.add(ekey)
                np = brd[op]
                if np:
                    e2 = rotate_edges(pieces[np[0]], np[1])
                    if edges[2] != BORDER and e2[0] != BORDER and edges[2] == e2[0]: s += 1
        # Also count edges where one end is in `affected` but the W or N neighbor is OUT of affected.
        for pos in affected:
            row, col = pos // SIZE, pos % SIZE
            # W: edge between (pos-1) and pos. If pos-1 not in affected.
            if col > 0 and (pos - 1) not in affected:
                ekey = ("h", pos - 1)
                if ekey in seen_edges: continue
                seen_edges.add(ekey)
                cell = brd[pos]
                np = brd[pos - 1]
                if cell and np:
                    edges = rotate_edges(pieces[cell[0]], cell[1])
                    e2 = rotate_edges(pieces[np[0]], np[1])
                    if edges[3] != BORDER and e2[1] != BORDER and edges[3] == e2[1]: s += 1
            if row > 0 and (pos - SIZE) not in affected:
                ekey = ("v", pos - SIZE)
                if ekey in seen_edges: continue
                seen_edges.add(ekey)
                cell = brd[pos]
                np = brd[pos - SIZE]
                if cell and np:
                    edges = rotate_edges(pieces[cell[0]], cell[1])
                    e2 = rotate_edges(pieces[np[0]], np[1])
                    if edges[0] != BORDER and e2[2] != BORDER and edges[0] == e2[2]: s += 1
        return s

    s_new = affected_score(tentative)
    seen_edges.clear()
    s_old = affected_score(board)
    return s_new - s_old, new_rots


def main():
    pieces = load_pieces()
    board, score = load_board()
    patch_data = json.load(open(PATCH))
    seed_cells = [m["pos"] for m in patch_data["mismatch_cells"]]
    print(f"Board score {score}, mismatch cells {len(seed_cells)}")

    # Group by border class to ensure transposability.
    def bc(pid): return sum(1 for c in pieces[pid] if c == BORDER)
    by_class = defaultdict(list)
    for pos in seed_cells:
        by_class[bc(board[pos][0])].append(pos)
    print(f"By border class within mismatch:")
    for k, v in by_class.items():
        print(f"  class {k}: {len(v)} cells")

    # Compute local scores once (current).
    cur_locals = {pos: cell_local(board, pieces, pos) for pos in seed_cells}

    # 3-cycle scan.
    t0 = time.time()
    deltas_3 = Counter()
    improvers_3 = []
    for cls, cells in by_class.items():
        for trio in itertools.combinations(cells, 3):
            for perm in itertools.permutations(trio):
                # cyclic perm with first element fixed: only 2 distinct 3-cycles per trio.
                if perm[0] != trio[0]: continue
                d, rots = evaluate_cycle(board, pieces, list(perm), cur_locals)
                if d is None: continue
                deltas_3[d] += 1
                if d >= 0:
                    improvers_3.append((perm, d, rots))
    elapsed = time.time() - t0
    print(f"\n3-cycle scan: {sum(deltas_3.values())} cycles in {elapsed:.1f}s")
    print(f"Δ-distribution:")
    for d in sorted(deltas_3):
        print(f"  Δ={d:+3d}: {deltas_3[d]}")

    if improvers_3:
        improvers_3.sort(key=lambda x: -x[1])
        print(f"\n★ 3-cycle improvers (Δ ≥ 0): {len(improvers_3)}")
        for (cycle, d, rots) in improvers_3[:30]:
            poses = [f"({p//SIZE},{p%SIZE})" for p in cycle]
            pids = [board[p][0] for p in cycle]
            print(f"  Δ={d:+d}: {poses[0]}->{poses[1]}->{poses[2]}->{poses[0]}  pieces {pids}  rots {rots}")

    # 4-cycle scan (restricted to interior class only for speed).
    t0 = time.time()
    deltas_4 = Counter()
    improvers_4 = []
    cls = 0  # interior
    cells = by_class[cls]
    print(f"\n4-cycle scan: C({len(cells)},4) × 6 = {len(list(itertools.combinations(cells, 4))) * 6} cycles ...")
    for quad in itertools.combinations(cells, 4):
        # Distinct 4-cycles with first fixed: 3! / 2 = 3 (forward and reverse equivalent? No, they are distinct moves).
        for perm in itertools.permutations(quad):
            if perm[0] != quad[0]: continue
            d, rots = evaluate_cycle(board, pieces, list(perm), cur_locals)
            if d is None: continue
            deltas_4[d] += 1
            if d >= 0:
                improvers_4.append((perm, d, rots))
    elapsed = time.time() - t0
    print(f"4-cycle scan: {sum(deltas_4.values())} cycles in {elapsed:.1f}s")
    print(f"Δ-distribution:")
    for d in sorted(deltas_4):
        print(f"  Δ={d:+3d}: {deltas_4[d]}")
    if improvers_4:
        improvers_4.sort(key=lambda x: -x[1])
        print(f"\n★★ 4-cycle improvers (Δ ≥ 0): {len(improvers_4)}")
        for (cycle, d, rots) in improvers_4[:30]:
            poses = [f"({p//SIZE},{p%SIZE})" for p in cycle]
            pids = [board[p][0] for p in cycle]
            print(f"  Δ={d:+d}: {poses}  pieces {pids}")


if __name__ == "__main__":
    sys.exit(main() or 0)
