#!/usr/bin/env python3
"""SPECTRAL-DESTROY Phase 3: Hungarian-assignment repair.

Same spectral-destroy as Phase 2, but instead of greedy per-cell repair,
solve a bipartite assignment problem:
  - LHS: destroyed cells
  - RHS: (piece, rotation) options for each cell
  - cost: -(matched edges with placed neighbors + matched edges between
    destroyed cells if we knew their assignment — but we don't, so just
    cells × neighbors)

For each cell × each (piece, rot) in available set, compute "static" cost.
Solve Hungarian, get one piece+rot per cell.

The Hungarian assignment is OPTIMAL on the static-cost objective. It's
not optimal on the FULL objective (which has cell-cell interactions) but
should beat greedy.
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


def edges_at_pos(board, pos, piece_id, rot, pieces, ignore_cells=None):
    """Match count of placed-neighbors. ignore_cells = set of positions to skip."""
    row, col = pos // W, pos % W
    p_edges = rotate(pieces[piece_id], rot)
    matches = 0
    if ignore_cells is None:
        ignore_cells = set()
    # N
    if row > 0:
        nb = pos - W
        if nb not in ignore_cells and nb in board:
            ne = rotate(pieces[board[nb][0]], board[nb][1])
            if ne[2] == p_edges[0] and p_edges[0] != BORDER: matches += 1
    # S
    if row < 15:
        nb = pos + W
        if nb not in ignore_cells and nb in board:
            ne = rotate(pieces[board[nb][0]], board[nb][1])
            if ne[0] == p_edges[2] and p_edges[2] != BORDER: matches += 1
    # W
    if col > 0:
        nb = pos - 1
        if nb not in ignore_cells and nb in board:
            ne = rotate(pieces[board[nb][0]], board[nb][1])
            if ne[1] == p_edges[3] and p_edges[3] != BORDER: matches += 1
    # E
    if col < 15:
        nb = pos + 1
        if nb not in ignore_cells and nb in board:
            ne = rotate(pieces[board[nb][0]], board[nb][1])
            if ne[3] == p_edges[1] and p_edges[1] != BORDER: matches += 1
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


def hungarian_repair(board_partial, pieces, destroyed_cells, available_pieces):
    """Solve bipartite assignment of destroyed cells × available pieces.

    Each cell × piece has 4 rotation options; pick max-edge rotation per (cell, piece).
    Then solve Hungarian on the n×n cost matrix.

    Returns repaired board, or None if infeasible.
    """
    n = len(destroyed_cells)
    if n != len(available_pieces):
        return None
    destroyed_set = set(destroyed_cells)

    # Build cost matrix C[cell_idx, piece_idx] = -max_rot(matched_edges)
    # Also remember the best rotation per (cell, piece).
    cost = np.zeros((n, n), dtype=np.float64)
    best_rot = np.zeros((n, n), dtype=np.int8)
    for ci, cell in enumerate(destroyed_cells):
        for pi, piece_id in enumerate(available_pieces):
            best_m = -1
            best_r = 0
            for r in range(4):
                m = edges_at_pos(board_partial, cell, piece_id, r, pieces,
                                 ignore_cells=destroyed_set)
                if m > best_m:
                    best_m = m
                    best_r = r
            cost[ci, pi] = -best_m  # negate for minimization
            best_rot[ci, pi] = best_r

    # Solve Hungarian.
    row_ind, col_ind = linear_sum_assignment(cost)
    repaired = dict(board_partial)
    for ci, pi in zip(row_ind, col_ind):
        cell = destroyed_cells[ci]
        piece = available_pieces[pi]
        rot = int(best_rot[ci, pi])
        repaired[cell] = (piece, rot)
    return repaired


def repair_greedy(board_partial, pieces, free_positions, available_pieces):
    """Same as before for baseline."""
    board = dict(board_partial)
    avail = set(available_pieces)
    for pos in free_positions:
        best_pid = None; best_rot = 0; best_score = -1
        for pid in list(avail):
            for rot in range(4):
                m = edges_at_pos(board, pos, pid, rot, pieces)
                if m > best_score:
                    best_score = m; best_pid = pid; best_rot = rot
        if best_pid is None:
            return None
        board[pos] = (best_pid, best_rot)
        avail.discard(best_pid)
    return board


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

    print(f"\n=== HUNGARIAN-REPAIR SPECTRAL-DESTROY ===", flush=True)
    print(f"For each cluster, destroy + hungarian-repair vs greedy-repair", flush=True)

    random.seed(42)
    rng = np.random.default_rng(42)

    sp_hung = []
    sp_grd = []
    rnd_hung = []
    rnd_grd = []
    best_found = s0

    for cluster in sorted(set(cluster_id)):
        cells_in_cluster = [pos for pos, (pid, _) in board0.items() if cluster_id[pid] == cluster]
        n = len(cells_in_cluster)
        if n < 5 or n > 60:
            continue
        avail_pieces = [board0[pos][0] for pos in cells_in_cluster]
        partial = {pos: d for pos, d in board0.items() if pos not in set(cells_in_cluster)}

        # Spectral-destroy + Hungarian.
        rep_h = hungarian_repair(partial, pieces, cells_in_cluster, avail_pieces)
        sh = score_board(rep_h, pieces) if rep_h else None

        # Spectral-destroy + greedy.
        free_pos_shuffled = list(cells_in_cluster); random.shuffle(free_pos_shuffled)
        avail_shuffled = [board0[pos][0] for pos in free_pos_shuffled]
        rep_g = repair_greedy(partial, pieces, free_pos_shuffled, avail_shuffled)
        sg = score_board(rep_g, pieces) if rep_g else None

        # Random-destroy + Hungarian (same n cells, picked randomly).
        rnd_cells = random.sample(list(board0.keys()), n)
        rnd_avail = [board0[pos][0] for pos in rnd_cells]
        rnd_partial = {pos: d for pos, d in board0.items() if pos not in set(rnd_cells)}
        rep_rh = hungarian_repair(rnd_partial, pieces, rnd_cells, rnd_avail)
        rh = score_board(rep_rh, pieces) if rep_rh else None

        # Random-destroy + greedy.
        rep_rg = repair_greedy(rnd_partial, pieces, rnd_cells, rnd_avail)
        rg = score_board(rep_rg, pieces) if rep_rg else None

        print(f"  cluster {cluster}: n={n:3d}  |  SP_Hung={sh}  SP_Greedy={sg}  |  RND_Hung={rh}  RND_Greedy={rg}", flush=True)

        for s, lst in [(sh, sp_hung), (sg, sp_grd), (rh, rnd_hung), (rg, rnd_grd)]:
            if s is not None: lst.append(s)
        for s in (sh, sg, rh, rg):
            if s is not None and s > best_found:
                best_found = s

    print(f"\n=== SUMMARY ===")
    print(f"  Initial: {s0}")
    if sp_hung: print(f"  Spectral + Hungarian: avg={sum(sp_hung)/len(sp_hung):.1f} best={max(sp_hung)}")
    if sp_grd:  print(f"  Spectral + Greedy:    avg={sum(sp_grd)/len(sp_grd):.1f} best={max(sp_grd)}")
    if rnd_hung: print(f"  Random + Hungarian:   avg={sum(rnd_hung)/len(rnd_hung):.1f} best={max(rnd_hung)}")
    if rnd_grd:  print(f"  Random + Greedy:      avg={sum(rnd_grd)/len(rnd_grd):.1f} best={max(rnd_grd)}")
    print(f"\n  Best score found across all trials: {best_found}")
    if best_found > s0:
        print(f"  🎯🎯 BREAKTHROUGH: beat initial {s0} → {best_found}!")


if __name__ == "__main__":
    main()
