#!/usr/bin/env python3
"""SPECTRAL-DESTROY Phase 4: ITERATIVE Hungarian.

Phase 3 Hungarian uses STATIC cost (each destroyed cell ignores other
destroyed cells when computing its piece-rotation matches). This is
suboptimal when destroyed cells are adjacent.

Iterative Hungarian: solve, place pieces, then RE-solve treating the
just-placed cells as fixed. Repeat until fixed-point.

Convergence: monotonically improving on score, terminates in a few iters.
"""

import json
import random
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

REPO = Path("/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2")
SPECTRAL = REPO / "output" / "vol-125" / "spectral"
BORDER = 65535
W = 16


def load_pieces():
    import csv
    pieces = []
    with open(REPO.parent / "data" / "puzzles" / "size_16_official_eternity.csv") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            N, E, S, W_ = (int(row[i].strip(), 2) for i in range(4))
            pieces.append((N, E, S, W_))
    return pieces


def rotate(piece, r):
    N, E, S, W_ = piece
    if r == 0: return (N, E, S, W_)
    if r == 1: return (W_, N, E, S)
    if r == 2: return (S, W_, N, E)
    if r == 3: return (E, S, W_, N)


def edges_at_pos(board, pos, piece_id, rot, pieces):
    """Match count with all PLACED neighbors (ignored cells = not in board)."""
    row, col = pos // W, pos % W
    p_edges = rotate(pieces[piece_id], rot)
    matches = 0
    for d_pos, opp_side, my_side in [
        (-W, 2, 0),  # N neighbor's S edge ↔ my N edge
        (+W, 0, 2),  # S
        (-1, 1, 3),  # W
        (+1, 3, 1),  # E
    ]:
        if d_pos == -W and row == 0: continue
        if d_pos == +W and row == 15: continue
        if d_pos == -1 and col == 0: continue
        if d_pos == +1 and col == 15: continue
        nb_pos = pos + d_pos
        if nb_pos in board:
            nb_pid, nb_rot = board[nb_pos]
            nb_edges = rotate(pieces[nb_pid], nb_rot)
            if nb_edges[opp_side] == p_edges[my_side] and p_edges[my_side] != BORDER:
                matches += 1
    return matches


def score_board(board, pieces):
    matches = 0
    for pos, (pid, rot) in board.items():
        row, col = pos // W, pos % W
        p_edges = rotate(pieces[pid], rot)
        if col < 15 and (pos + 1) in board:
            nb = board[pos + 1]
            ne = rotate(pieces[nb[0]], nb[1])
            if p_edges[1] == ne[3] and p_edges[1] != BORDER: matches += 1
        if row < 15 and (pos + W) in board:
            nb = board[pos + W]
            ne = rotate(pieces[nb[0]], nb[1])
            if p_edges[2] == ne[0] and p_edges[2] != BORDER: matches += 1
    return matches


def iterhung_repair(board0, pieces, destroyed_cells, available_pieces, max_iters=5, rng=None):
    """Iterative Hungarian repair.
    Initial: assign all destroyed cells via Hungarian on partial-board.
    Then: for each iteration, pick a SUBSET of currently-placed-during-repair cells,
    UN-place them, re-Hungarian. This re-examines assignments with knowledge of
    initial assignments of OTHER cells.

    Simpler version: one-shot Hungarian, then for each destroyed cell, try the
    best alternative piece-rotation given the new placement context (local
    fix-up). Repeat to convergence.
    """
    if rng is None:
        rng = np.random.default_rng(0)
    n = len(destroyed_cells)
    if n != len(available_pieces):
        return None

    destroyed_set = set(destroyed_cells)
    partial = {pos: d for pos, d in board0.items() if pos not in destroyed_set}

    # Initial Hungarian (static cost, ignoring destroyed cells' edges between each other).
    def static_hungarian():
        cost = np.zeros((n, n), dtype=np.float64)
        best_rot = np.zeros((n, n), dtype=np.int8)
        for ci, cell in enumerate(destroyed_cells):
            for pi, pid in enumerate(available_pieces):
                bm, br = -1, 0
                for r in range(4):
                    m = edges_at_pos(partial, cell, pid, r, pieces)
                    if m > bm: bm, br = m, r
                cost[ci, pi] = -bm
                best_rot[ci, pi] = br
        ri, ci_ = linear_sum_assignment(cost)
        return {destroyed_cells[r]: (available_pieces[c], int(best_rot[r, c])) for r, c in zip(ri, ci_)}

    placement = static_hungarian()
    current_board = dict(partial)
    current_board.update(placement)

    best_score = score_board(current_board, pieces)

    # Iterate: re-Hungarian with the NEW placements visible to each cell's cost.
    for it in range(max_iters):
        # For each destroyed cell, compute cost given OTHER destroyed-cell placements as fixed.
        # That means: temporarily REMOVE this cell, see what's best for it.
        cost = np.zeros((n, n), dtype=np.float64)
        best_rot = np.zeros((n, n), dtype=np.int8)
        for ci, cell in enumerate(destroyed_cells):
            # Build context: current_board with `cell` removed.
            ctx = {p: d for p, d in current_board.items() if p != cell}
            for pi, pid in enumerate(available_pieces):
                bm, br = -1, 0
                for r in range(4):
                    m = edges_at_pos(ctx, cell, pid, r, pieces)
                    if m > bm: bm, br = m, r
                cost[ci, pi] = -bm
                best_rot[ci, pi] = br
        ri, ci_ = linear_sum_assignment(cost)
        new_placement = {destroyed_cells[r]: (available_pieces[c], int(best_rot[r, c])) for r, c in zip(ri, ci_)}

        new_board = dict(partial)
        new_board.update(new_placement)
        new_score = score_board(new_board, pieces)

        if new_score > best_score:
            best_score = new_score
            current_board = new_board
        elif new_score == best_score:
            # converged
            break
        else:
            # Hungarian can oscillate; take if not worse than -2
            if new_score >= best_score - 1:
                current_board = new_board
            else:
                break

    return current_board


