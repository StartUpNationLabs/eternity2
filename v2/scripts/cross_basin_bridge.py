#!/usr/bin/env python3
"""CROSS-BASIN HUNGARIAN-BRIDGE — Phase 5 of SPECTRAL-SWAP family.

Inspired by vol-65 σ-cycle findings: between distinct basins of similar
score, there exist σ-permutations that decompose into cycles of various
lengths. Naively applying full σ destroys score; cycle-by-cycle application
preserves score within basin but doesn't escape.

NEW idea: hybridize two basins by partially applying their σ, then run
iter-Hungarian repair on the hybrid. The repair re-optimizes the disagreed
cells, possibly finding INTERMEDIATE local optima with score > max(A, B).

Pipeline:
1. Load basin A (e.g., 461 record) and basin B (e.g., 460 record from
   different offset)
2. Compute differing cells D = {pos : A[pos] != B[pos]}
3. For each subset size k ∈ {0.25|D|, 0.5|D|, 0.75|D|}:
   - Pick random k cells from D
   - Replace A's pieces at those cells with B's pieces
   - Run iter-Hungarian on all cells in D as "destroyed"
4. Score the result. Report best across trials.
"""

import json
import random
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

REPO = Path("/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2")
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
    row, col = pos // W, pos % W
    p_edges = rotate(pieces[piece_id], rot)
    matches = 0
    for d_pos, opp_side, my_side in [(-W, 2, 0), (+W, 0, 2), (-1, 1, 3), (+1, 3, 1)]:
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
            nb = board[pos + 1]; ne = rotate(pieces[nb[0]], nb[1])
            if p_edges[1] == ne[3] and p_edges[1] != BORDER: matches += 1
        if row < 15 and (pos + W) in board:
            nb = board[pos + W]; ne = rotate(pieces[nb[0]], nb[1])
            if p_edges[2] == ne[0] and p_edges[2] != BORDER: matches += 1
    return matches


def load_board(path):
    with open(path) as f:
        d = json.load(f)
    return {p["pos"]: (p["piece_id"], p["rotation"]) for p in d["placement"]}, d.get("matched", 0)


def iterhung_repair(board0, pieces, destroyed_cells, available_pieces, max_iters=8):
    n = len(destroyed_cells)
    if n != len(available_pieces): return None
    destroyed_set = set(destroyed_cells)
    partial = {pos: d for pos, d in board0.items() if pos not in destroyed_set}

    def step(current_board):
        cost = np.zeros((n, n))
        best_rot = np.zeros((n, n), dtype=np.int8)
        for ci, cell in enumerate(destroyed_cells):
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
        result = dict(partial)
        result.update(new_placement)
        return result

    current = step(partial)
    best_s = score_board(current, pieces)
    for _ in range(max_iters):
        nxt = step(current)
        ns = score_board(nxt, pieces)
        if ns > best_s:
            best_s = ns; current = nxt
        elif ns == best_s:
            break
        else:
            break
    return current


def hybridize(boardA, boardB, k_cells_from_B, rng):
    """Build hybrid: start with boardA, replace k_cells_from_B with boardB's pieces.
    Returns (hybrid_board, set_of_replaced_cells).

    Tricky: pieces in boardB at replaced positions may collide with pieces in
    boardA at non-replaced positions. We need to ENSURE the final hybrid uses
    each piece at most once.

    Approach: pick replaced cells. For each, take boardB's piece at that cell.
    Then, find which boardA cells use those pieces (collision sources), and
    replace those with boardA's pieces at the originally-replaced cells.
    This is the σ-cycle composition.
    """
    # Differing cells D
    diff = [pos for pos in range(256) if boardA.get(pos) != boardB.get(pos)]
    if not diff: return dict(boardA), set()
    k = min(k_cells_from_B, len(diff))
    cells_take = rng.choice(diff, size=k, replace=False).tolist()
    cells_take_set = set(cells_take)

    # σ: piece at boardA[pos] is at SOME other pos in boardB.
    # Track which pieces are introduced and which are evicted.
    introduced = {boardB[pos][0] for pos in cells_take if pos in boardB}
    evicted = {boardA[pos][0] for pos in cells_take if pos in boardA}

    # Build hybrid: start from boardA, swap cells_take.
    hybrid = dict(boardA)
    for pos in cells_take:
        if pos in boardB:
            hybrid[pos] = boardB[pos]

    # Find duplicates: pieces appearing >1 time.
    from collections import Counter
    piece_counts = Counter(pid for pid, _ in hybrid.values())
    duplicates = {pid for pid, count in piece_counts.items() if count > 1}

    # For each duplicated piece, REMOVE it from its boardA position (since the
    # boardB-introduced version is at a cells_take position).
    cells_dropped = set()
    for pos, (pid, rot) in list(hybrid.items()):
        if pid in duplicates and pos not in cells_take_set:
            # This is the "old" position; remove.
            del hybrid[pos]
            cells_dropped.add(pos)
            duplicates.discard(pid)  # done with this piece

    # Cells now MISSING from hybrid: cells_dropped (need to be filled)
    # Available pieces: pieces from boardA that aren't currently in hybrid.
    used_pieces = set(pid for pid, _ in hybrid.values())
    all_pieces_in_A = {pid for pid, _ in boardA.values()}
    available = all_pieces_in_A - used_pieces

    return hybrid, cells_dropped, list(available)


