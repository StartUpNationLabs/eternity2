#!/usr/bin/env python3
"""SPECTRAL-DESTROY prototype — phase 2 of SPECTRAL-SWAP invention.

Given:
  - A board (e.g., a 461 record)
  - The 256 pieces' spectral cluster IDs (from spectral_piece_similarity.py)

Operator:
  1. Pick a spectral cluster C.
  2. Find all cells whose piece is in cluster C.
  3. UN-PLACE those cells (remove their pieces from the board).
  4. Re-solve: greedy fill of the unplaced cells, choosing for each
     cell the piece+rotation that maximizes local edge matches with
     already-placed neighbors.
  5. Measure new score.

Compare against:
  - Random-cell-destroy (pick same number of cells randomly), refill same way.

If SPECTRAL beats RANDOM consistently, the operator has signal.
"""

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO = Path("/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2")
SPECTRAL = REPO / "output" / "vol-125" / "spectral"
BORDER = 65535
W = 16  # board width


def load_pieces() -> list[tuple]:
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
    """Return matched-edge count contribution from cell pos."""
    row, col = pos // W, pos % W
    p_edges = rotate(pieces[piece_id], rot)  # (N, E, S, W)
    matches = 0
    # N neighbor
    if row > 0:
        np_pos = pos - W
        np_data = board.get(np_pos)
        if np_data:
            np_id, np_rot = np_data
            np_edges = rotate(pieces[np_id], np_rot)
            # S edge of N-neighbor must match N edge of this
            if np_edges[2] == p_edges[0] and p_edges[0] != BORDER:
                matches += 1
    else:
        # top border
        if p_edges[0] == BORDER: matches += 0  # border-border doesn't count as matched edge
    # S neighbor
    if row < 15:
        sp_pos = pos + W
        sp_data = board.get(sp_pos)
        if sp_data:
            sp_id, sp_rot = sp_data
            sp_edges = rotate(pieces[sp_id], sp_rot)
            if sp_edges[0] == p_edges[2] and p_edges[2] != BORDER:
                matches += 1
    # W neighbor
    if col > 0:
        wp_pos = pos - 1
        wp_data = board.get(wp_pos)
        if wp_data:
            wp_id, wp_rot = wp_data
            wp_edges = rotate(pieces[wp_id], wp_rot)
            if wp_edges[1] == p_edges[3] and p_edges[3] != BORDER:
                matches += 1
    # E neighbor
    if col < 15:
        ep_pos = pos + 1
        ep_data = board.get(ep_pos)
        if ep_data:
            ep_id, ep_rot = ep_data
            ep_edges = rotate(pieces[ep_id], ep_rot)
            if ep_edges[3] == p_edges[1] and p_edges[1] != BORDER:
                matches += 1
    return matches


def score_board(board, pieces):
    """Total matched interior+border edges. Each pair counted once."""
    seen_edges = set()
    matches = 0
    for pos, (pid, rot) in board.items():
        row, col = pos // W, pos % W
        p_edges = rotate(pieces[pid], rot)
        # Right edge with E neighbor
        if col < 15:
            n_data = board.get(pos + 1)
            if n_data:
                n_id, n_rot = n_data
                n_edges = rotate(pieces[n_id], n_rot)
                if p_edges[1] == n_edges[3] and p_edges[1] != BORDER:
                    matches += 1
        # Bottom edge with S neighbor
        if row < 15:
            n_data = board.get(pos + W)
            if n_data:
                n_id, n_rot = n_data
                n_edges = rotate(pieces[n_id], n_rot)
                if p_edges[2] == n_edges[0] and p_edges[2] != BORDER:
                    matches += 1
    return matches


def repair_greedy(board_partial, pieces, free_positions, available_pieces):
    """Greedy fill of free_positions with available_pieces.
    For each position (in order), pick the piece+rotation maximizing matched edges."""
    board = dict(board_partial)
    avail = set(available_pieces)
    for pos in free_positions:
        best_pid = None
        best_rot = 0
        best_score = -1
        for pid in list(avail):
            for rot in range(4):
                m = edges_at_pos(board, pos, pid, rot, pieces)
                if m > best_score:
                    best_score = m
                    best_pid = pid
                    best_rot = rot
        if best_pid is None:
            # No piece available — abort (shouldn't happen if avail size = free)
            return None
        board[pos] = (best_pid, best_rot)
        avail.discard(best_pid)
    return board