def main():
    record_path = REPO / "database-400-480" / "461_RECORD_461_off110_seed1_8e88ff5a.json"
    spectral_path = SPECTRAL / "piece_spectral.json"
    with open(record_path) as f:
        record = json.load(f)
    placements = record["placement"]
    board0 = {p["pos"]: (p["piece_id"], p["rotation"]) for p in placements}
    with open(spectral_path) as f:
        spec = json.load(f)
    cluster_id = spec["cluster_id_per_piece"]
    pieces = load_pieces()
    s0 = score_board(board0, pieces)
    print(f"Initial score: {s0}", flush=True)

    print(f"\n=== ITERATIVE HUNGARIAN ===", flush=True)
    random.seed(42)
    rng = np.random.default_rng(42)

    best_found = s0
    best_board = dict(board0)

    # Try each cluster.
    for cluster in sorted(set(cluster_id)):
        cells_in_cluster = [pos for pos, (pid, _) in board0.items() if cluster_id[pid] == cluster]
        n = len(cells_in_cluster)
        if n < 5 or n > 60:
            continue
        avail_pieces = [board0[pos][0] for pos in cells_in_cluster]
        rep = iterhung_repair(board0, pieces, cells_in_cluster, avail_pieces,
                              max_iters=10, rng=rng)
        if rep is None: continue
        sc = score_board(rep, pieces)
        marker = " 🎯" if sc > s0 else ""
        print(f"  cluster {cluster} (n={n}): {sc}{marker}", flush=True)
        if sc > best_found:
            best_found = sc
            best_board = rep

    # Also try random-destroy for comparison.
    print(f"\n=== ITER-HUNG on RANDOM destroy ===", flush=True)
    for trial in range(8):
        n = random.choice([20, 25, 30, 35])
        rnd_cells = random.sample(list(board0.keys()), n)
        rnd_avail = [board0[pos][0] for pos in rnd_cells]
        rep = iterhung_repair(board0, pieces, rnd_cells, rnd_avail, max_iters=10, rng=rng)
        if rep is None: continue
        sc = score_board(rep, pieces)
        marker = " 🎯" if sc > s0 else ""
        print(f"  trial {trial} (n={n}): {sc}{marker}", flush=True)
        if sc > best_found:
            best_found = sc
            best_board = rep

    print(f"\n=== SUMMARY ===")
    print(f"  Initial: {s0}")
    print(f"  Best found: {best_found}")
    if best_found > s0:
        print(f"  🎯🎯 BREAKTHROUGH: {s0} → {best_found}!")
        # Save the new record.
        out_path = REPO / "output" / "vol-125" / f"spectral_iterhung_{best_found}.json"
        out_data = {
            "matched": best_found,
            "source": "spectral_destroy_iterhung",
            "placement": [
                {"pos": p, "piece_id": pid, "rotation": rot}
                for p, (pid, rot) in sorted(best_board.items())
            ],
        }
        out_path.write_text(json.dumps(out_data, indent=2))
        print(f"  Saved: {out_path}")
    else:
        print(f"  No breakthrough this run.")


if __name__ == "__main__":
    main()