def main():
    # Pick two basins to hybridize.
    record_paths = [
        REPO / "database-400-480" / "461_RECORD_461_off110_seed1_8e88ff5a.json",
        REPO / "database-400-480" / "460_RECORD_460_bf_bw_off125_seed42_156f0832.json",
    ]
    boardA, sA = load_board(record_paths[0])
    boardB, sB = load_board(record_paths[1])
    print(f"Basin A: {record_paths[0].name}, score {sA}", flush=True)
    print(f"Basin B: {record_paths[1].name}, score {sB}", flush=True)

    pieces = load_pieces()
    print(f"  rescored A: {score_board(boardA, pieces)}", flush=True)
    print(f"  rescored B: {score_board(boardB, pieces)}", flush=True)

    diff = [pos for pos in range(256) if boardA.get(pos) != boardB.get(pos)]
    print(f"  differing cells: {len(diff)} of 256", flush=True)

    rng = np.random.default_rng(42)
    s0 = max(sA, sB)
    best_found = s0
    best_board = boardA

    print(f"\n=== CROSS-BASIN BRIDGE trials ===", flush=True)

    for trial in range(20):
        k_pct = rng.choice([0.15, 0.20, 0.25, 0.30, 0.40])
        k = int(k_pct * len(diff))
        if k < 4: continue
        hybrid, missing_cells, available_pieces = hybridize(boardA, boardB, k, rng)
        if len(missing_cells) != len(available_pieces):
            # imbalance — skip
            print(f"  trial {trial}: imbalanced (missing={len(missing_cells)}, avail={len(available_pieces)})", flush=True)
            continue
        # Run iter-Hungarian on the missing cells.
        repaired = iterhung_repair(hybrid, pieces, list(missing_cells), available_pieces, max_iters=5)
        if repaired is None: continue
        sc = score_board(repaired, pieces)
        marker = " 🎯" if sc > s0 else ""
        print(f"  trial {trial}: k_from_B={k}/{len(diff)} ({k_pct*100:.0f}%), missing={len(missing_cells)}, score={sc}{marker}", flush=True)
        if sc > best_found:
            best_found = sc
            best_board = repaired

    print(f"\n=== SUMMARY ===")
    print(f"  Best score across 20 trials: {best_found}")
    if best_found > s0:
        print(f"  🎯🎯 BREAKTHROUGH: {s0} → {best_found}!")
        out_path = REPO / "output" / "vol-125" / f"cross_basin_bridge_{best_found}.json"
        out_data = {
            "matched": best_found,
            "source": "cross_basin_bridge",
            "basin_A": str(record_paths[0].name),
            "basin_B": str(record_paths[1].name),
            "placement": [
                {"pos": p, "piece_id": pid, "rotation": rot}
                for p, (pid, rot) in sorted(best_board.items())
            ],
        }
        out_path.write_text(json.dumps(out_data, indent=2))
        print(f"  Saved: {out_path}")


if __name__ == "__main__":
    main()
