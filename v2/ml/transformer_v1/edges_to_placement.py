"""Convert predicted edges to a canonical-E2 piece placement.

After the transformer predicts edges at all 256 cells, we need to find:
- For each cell, which canonical-E2 piece (and rotation) best matches the
  predicted (N, E, S, W) edges?
- Subject to piece-uniqueness (each piece used exactly once).

This is a linear assignment problem solved via JV / Hungarian (lsap).

Cost matrix:
- Rows = 256 cells (× 4 rotations = 1024 rows for joint formulation)
- Cols = 256 canonical pieces
- Cost[cell, piece] = # mismatched edges between predicted and piece's edges

Output: 256 (piece_id, rotation) assignments per cell, with min total mismatch.
"""

import numpy as np
from scipy.optimize import linear_sum_assignment


W = 16
N_CELLS = 256


def rotate(piece, r):
    N, E, S, W_ = piece
    if r == 0: return (N, E, S, W_)
    if r == 1: return (W_, N, E, S)
    if r == 2: return (S, W_, N, E)
    if r == 3: return (E, S, W_, N)


def edges_to_placement(predicted_edges: np.ndarray, canonical_pieces: list,
                       fix_hints: dict = None) -> dict:
    """
    Args:
        predicted_edges: [256, 4] uint8 array of predicted (N, E, S, W) per cell
        canonical_pieces: list of 256 piece tuples (N, E, S, W) at rotation 0
        fix_hints: optional {pos: (piece_id, rotation)} to FREEZE during assignment

    Returns:
        {pos: (piece_id, rotation)} — best assignment minimizing total mismatch.
    """
    # Build per-cell × per-piece × rotation cost matrix.
    # For each (cell, piece, rot) combination, compute mismatch count.
    # Use 1024 × 256 cost (each piece occupies 4 rows for rotation).
    # Actually simpler: for each (cell, piece) precompute BEST rotation,
    # store that. Then solve 256×256 LAP.

    n = N_CELLS
    fixed_cells = set(fix_hints.keys()) if fix_hints else set()
    fixed_pieces = set(p for p, _ in fix_hints.values()) if fix_hints else set()

    cost = np.zeros((n, n), dtype=np.float32)
    best_rot = np.zeros((n, n), dtype=np.int8)

    for cell in range(n):
        if cell in fixed_cells:
            # Force this cell to its hint.
            pid, rot = fix_hints[cell]
            for piece in range(n):
                if piece == pid:
                    cost[cell, piece] = 0  # exact match
                    best_rot[cell, piece] = rot
                else:
                    cost[cell, piece] = 1e6  # huge penalty
            continue

        pred = predicted_edges[cell]  # (N, E, S, W)
        for piece in range(n):
            if piece in fixed_pieces:
                cost[cell, piece] = 1e6  # don't assign this piece here
                continue
            # Try all 4 rotations, pick best.
            best_mm = 5
            br = 0
            for r in range(4):
                p_edges = rotate(canonical_pieces[piece], r)
                mm = sum(1 for i in range(4) if p_edges[i] != pred[i])
                if mm < best_mm:
                    best_mm, br = mm, r
            cost[cell, piece] = best_mm
            best_rot[cell, piece] = br

    # Solve LAP.
    row_ind, col_ind = linear_sum_assignment(cost)
    placement = {}
    for cell, piece in zip(row_ind, col_ind):
        placement[int(cell)] = (int(piece), int(best_rot[cell, piece]))
    return placement


def score_placement(placement: dict, canonical_pieces: list) -> int:
    """Count matched edges (480 = perfect)."""
    matches = 0
    BORDER = 0
    for pos, (pid, rot) in placement.items():
        r, c = pos // W, pos % W
        e = rotate(canonical_pieces[pid], rot)
        # E ↔ neighbor's W
        if c < 15 and (pos + 1) in placement:
            nb_pid, nb_rot = placement[pos + 1]
            ne = rotate(canonical_pieces[nb_pid], nb_rot)
            if e[1] == ne[3] and e[1] != BORDER: matches += 1
        # S ↔ neighbor's N
        if r < 15 and (pos + W) in placement:
            nb_pid, nb_rot = placement[pos + W]
            ne = rotate(canonical_pieces[nb_pid], nb_rot)
            if e[2] == ne[0] and e[2] != BORDER: matches += 1
    return matches
