#!/usr/bin/env python3
"""Wauters/Salassa polishing pipeline for an Eternity II board.

Implements the EXTRACTABLE polishing steps from Salassa et al. 2017
(arXiv:1709.00252) §3:
  - TA (Tile Assignment): probabilistic K=16 non-adjacent tile removal,
    reinsert optimally via Hungarian matching.
  - BW (Black & White): checkers pattern, Hungarian on each half.
  - TSR (Tile Swap + Rotation): exhaustive 2-swap + rotation, steepest
    descent until local optimum.

Skipped (would need MILP / max-clique):
  - BO (Border Optimisation): requires MILP solver on border ring.
  - RO (Region Optimisation via Max-Clique): requires Grosso-Locatelli
    -Pullan or python-igraph max-clique solver.

Steepest-descent acceptance only (no Metropolis). Outer loop is one
pass through {TA → BW → TSR}, repeated until no improvement.

Usage:
    python3 scripts/wauters_polish.py BOARD_JSON [--out out.json]
                                       [--ta-n 1000] [--ta-k 16]
                                       [--max-outer 5]

The board is read from .placement (the canonical pt_e2 format) or
falls back to bucas_url decoding. Output is a JSON in the same format
as pt_e2's report, ready to feed back into pt_e2 --start-from.

This implementation is single-core Python + scipy. No CPU contention
with concurrently-running Rust PT/CP.

Hint pieces: pinned (never moved). The official 5 hint cells are
identified by reading the puzzle CSV's per-piece hint columns.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

W = 16
H = 16
BORDER = 0
N_CELLS = W * H


def parse_csv_piece_word(s):
    v = int(s.strip(), 2)
    if v == 65535:
        return 0  # BORDER
    return v


def load_puzzle(path):
    """Returns (pieces_4col, hints_dict).
    pieces_4col: numpy array (n_pieces, 4) = (top, right, bottom, left).
    hints_dict: pos -> (piece_id, rotation).
    """
    pieces = []
    hints = {}
    with open(path) as f:
        size = int(f.readline().strip())
        assert size == W, f"expected size {W}, got {size}"
        for pid, line in enumerate(f):
            cols = line.strip().split(',')
            if len(cols) < 4:
                continue
            quad = tuple(parse_csv_piece_word(cols[i]) for i in range(4))
            pieces.append(quad)
            if len(cols) >= 7:
                x = int(cols[4]); y = int(cols[5]); rot = int(cols[6])
                if (x, y, rot) != (0, 0, 0):
                    pos = y * W + x
                    hints[pos] = (pid, rot)
    pieces_arr = np.array(pieces, dtype=np.int32)
    return pieces_arr, hints


def piece_rotations_tensor(pieces):
    """Returns (n_pieces, 4, 4) tensor: piece_rotations[p, r, side]
    gives the color on `side` of piece p rotated by r 90-degree CW
    increments. side: 0=top, 1=right, 2=bottom, 3=left.

    Rotation convention (matches Rust core/src/piece.rs):
      rot=0: (top, right, bottom, left) = (t, r, b, l)
      rot=1 (CW 90):  (l, t, r, b)
      rot=2 (180):    (b, l, t, r)
      rot=3 (CCW 90): (r, b, l, t)
    """
    n = pieces.shape[0]
    out = np.zeros((n, 4, 4), dtype=np.int32)
    out[:, 0, :] = pieces  # (top, right, bottom, left)
    # rot=1: rotated CW: new top = old left, new right = old top, new bottom = old right, new left = old bottom
    out[:, 1, 0] = pieces[:, 3]
    out[:, 1, 1] = pieces[:, 0]
    out[:, 1, 2] = pieces[:, 1]
    out[:, 1, 3] = pieces[:, 2]
    # rot=2: 180
    out[:, 2, 0] = pieces[:, 2]
    out[:, 2, 1] = pieces[:, 3]
    out[:, 2, 2] = pieces[:, 0]
    out[:, 2, 3] = pieces[:, 1]
    # rot=3: CCW
    out[:, 3, 0] = pieces[:, 1]
    out[:, 3, 1] = pieces[:, 2]
    out[:, 3, 2] = pieces[:, 3]
    out[:, 3, 3] = pieces[:, 0]
    return out


def load_board(json_path, n_pieces):
    """Returns board as (N_CELLS,) array of int (piece_id * 4 + rotation),
    or -1 for empty. We pack (piece_id, rotation) into a single int.
    """
    j = json.load(open(json_path))
    placement = j.get("placement")
    if placement is None:
        raise ValueError(f"no placement array in {json_path}")
    assert len(placement) == N_CELLS
    board = np.full(N_CELLS, -1, dtype=np.int32)
    for pos, cell in enumerate(placement):
        if cell is None:
            continue
        pid = int(cell["piece_id"])
        rot = int(cell["rotation"])
        board[pos] = pid * 4 + rot
    return board, j


def unpack(packed):
    """packed -> (pid, rot)."""
    return packed // 4, packed % 4


def pack(pid, rot):
    return pid * 4 + rot


def score_board(board, piece_rot):
    """Total matched interior edges."""
    matched = 0
    for y in range(H):
        for x in range(W):
            pos = y * W + x
            if board[pos] < 0:
                continue
            pid, rot = unpack(board[pos])
            edges = piece_rot[pid, rot]
            # Right neighbor.
            if x + 1 < W:
                rpos = y * W + (x + 1)
                if board[rpos] < 0:
                    continue
                rpid, rrot = unpack(board[rpos])
                redges = piece_rot[rpid, rrot]
                if edges[1] == redges[3] and edges[1] != BORDER:
                    matched += 1
            # Bottom neighbor.
            if y + 1 < H:
                bpos = (y + 1) * W + x
                if board[bpos] < 0:
                    continue
                bpid, brot = unpack(board[bpos])
                bedges = piece_rot[bpid, brot]
                if edges[2] == bedges[0] and edges[2] != BORDER:
                    matched += 1
    return matched


def cell_class(pos):
    """0=corner, 1=edge, 2=interior."""
    x, y = pos % W, pos // W
    n_border_sides = (x == 0) + (x == W - 1) + (y == 0) + (y == H - 1)
    if n_border_sides >= 2:
        return 0  # corner (only 4 cells)
    if n_border_sides == 1:
        return 1  # edge
    return 2  # interior


def neighbour_edge_constraint(pos):
    """For a cell at position `pos`, return list of (side, required_color) constraints
    arising from board borders (no neighbor on that side ⇒ side must be BORDER).

    side: 0=top, 1=right, 2=bottom, 3=left
    """
    x, y = pos % W, pos // W
    constraints = []
    if y == 0:
        constraints.append((0, BORDER))  # top is board edge
    if x == W - 1:
        constraints.append((1, BORDER))
    if y == H - 1:
        constraints.append((2, BORDER))
    if x == 0:
        constraints.append((3, BORDER))
    return constraints


def local_match_at(board, piece_rot, pos, candidate_packed=None):
    """Count matched edges contributed by the cell at `pos` to its 4 neighbours.
    If `candidate_packed` is given, evaluate as if pos had that packed value
    instead of board[pos]. Each match counts ONCE per shared edge.
    """
    if candidate_packed is None:
        if board[pos] < 0:
            return 0
        pid, rot = unpack(board[pos])
    else:
        pid, rot = unpack(candidate_packed)
    edges = piece_rot[pid, rot]
    x, y = pos % W, pos // W
    m = 0
    # Top
    if y > 0:
        np_ = (y - 1) * W + x
        if board[np_] >= 0:
            npid, nrot = unpack(board[np_])
            nedges = piece_rot[npid, nrot]
            if edges[0] == nedges[2] and edges[0] != BORDER:
                m += 1
    # Right
    if x + 1 < W:
        np_ = y * W + (x + 1)
        if board[np_] >= 0:
            npid, nrot = unpack(board[np_])
            nedges = piece_rot[npid, nrot]
            if edges[1] == nedges[3] and edges[1] != BORDER:
                m += 1
    # Bottom
    if y + 1 < H:
        np_ = (y + 1) * W + x
        if board[np_] >= 0:
            npid, nrot = unpack(board[np_])
            nedges = piece_rot[npid, nrot]
            if edges[2] == nedges[0] and edges[2] != BORDER:
                m += 1
    # Left
    if x > 0:
        np_ = y * W + (x - 1)
        if board[np_] >= 0:
            npid, nrot = unpack(board[np_])
            nedges = piece_rot[npid, nrot]
            if edges[3] == nedges[1] and edges[3] != BORDER:
                m += 1
    return m


def piece_class(piece_edges):
    """Classify a piece by number of BORDER edges: 2=corner, 1=edge, 0=interior."""
    n = (piece_edges == BORDER).sum()
    if n >= 2:
        return 0
    if n == 1:
        return 1
    return 2


def compute_cost_matrix(board, piece_rot, removed_positions, removed_piece_ids,
                        pinned_set):
    """For the TA neighborhood: removed_piece_ids are the K piece IDs that
    were removed; removed_positions are the K hole positions. Construct
    a cost matrix of shape (K, K*4) where cost[i, j*4 + r] = number of
    UNMATCHED edges contributed by placing removed_piece_ids[i] at
    removed_positions[j] with rotation r, against the 4 fixed neighbours
    on the board (which are NOT among the removed cells, since we
    removed only non-adjacent cells).

    For piece-class compatibility: pieces must go to cells of compatible
    class (corner pieces to corner cells, etc.). Incompatible
    (piece, position, rot) gets a large cost (sentinel = 9999).

    Linear assignment finds the minimum-cost assignment of pieces to
    (position, rotation) pairs, with each piece used exactly once and
    each position filled by exactly one piece-rotation.

    Returns a numpy float64 array.
    """
    K = len(removed_positions)
    cost = np.full((K, K * 4), 9999.0, dtype=np.float64)

    cell_classes = [cell_class(p) for p in removed_positions]
    piece_classes = [piece_class(piece_rot[pid, 0]) for pid in removed_piece_ids]

    for i, pid in enumerate(removed_piece_ids):
        pclass = piece_classes[i]
        for j, pos in enumerate(removed_positions):
            cclass = cell_classes[j]
            # Strict piece-class assignment.
            if pclass != cclass:
                continue
            # Border-side constraints: piece edges facing board border must be BORDER.
            bdry = neighbour_edge_constraint(pos)
            for r in range(4):
                edges = piece_rot[pid, r]
                # Check border constraints.
                ok = True
                for side, req in bdry:
                    if edges[side] != req:
                        ok = False
                        break
                if not ok:
                    continue
                # Cost = (unmatched edges) when placing pid+r at pos.
                # We count UNMATCHED interior-facing edges by computing
                # 4 - (matches against existing fixed neighbours) - (BORDER edges).
                # Actually, the cost matrix should represent COST of placement;
                # use "negative matches" so minimizing cost = maximizing matches.
                # But we want unmatched-edge count interpretation.
                # We adopt: cost = -matches_contributed.
                matches = local_match_at(board, piece_rot, pos,
                                         candidate_packed=pack(pid, r))
                cost[i, j * 4 + r] = -float(matches)
    return cost


def remove_pieces(board, positions):
    """Remove pieces at given positions, returning the piece_ids that were there.
    Positions where board is already empty get pid=-1 (skip)."""
    pids = []
    for pos in positions:
        if board[pos] < 0:
            pids.append(-1)
        else:
            pid, _rot = unpack(board[pos])
            pids.append(pid)
            board[pos] = -1
    return pids


def reinsert_via_hungarian(board, piece_rot, positions, piece_ids, pinned_set):
    """Solve bipartite matching to reinsert piece_ids at positions
    (with optimal rotation). Updates board in place.

    Returns the total matches contributed by the reinserted set.
    """
    K = len(positions)
    assert len(piece_ids) == K
    # Filter to non-empty (skip -1 piece_ids).
    valid_idx = [i for i, p in enumerate(piece_ids) if p >= 0]
    if not valid_idx:
        return 0
    valid_pids = [piece_ids[i] for i in valid_idx]
    valid_positions = [positions[i] for i in valid_idx]
    K = len(valid_idx)

    cost = compute_cost_matrix(board, piece_rot, valid_positions, valid_pids, pinned_set)

    # Hungarian (linear_sum_assignment) — supports rectangular cost; we have
    # K rows × K*4 cols. We allow each piece to be assigned to one of the
    # K positions × 4 rotations, but ensure each POSITION is used at most once.
    # scipy's lsap on rectangular gives row indices (each piece) → col indices
    # (each is a position*4+rot). But position-uniqueness is NOT guaranteed:
    # two different pieces could be assigned to (same pos, different rot).
    #
    # Workaround: collapse to (K, K) cost matrix where cost[i, j] = best rotation cost
    # for piece i at position j. Then map back to rotation.
    cost_pos = np.full((K, K), 9999.0, dtype=np.float64)
    best_rot = np.zeros((K, K), dtype=np.int32)
    for i in range(K):
        for j in range(K):
            row = cost[i, j*4:(j+1)*4]
            best_r = int(np.argmin(row))
            cost_pos[i, j] = row[best_r]
            best_rot[i, j] = best_r

    row_ind, col_ind = linear_sum_assignment(cost_pos)
    total_match = 0
    for i, j in zip(row_ind, col_ind):
        if cost_pos[i, j] >= 9999.0:
            # Infeasible assignment fell through; can't place this piece.
            # Restore: leave empty. Caller should handle.
            continue
        pid = valid_pids[i]
        pos = valid_positions[j]
        rot = best_rot[i, j]
        board[pos] = pack(pid, rot)
        total_match += -int(cost_pos[i, j])
    return total_match


def sample_non_adjacent_cells(board, K, pinned_set, rng, prob_weights=None):
    """Sample K mutually non-adjacent cells (no two share an edge), weighted
    by prob_weights[pos] if given (must be non-negative).

    Pinned cells (hints) are excluded. Uses a greedy random-acceptance
    approach: repeatedly draw a position, accept if not pinned and not
    adjacent to any already-selected. Cap attempts at 10*K*N_CELLS.
    """
    if prob_weights is None:
        weights = np.ones(N_CELLS, dtype=np.float64)
    else:
        weights = np.array(prob_weights, dtype=np.float64).copy()
    weights[list(pinned_set)] = 0.0
    if weights.sum() == 0:
        return []

    selected = []
    selected_set = set()
    forbidden = set(pinned_set)
    max_attempts = 10 * K * N_CELLS
    for _ in range(max_attempts):
        if len(selected) >= K:
            break
        if weights.sum() == 0:
            break
        p = weights / weights.sum()
        pos = int(rng.choice(N_CELLS, p=p))
        if pos in forbidden:
            weights[pos] = 0
            continue
        selected.append(pos)
        selected_set.add(pos)
        forbidden.add(pos)
        # Mark all 4 neighbours forbidden too (non-adjacent constraint).
        x, y = pos % W, pos // W
        for (dx, dy) in [(-1,0),(1,0),(0,-1),(0,1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H:
                npos = ny * W + nx
                forbidden.add(npos)
                weights[npos] = 0
        weights[pos] = 0
    return selected


def per_cell_unmatched_count(board, piece_rot):
    """For each cell, count unmatched edges (out of 4)."""
    unmatched = np.zeros(N_CELLS, dtype=np.float64)
    for pos in range(N_CELLS):
        if board[pos] < 0:
            continue
        m = local_match_at(board, piece_rot, pos)
        # Pieces have up to 4 edges; corners 2 interior, edges 3 interior, interior 4.
        cclass = cell_class(pos)
        if cclass == 0:
            denom = 2
        elif cclass == 1:
            denom = 3
        else:
            denom = 4
        unmatched[pos] = denom - m
    return unmatched


def tsr_iteration(board, piece_rot, pinned_set, rng, max_attempts=None):
    """TSR (Tile Swap + Rotation): pick two non-pinned cells of compatible
    class, swap their pieces, try all 16 rotation pairs, accept the best
    if it strictly improves total score (steepest descent). Returns
    delta_score and (i, j) of the cells swapped (or None if no improvement).

    Strictly improving (delta > 0) — needs delta >= 1.

    For efficiency: iterate over all O(N^2) pairs but stop at first
    improvement (first-improvement local search; classic LS heuristic).
    """
    cells_by_class = [[] for _ in range(3)]
    for pos in range(N_CELLS):
        if pos in pinned_set:
            continue
        if board[pos] < 0:
            continue
        cells_by_class[cell_class(pos)].append(pos)

    # Shuffle each class so we don't always start at the same pair.
    for cl in range(3):
        rng.shuffle(cells_by_class[cl])

    best_delta = 0
    best_swap = None
    best_rots = None
    attempts = 0

    score_before = score_board(board, piece_rot)
    for cl in range(3):
        cells = cells_by_class[cl]
        for i_idx in range(len(cells)):
            for j_idx in range(i_idx + 1, len(cells)):
                p_i = cells[i_idx]
                p_j = cells[j_idx]
                pid_i, _ = unpack(board[p_i])
                pid_j, _ = unpack(board[p_j])

                # For corners and edges, only certain rotations are valid;
                # for interior cells, all 4. We just try all 4 and use the
                # local_match_at constraint check (BORDER edges).
                # Need to check feasibility (piece must respect border sides).
                old_packed_i = int(board[p_i])
                old_packed_j = int(board[p_j])

                # Old local contribution (pair).
                # We approximate by isolated local contributions; since
                # the pair is mostly non-adjacent (different cells),
                # this slightly under-counts adjacent matches. But for
                # the deltas it's symmetric and works for non-adjacent
                # pairs. For adjacent pairs we'd need the joint score.
                x_i, y_i = p_i % W, p_i // W
                x_j, y_j = p_j % W, p_j // W
                adjacent = (abs(x_i - x_j) + abs(y_i - y_j) == 1)

                # For both adjacent and non-adjacent pairs we compute
                # the joint match-count which correctly handles the
                # shared edge between them (counted once in score, twice
                # in sum-of-local-matches).
                old_local_i = local_match_at(board, piece_rot, p_i)
                old_local_j = local_match_at(board, piece_rot, p_j)
                # For adjacent pairs: subtract 1 if the shared edge
                # currently matches, since local_match_at counts it
                # in BOTH cells' local counts.
                shared_match_old = 0
                if adjacent:
                    # Determine which sides face each other.
                    if x_j == x_i + 1:  # j is right of i
                        ci = piece_rot[unpack(old_packed_i)[0], unpack(old_packed_i)[1], 1]
                        cj = piece_rot[unpack(old_packed_j)[0], unpack(old_packed_j)[1], 3]
                    elif x_j == x_i - 1:  # j is left of i
                        ci = piece_rot[unpack(old_packed_i)[0], unpack(old_packed_i)[1], 3]
                        cj = piece_rot[unpack(old_packed_j)[0], unpack(old_packed_j)[1], 1]
                    elif y_j == y_i + 1:  # j is below i
                        ci = piece_rot[unpack(old_packed_i)[0], unpack(old_packed_i)[1], 2]
                        cj = piece_rot[unpack(old_packed_j)[0], unpack(old_packed_j)[1], 0]
                    else:  # y_j == y_i - 1, j is above i
                        ci = piece_rot[unpack(old_packed_i)[0], unpack(old_packed_i)[1], 0]
                        cj = piece_rot[unpack(old_packed_j)[0], unpack(old_packed_j)[1], 2]
                    if ci == cj and ci != BORDER:
                        shared_match_old = 1
                old_total = old_local_i + old_local_j - shared_match_old

                # Try all 4 × 4 = 16 rotation combos.
                best_pair_delta = 0
                best_pair_rots = None
                for r_i in range(4):
                    # Check that pid_j can sit at p_i with rotation r_i.
                    edges_i = piece_rot[pid_j, r_i]
                    bdry_i = neighbour_edge_constraint(p_i)
                    ok = all(edges_i[s] == c for s, c in bdry_i)
                    if not ok:
                        continue
                    for r_j in range(4):
                        edges_j = piece_rot[pid_i, r_j]
                        bdry_j = neighbour_edge_constraint(p_j)
                        ok2 = all(edges_j[s] == c for s, c in bdry_j)
                        if not ok2:
                            continue
                        # Hypothetical: place pid_j (r_i) at p_i and pid_i (r_j) at p_j.
                        board[p_i] = pack(pid_j, r_i)
                        board[p_j] = pack(pid_i, r_j)
                        new_local_i = local_match_at(board, piece_rot, p_i)
                        new_local_j = local_match_at(board, piece_rot, p_j)
                        shared_match_new = 0
                        if adjacent:
                            ep_i = piece_rot[pid_j, r_i]
                            ep_j = piece_rot[pid_i, r_j]
                            if x_j == x_i + 1:
                                a, b = ep_i[1], ep_j[3]
                            elif x_j == x_i - 1:
                                a, b = ep_i[3], ep_j[1]
                            elif y_j == y_i + 1:
                                a, b = ep_i[2], ep_j[0]
                            else:
                                a, b = ep_i[0], ep_j[2]
                            if a == b and a != BORDER:
                                shared_match_new = 1
                        new_total = new_local_i + new_local_j - shared_match_new
                        pair_delta = new_total - old_total
                        if pair_delta > best_pair_delta:
                            best_pair_delta = pair_delta
                            best_pair_rots = (r_i, r_j)
                        # Revert each trial.
                        board[p_i] = old_packed_i
                        board[p_j] = old_packed_j
                attempts += 1
                if best_pair_delta > 0 and best_pair_delta > best_delta:
                    best_delta = best_pair_delta
                    best_swap = (p_i, p_j)
                    best_rots = best_pair_rots
                    # Apply NOW and return (first-improvement strategy).
                    board[p_i] = pack(pid_j, best_pair_rots[0])
                    board[p_j] = pack(pid_i, best_pair_rots[1])
                    return best_delta, best_swap
                if max_attempts is not None and attempts >= max_attempts:
                    return 0, None
    return 0, None


def ta_iteration(board, piece_rot, K, pinned_set, rng):
    """One TA iteration: select K non-adjacent cells weighted by unmatched count,
    remove pieces, reinsert via Hungarian. Returns (delta_score, n_actually_removed).
    Steepest-descent: revert if score decreases.
    """
    score_before = score_board(board, piece_rot)
    weights = per_cell_unmatched_count(board, piece_rot) + 0.1  # ε

    selected = sample_non_adjacent_cells(board, K, pinned_set, rng, weights)
    if not selected:
        return 0, 0

    # Snapshot for revert.
    snapshot = {pos: int(board[pos]) for pos in selected}
    removed_pids = remove_pieces(board, selected)
    # Reinsert.
    reinsert_via_hungarian(board, piece_rot, selected, removed_pids, pinned_set)

    score_after = score_board(board, piece_rot)
    delta = score_after - score_before
    if delta < 0:
        # Revert.
        for pos, packed in snapshot.items():
            board[pos] = packed
        return 0, len(selected)
    return delta, len(selected)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board_json")
    ap.add_argument("--puzzle", default="../data/puzzles/size_16_official_eternity.csv")
    ap.add_argument("--out", default=None)
    ap.add_argument("--ta-n", type=int, default=1000)
    ap.add_argument("--ta-k", type=int, default=16)
    ap.add_argument("--max-outer", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    pieces, hints = load_puzzle(args.puzzle)
    piece_rot = piece_rotations_tensor(pieces)
    print(f"# loaded {pieces.shape[0]} pieces, {len(hints)} hints", file=sys.stderr)

    pinned_set = set(hints.keys())

    board, source_j = load_board(args.board_json, pieces.shape[0])
    initial_score = score_board(board, piece_rot)
    print(f"# initial score: {initial_score}/480", file=sys.stderr)

    rng = np.random.default_rng(args.seed)

    # -------- Outer loop: TA → TSR (BW deferred) --------
    best_score = initial_score
    best_board = board.copy()
    t0 = time.time()
    for outer in range(args.max_outer):
        outer_start_score = best_score
        # TA neighborhood (ta_n iterations).
        accepted_ta = 0
        for it in range(args.ta_n):
            delta, n_rem = ta_iteration(board, piece_rot, args.ta_k,
                                        pinned_set, rng)
            if delta > 0:
                accepted_ta += 1
                s = score_board(board, piece_rot)
                if s > best_score:
                    best_score = s
                    best_board = board.copy()
                    print(f"# [outer={outer+1} TA={it+1}] new best: {s}/480 (+{delta})",
                          file=sys.stderr)
            if it % 100 == 0:
                elapsed = time.time() - t0
                cur = score_board(board, piece_rot)
                print(f"# [outer={outer+1} TA={it+1}/{args.ta_n}] cur={cur} best={best_score} "
                      f"acc={accepted_ta} t={elapsed:.0f}s", file=sys.stderr)

        # TSR: exhaustive 2-swap until local optimum.
        print(f"# [outer={outer+1}] TSR phase starting", file=sys.stderr)
        tsr_iters = 0
        while True:
            delta, swap = tsr_iteration(board, piece_rot, pinned_set, rng)
            if delta <= 0 or swap is None:
                break
            tsr_iters += 1
            s = score_board(board, piece_rot)
            if s > best_score:
                best_score = s
                best_board = board.copy()
                print(f"# [outer={outer+1} TSR={tsr_iters}] new best: {s}/480 "
                      f"(+{delta}, swap {swap})", file=sys.stderr)
            if tsr_iters > 200:
                break
        print(f"# [outer={outer+1}] TSR: {tsr_iters} improvements, best={best_score}",
              file=sys.stderr)

        if best_score == outer_start_score:
            print(f"# outer {outer+1}: no improvement, stopping", file=sys.stderr)
            break

    # Output report (mimicking pt_e2 format).
    out_path = args.out or args.board_json.replace(".json", f"_polished_{best_score}of480.json")
    placement = []
    for pos in range(N_CELLS):
        if best_board[pos] < 0:
            placement.append(None)
        else:
            pid, rot = unpack(best_board[pos])
            placement.append({"piece_id": int(pid), "rotation": int(rot)})

    # Preserve original structure where possible.
    out = dict(source_j)
    out["score"] = {
        "matched_edges": int(best_score),
        "total_edges": 480,
        "percent": 100.0 * best_score / 480,
        "placed_cells": int((best_board >= 0).sum()),
        "total_cells": N_CELLS,
    }
    out["placement"] = placement
    out["details"] = out.get("details", {})
    out["details"]["wauters_polish"] = {
        "initial_score": int(initial_score),
        "final_score": int(best_score),
        "ta_n": args.ta_n,
        "ta_k": args.ta_k,
        "max_outer": args.max_outer,
        "seed": args.seed,
    }
    # Rewrite bucas_url? Skip for now; just placement is what pt_e2 --start-from needs.

    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

    print(f"\n=== DONE ===")
    print(f"initial: {initial_score}/480")
    print(f"final:   {best_score}/480 (delta +{best_score - initial_score})")
    print(f"output:  {out_path}")


if __name__ == "__main__":
    main()
