#!/usr/bin/env python3
"""
N5b/d: Expand the 38-cell mismatch patch by adding the HALO (1-hop or
k-hop neighbours) and re-run BB enumeration. This tests whether the
patch is boundary-locked vs. genuinely solvable with more pieces.

Approach:
- Take the 38 mismatch cells.
- Add cells within radius r (4-adjacency, in lattice distance) to the
  patch. The pool then includes their currently-placed pieces too.
- Re-run BB with timeout 120s.
- Report whether expanded patch can improve the matched-edge count.

Run for r=1, 2, 3 to characterise the "minimum radius needed for
escape." If r=1 is enough, ComponentPlusHaloDestroy(k≈60) should be
able to find the move. If r=3 (≈170 cells), we need almost full board.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path("/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2")
PATCH = ROOT / "output/n5_patch/patch_data.json"

sys.path.insert(0, str(ROOT / "scripts"))
from n5_patch_analysis import (  # type: ignore  # noqa: E402
    load_pieces,
    load_board,
    rotate_edges,
    BORDER,
    SIZE,
    N_CELLS,
)


def expand_patch(seed_cells, radius):
    """Expand seed_cells set by `radius` hops on 4-adjacency."""
    cur = set(seed_cells)
    for _ in range(radius):
        new = set(cur)
        for pos in cur:
            row, col = pos // SIZE, pos % SIZE
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = row + dr, col + dc
                if 0 <= nr < SIZE and 0 <= nc < SIZE:
                    new.add(nr * SIZE + nc)
        cur = new
    return sorted(cur)


def run_bb(patch_cells, pool_pids, board, pieces, time_budget_s=60.0):
    """Branch-and-bound on a given patch with given pool. Returns
    (best_score, current_score, nodes_explored, time_used, ub_initial)."""

    patch_set = set(patch_cells)

    # Validate piece pool: must equal the cells currently in patch (one-piece-per-cell)
    # and the bag we're allowed to permute.
    assert len(pool_pids) == len(patch_cells), f"pool {len(pool_pids)} != patch {len(patch_cells)}"

    # Boundary score per (pos, pid, rot).
    boundary_score = {}
    for pos in patch_cells:
        row, col = pos // SIZE, pos % SIZE
        for pid in set(pool_pids):
            for rot in range(4):
                edges = rotate_edges(pieces[pid], rot)
                ok = True
                # border alignment with grid edges
                if row == 0:
                    if edges[0] != BORDER: ok = False
                else:
                    if edges[0] == BORDER: ok = False
                if col == SIZE - 1:
                    if edges[1] != BORDER: ok = False
                else:
                    if edges[1] == BORDER: ok = False
                if row == SIZE - 1:
                    if edges[2] != BORDER: ok = False
                else:
                    if edges[2] == BORDER: ok = False
                if col == 0:
                    if edges[3] != BORDER: ok = False
                else:
                    if edges[3] == BORDER: ok = False
                if not ok:
                    continue

                bscore = 0
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

    interior_edges = []
    for pos in patch_cells:
        row, col = pos // SIZE, pos % SIZE
        if col < SIZE - 1 and (pos + 1) in patch_set:
            interior_edges.append((pos, pos + 1))
        if row < SIZE - 1 and (pos + SIZE) in patch_set:
            interior_edges.append((pos, pos + SIZE))

    cur_assignment = {pos: board[pos] for pos in patch_cells}

    def score_assignment(assignment):
        s = 0
        for pos, pr in assignment.items():
            if pr is None:
                continue
            pid, rot = pr
            edges = rotate_edges(pieces[pid], rot)
            row, col = pos // SIZE, pos % SIZE
            s += boundary_score.get((pos, pid, rot), 0)
            if col < SIZE - 1 and (pos + 1) in patch_set:
                pr2 = assignment.get(pos + 1)
                if pr2:
                    pid2, rot2 = pr2
                    e2 = rotate_edges(pieces[pid2], rot2)
                    if edges[1] != BORDER and e2[3] != BORDER and edges[1] == e2[3]:
                        s += 1
            if row < SIZE - 1 and (pos + SIZE) in patch_set:
                pr2 = assignment.get(pos + SIZE)
                if pr2:
                    pid2, rot2 = pr2
                    e2 = rotate_edges(pieces[pid2], rot2)
                    if edges[2] != BORDER and e2[0] != BORDER and edges[2] == e2[0]:
                        s += 1
        return s

    cur_score = score_assignment(cur_assignment)

    # Cell options.
    cell_options = {}
    for pos in patch_cells:
        opts = []
        for pid in pool_pids:
            for rot in range(4):
                if (pos, pid, rot) in boundary_score:
                    opts.append((pid, rot))
        cell_options[pos] = opts

    # Order cells by option count ascending.
    cells_ordered = sorted(patch_cells, key=lambda p: len(cell_options[p]))

    assignment = {}
    used = set()
    best = [cur_score, dict(cur_assignment)]
    nodes = [0]
    cutoff = time.time() + time_budget_s

    def interior_at(pos, pid, rot):
        edges = rotate_edges(pieces[pid], rot)
        row, col = pos // SIZE, pos % SIZE
        s = 0
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

    def upper_bound(idx, current_score):
        ub = current_score
        for j in range(idx, len(cells_ordered)):
            pos = cells_ordered[j]
            max_b = 0
            for pid, rot in cell_options[pos]:
                if pid in used:
                    continue
                b = boundary_score[(pos, pid, rot)]
                if b > max_b:
                    max_b = b
            ub += max_b
        unplaced = set(cells_ordered[idx:])
        for a, b in interior_edges:
            if a in unplaced or b in unplaced:
                ub += 1
        return ub

    def bt(idx, current_score):
        nodes[0] += 1
        if time.time() > cutoff:
            return
        if idx == len(cells_ordered):
            if current_score > best[0]:
                best[0] = current_score
                best[1] = dict(assignment)
                # silent — no print in inner loop
            return
        if upper_bound(idx, current_score) <= best[0]:
            return
        pos = cells_ordered[idx]
        opts = [
            (pid, rot, boundary_score[(pos, pid, rot)])
            for (pid, rot) in cell_options[pos]
            if pid not in used
        ]
        opts.sort(key=lambda x: -x[2])
        for pid, rot, b in opts:
            inc = b + interior_at(pos, pid, rot)
            assignment[pos] = (pid, rot)
            used.add(pid)
            bt(idx + 1, current_score + inc)
            used.discard(pid)
            del assignment[pos]

    t0 = time.time()
    bt(0, 0)
    elapsed = time.time() - t0

    initial_ub = upper_bound(0, 0)
    return best[0], cur_score, nodes[0], elapsed, initial_ub


def main():
    pieces = load_pieces()
    board, score = load_board()
    patch_data = json.load(open(PATCH))
    seed_cells = [m["pos"] for m in patch_data["mismatch_cells"]]

    print(f"Board score: {score}/480 (mismatch edges: {480 - score})")
    print(f"Seed (mismatch) cells: {len(seed_cells)}")

    for radius in (0, 1):
        expanded = expand_patch(seed_cells, radius)
        pool_pids = [board[pos][0] for pos in expanded]
        print(f"\n=== Radius {radius}: patch size {len(expanded)} ===", flush=True)
        budget = 30.0 if len(expanded) <= 40 else 90.0
        best, cur, nodes, elapsed, ub = run_bb(
            expanded, pool_pids, board, pieces, time_budget_s=budget
        )
        print(f"  Initial UB: {ub}")
        print(f"  Current patch score: {cur}")
        print(f"  Best found ({elapsed:.1f}s, {nodes} nodes): {best}")
        print(f"  Improvement: {best - cur:+d}")
        if best > cur:
            print(f"  → +{best-cur} matched edges achievable in expanded patch!")


if __name__ == "__main__":
    sys.exit(main() or 0)