def main():
    record_path = REPO / "database-400-480" / "461_RECORD_461_off110_seed1_8e88ff5a.json"
    spectral_path = SPECTRAL / "piece_spectral.json"

    print(f"Loading record from {record_path.name}...", flush=True)
    with open(record_path) as f:
        record = json.load(f)
    placements = record["placement"]
    board0 = {p["pos"]: (p["piece_id"], p["rotation"]) for p in placements}
    print(f"  initial score: {record['matched']}", flush=True)

    print(f"Loading spectral data...", flush=True)
    with open(spectral_path) as f:
        spec = json.load(f)
    cluster_id = spec["cluster_id_per_piece"]  # 256 ints
    cluster_counts = spec["cluster_counts"]
    print(f"  cluster sizes: {dict(cluster_counts)}", flush=True)

    pieces = load_pieces()
    s0 = score_board(board0, pieces)
    print(f"  recomputed score: {s0}", flush=True)
    if s0 != record["matched"]:
        print(f"  WARN: rescored ({s0}) != reported ({record['matched']})", flush=True)

    # For each cluster, run spectral-destroy and compare with random-destroy.
    print(f"\n=== SPECTRAL-DESTROY trials ===", flush=True)
    print(f"For each cluster C: pick all cells whose piece is in C, destroy, greedy-repair", flush=True)

    results_spectral = []
    results_random = []

    random.seed(42)

    for cluster in sorted(set(cluster_id)):
        cells_in_cluster = [pos for pos, (pid, _) in board0.items() if cluster_id[pid] == cluster]
        n = len(cells_in_cluster)
        if n < 5 or n > 60:
            continue  # skip too-small/too-large clusters
        # Free positions and available pieces.
        free_positions = list(cells_in_cluster)
        random.shuffle(free_positions)
        available_pieces = [board0[pos][0] for pos in free_positions]

        # Build partial board (remove cluster cells).
        partial = {pos: data for pos, data in board0.items() if pos not in cells_in_cluster}

        # SPECTRAL repair (free_positions in original cluster order).
        repaired_sp = repair_greedy(partial, pieces, free_positions, available_pieces)
        if repaired_sp:
            sp_score = score_board(repaired_sp, pieces)
        else:
            sp_score = None

        # RANDOM-DESTROY trial: pick n cells RANDOMLY across all 256, destroy same way.
        random_cells = random.sample(list(board0.keys()), n)
        random_avail = [board0[pos][0] for pos in random_cells]
        partial_rnd = {pos: data for pos, data in board0.items() if pos not in random_cells}
        repaired_rnd = repair_greedy(partial_rnd, pieces, random_cells, random_avail)
        rnd_score = score_board(repaired_rnd, pieces) if repaired_rnd else None

        print(f"  cluster {cluster}: |cells|={n:3d} | spectral={sp_score}  random={rnd_score}", flush=True)
        if sp_score is not None: results_spectral.append((cluster, n, sp_score))
        if rnd_score is not None: results_random.append((cluster, n, rnd_score))

    # Summary.
    print(f"\n=== SUMMARY ===", flush=True)
    if results_spectral and results_random:
        sp_avg = sum(r[2] for r in results_spectral) / len(results_spectral)
        rnd_avg = sum(r[2] for r in results_random) / len(results_random)
        sp_best = max(r[2] for r in results_spectral)
        rnd_best = max(r[2] for r in results_random)
        print(f"  Spectral: avg={sp_avg:.1f}, best={sp_best}", flush=True)
        print(f"  Random:   avg={rnd_avg:.1f}, best={rnd_best}", flush=True)
        print(f"  Improvement (avg): {sp_avg - rnd_avg:+.1f}", flush=True)
        print(f"  Initial board: {s0}", flush=True)
        if sp_best > s0:
            print(f"  🎯 SPECTRAL FOUND BETTER: {sp_best} > {s0}!", flush=True)
        if rnd_best > s0:
            print(f"  RANDOM also found better: {rnd_best} > {s0}", flush=True)


if __name__ == "__main__":
    main()
