#!/usr/bin/env python3
"""
N5 step 2: PATCH ENUMERATION.

Given:
- a 457 board
- the 38 mismatch cells + their 38 placed pieces (the "patch")
- the perimeter of the patch is the fixed boundary (cells outside the
  patch are kept as-is, providing constraints on patch perimeter edges)

Question: enumerate (or upper-bound by branch-and-bound) the best-match
re-assignment of the 38 pieces to the 38 cells (each piece used once,
each cell filled once). This is a 38-piece bag, 38-cell board, with
boundary constraints from the surrounding 218 placed cells.

If the best-match achievable is strictly greater than 23-mismatches-in-patch,
we have a +k move that ALNS cannot see locally but exact patch search can.

Algorithm:
- Build a list of cells in patch.
- For each (cell, piece, rotation), compute the "edge-contribution": number of
  matched edges (against the boundary OR vs another patch cell).
- Backtrack with branch & bound: at each cell, try all (piece, rotation) options
  consistent with already-placed patch cells + boundary, prune by upper bound.

Output: best achievable score in the patch and (optionally) the assignment.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path("/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2")
PATCH = ROOT / "output/n5_patch/patch_data.json"

# Reuse loader.
sys.path.insert(0, str(ROOT / "scripts"))
from n5_patch_analysis import (  # type: ignore  # noqa: E402
    load_pieces,
    load_board,
    rotate_edges,
    BORDER,
    SIZE,
    N_CELLS,
)


def main():
    pieces = load_pieces()
    board, score = load_board()
    patch_data = json.load(open(PATCH))

    # Cells in the patch (the mismatch cells).
    patch_cells = sorted([m["pos"] for m in patch_data["mismatch_cells"]])
    patch_set = set(patch_cells)
    K = len(patch_cells)
    print(f"Patch: {K} cells")

    # The pool of pieces = the K pieces currently at those K cells.
    pool_pids = [board[pos][0] for pos in patch_cells]
    print(f"Pool pieces: {pool_pids[:10]} ...")

    # For each (cell, piece, rotation), what is the edge contribution
    # to the BOUNDARY (sum of matches with cells OUTSIDE the patch).
    # And inside the patch we track via runtime DP.

    def neighbors(pos):
        row, col = pos // SIZE, pos % SIZE
        nbrs = {}
        if row > 0:
            nbrs["N"] = pos - SIZE
        if col < SIZE - 1:
            nbrs["E"] = pos + 1
        if row < SIZE - 1:
            nbrs["S"] = pos + SIZE
        if col > 0:
            nbrs["W"] = pos - 1
        return nbrs

    # For each patch cell, identify which of its 4 neighbours are BOUNDARY
    # (outside patch) vs INTERIOR (inside patch). Compute boundary contribution
    # for (cell, pid, rot).
    boundary_score = {}  # (pos, pid, rot) -> int
    border_match = {}    # (pos, pid, rot) -> True if matches BORDER on outside edges
    for pos in patch_cells:
        row, col = pos // SIZE, pos % SIZE
        # boundary edges: those that face cells OUTSIDE the patch.
        # For each direction, get neighbor pos and whether it's in patch.
        for pid in set(pool_pids):  # try each piece in pool
            for rot in range(4):
                edges = rotate_edges(pieces[pid], rot)  # (N, E, S, W)
                # Check border alignment with grid edge.
                ok = True
                # N
                if row == 0:
                    if edges[0] != BORDER:
                        ok = False
                else:
                    if edges[0] == BORDER:
                        ok = False
                if not ok:
                    continue
                if col == SIZE - 1:
                    if edges[1] != BORDER: ok = False
                else:
                    if edges[1] == BORDER: ok = False
                if not ok:
                    continue
                if row == SIZE - 1:
                    if edges[2] != BORDER: ok = False
                else:
                    if edges[2] == BORDER: ok = False
                if not ok:
                    continue
                if col == 0:
                    if edges[3] != BORDER: ok = False
                else:
                    if edges[3] == BORDER: ok = False
                if not ok:
                    continue

                # Now compute boundary contribution.
                bscore = 0
                # N
                if row > 0 and (pos - SIZE) not in patch_set:
                    np = board[pos - SIZE]
                    if np:
                        _, _, ns, _ = rotate_edges(pieces[np[0]], np[1])
                        if edges[0] != BORDER and ns != BORDER and edges[0] == ns:
                            bscore += 1
                if col < SIZE - 1 and (pos + 1) not in patch_set:
                    np = board[pos + 1]
                    if np:
                        _, _, _, nw = rotate_edges(pieces[np[0]], np[1])
                        if edges[1] != BORDER and nw != BORDER and edges[1] == nw:
                            bscore += 1
                if row < SIZE - 1 and (pos + SIZE) not in patch_set:
                    np = board[pos + SIZE]
                    if np:
                        nn, _, _, _ = rotate_edges(pieces[np[0]], np[1])
                        if edges[2] != BORDER and nn != BORDER and edges[2] == nn:
                            bscore += 1
                if col > 0 and (pos - 1) not in patch_set:
                    np = board[pos - 1]
                    if np:
                        _, ne, _, _ = rotate_edges(pieces[np[0]], np[1])
                        if edges[3] != BORDER and ne != BORDER and edges[3] == ne:
                            bscore += 1
                boundary_score[(pos, pid, rot)] = bscore

    # Now: which interior edges exist in the patch? An "interior patch edge"
    # is between two cells both in patch_set.
    interior_edges = []
    for pos in patch_cells:
        row, col = pos // SIZE, pos % SIZE
        # E neighbor
        if col < SIZE - 1 and (pos + 1) in patch_set:
            interior_edges.append((pos, pos + 1, "horizontal"))
        # S neighbor
        if row < SIZE - 1 and (pos + SIZE) in patch_set:
            interior_edges.append((pos, pos + SIZE, "vertical"))
    print(f"Interior patch edges: {len(interior_edges)}")

    # Compute "current patch score" as a baseline.
    cur_assignment = {pos: board[pos] for pos in patch_cells}

    def patch_score(assignment):
        s = 0
        for pos, pr in assignment.items():
            if pr is None:
                continue
            pid, rot = pr
            edges = rotate_edges(pieces[pid], rot)
            row, col = pos // SIZE, pos % SIZE
            # boundary
            s += boundary_score.get((pos, pid, rot), 0)
            # interior to the EAST (count once)
            if col < SIZE - 1 and (pos + 1) in patch_set:
                op2 = pos + 1
                pr2 = assignment.get(op2)
                if pr2:
                    pid2, rot2 = pr2
                    e2 = rotate_edges(pieces[pid2], rot2)
                    if edges[1] != BORDER and e2[3] != BORDER and edges[1] == e2[3]:
                        s += 1
            if row < SIZE - 1 and (pos + SIZE) in patch_set:
                op2 = pos + SIZE
                pr2 = assignment.get(op2)
                if pr2:
                    pid2, rot2 = pr2
                    e2 = rotate_edges(pieces[pid2], rot2)
                    if edges[2] != BORDER and e2[0] != BORDER and edges[2] == e2[0]:
                        s += 1
        return s

    cur_score = patch_score(cur_assignment)
    print(f"Current patch score (boundary + interior): {cur_score}")

    # Max possible per cell (boundary).
    sum_bscore_max = 0
    for pos in patch_cells:
        max_b = 0
        for pid in set(pool_pids):
            for rot in range(4):
                k = boundary_score.get((pos, pid, rot))
                if k is not None and k > max_b:
                    max_b = k
        sum_bscore_max += max_b
    print(f"Sum-of-max boundary scores (independent upper bound): {sum_bscore_max}")
    print(f"Number of interior edges (also potentially contributing): {len(interior_edges)}")
    print(f"Strict upper bound on patch score: {sum_bscore_max + len(interior_edges)}")

    # Now the enumeration. We're going to do branch-and-bound with cells ordered
    # by MRV (most constrained first). For each cell pick a (pid, rot); each pid
    # used once.

    # Cell ordering — for now, just sorted by # of valid (pid, rot) combinations,
    # ascending (most constrained first).
    cell_options = {}
    for pos in patch_cells:
        opts = []
        for pid in pool_pids:
            for rot in range(4):
                if (pos, pid, rot) in boundary_score:
                    opts.append((pid, rot))
        cell_options[pos] = opts

    cells_ordered = sorted(patch_cells, key=lambda p: len(cell_options[p]))
    print(f"\nCell option counts (sorted ascending):")
    for pos in cells_ordered[:10]:
        row, col = pos // SIZE, pos % SIZE
        print(f"  pos {pos} ({row},{col}): {len(cell_options[pos])} options")

    # Backtracking with pruning.
    pool_set = set(pool_pids)
    assignment: dict = {}
    used_pids: set = set()
    best = [cur_score, dict(cur_assignment)]
    nodes = [0]
    cutoff_time = time.time() + 60.0  # 60s cap

    # Pre-compute interior-edges-touching-remaining-cells per idx for UB.
    # An interior edge is "remaining" if at least one endpoint is unassigned.
    def upper_bound(idx, current_score):
        ub = current_score
        # Max boundary contribution from remaining cells.
        for j in range(idx, len(cells_ordered)):
            pos = cells_ordered[j]
            max_b = 0
            for pid, rot in cell_options[pos]:
                if pid in used_pids:
                    continue
                b = boundary_score[(pos, pid, rot)]
                if b > max_b:
                    max_b = b
            ub += max_b
        # Count interior edges where at least one endpoint is still unplaced.
        # Each such edge could in principle still be matched (UB = +1 per edge).
        unplaced = set(cells_ordered[idx:])
        for a, b, _kind in interior_edges:
            if a in unplaced or b in unplaced:
                ub += 1
        return ub

    def interior_score_at(pos, pid, rot):
        """Score contributed by interior edges where 'pos' is the LATER assignment
        — i.e., neighbour already assigned. Counted once."""
        edges = rotate_edges(pieces[pid], rot)
        row, col = pos // SIZE, pos % SIZE
        s = 0
        # Check each direction; only count if neighbor is in patch AND already assigned.
        # N
        if row > 0 and (pos - SIZE) in patch_set:
            pr2 = assignment.get(pos - SIZE)
            if pr2:
                e2 = rotate_edges(pieces[pr2[0]], pr2[1])
                if edges[0] != BORDER and e2[2] != BORDER and edges[0] == e2[2]:
                    s += 1
        if col < SIZE - 1 and (pos + 1) in patch_set:
            pr2 = assignment.get(pos + 1)
            if pr2:
                e2 = rotate_edges(pieces[pr2[0]], pr2[1])
                if edges[1] != BORDER and e2[3] != BORDER and edges[1] == e2[3]:
                    s += 1
        if row < SIZE - 1 and (pos + SIZE) in patch_set:
            pr2 = assignment.get(pos + SIZE)
            if pr2:
                e2 = rotate_edges(pieces[pr2[0]], pr2[1])
                if edges[2] != BORDER and e2[0] != BORDER and edges[2] == e2[0]:
                    s += 1
        if col > 0 and (pos - 1) in patch_set:
            pr2 = assignment.get(pos - 1)
            if pr2:
                e2 = rotate_edges(pieces[pr2[0]], pr2[1])
                if edges[3] != BORDER and e2[1] != BORDER and edges[3] == e2[1]:
                    s += 1
        return s

    def bt(idx, current_score):
        nodes[0] += 1
        if time.time() > cutoff_time:
            return
        if idx == len(cells_ordered):
            if current_score > best[0]:
                best[0] = current_score
                best[1] = dict(assignment)
                print(f"  ** new best: {best[0]} (nodes={nodes[0]})")
            return
        if upper_bound(idx, current_score) <= best[0]:
            return
        pos = cells_ordered[idx]
        # Sort options by edge contribution descending.
        opts = [
            (pid, rot, boundary_score[(pos, pid, rot)])
            for (pid, rot) in cell_options[pos]
            if pid not in used_pids
        ]
        opts.sort(key=lambda x: -x[2])
        for pid, rot, b in opts:
            inc = b + interior_score_at(pos, pid, rot)
            assignment[pos] = (pid, rot)
            used_pids.add(pid)
            bt(idx + 1, current_score + inc)
            used_pids.discard(pid)
            del assignment[pos]

    print(f"\nStarting branch-and-bound (60s budget) ...")
    t0 = time.time()
    bt(0, 0)
    elapsed = time.time() - t0
    print(f"\nElapsed: {elapsed:.1f}s, nodes: {nodes[0]}")
    print(f"Best patch score found: {best[0]} (started at {cur_score})")
    print(f"Improvement: {best[0] - cur_score:+d}")

    if best[0] > cur_score:
        improved_assignment = best[1]
        print(f"\nCells that changed from current:")
        for pos in sorted(patch_cells):
            cur = cur_assignment[pos]
            nw = improved_assignment.get(pos)
            if nw and nw != cur:
                row, col = pos // SIZE, pos % SIZE
                print(f"  ({row:2d},{col:2d}) pos={pos}: {cur} -> {nw}")
    else:
        print(f"\nNo improvement found in {elapsed:.1f}s. Patch is at LOCAL OPTIMUM under 38-piece-permutation moves.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
