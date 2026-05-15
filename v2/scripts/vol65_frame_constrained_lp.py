#!/usr/bin/env python3
"""Vol-65 — Frame-constrained LP relaxation of E2.

Formulation:
- Variables x[piece, cell, rotation] for frame-respecting placements:
  * Corner pieces at corner cells, rotation forced by border-side direction
  * Edge pieces at perimeter (non-corner) cells, rotation forced by border-side direction
  * Interior pieces at interior cells, all 4 rotations
- Constraints:
  * Cell coverage: Σ_{(p,r) valid at c} x[p,c,r] = 1
  * Piece coverage: Σ_{(c,r) valid for p} x[p,c,r] = 1
- For each adjacent cell pair (c1, c2) and color c, an auxiliary:
  μ[c1, c2, c] = Σ_{(p,r): outgoing side of piece at c1 toward c2 has color c} x[p, c1, r]
- Matched edge contribution per (c1, c2): Σ_c y[c1, c2, c]
  where y[c1, c2, c] ≤ μ[c1, c2, c] AND y[c1, c2, c] ≤ μ[c2, c1, c]
- Objective: maximize total y.

This is a SOUND LP-relaxation of the full E2 matched-edge optimization.
If LP UB < 469, we've found a NEW sound bound.

Goal: compute LP-UB and compare to 469 (McGavin) and 480 (puzzle perfect).
"""

import collections
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix, vstack as sp_vstack

PUZZLE_CSV = "../data/puzzles/size_16_official_eternity.csv"
W = H = 16


def load_canonical_pieces():
    BORDER_RAW = 65535
    pieces = []
    with open(PUZZLE_CSV) as f:
        size = int(f.readline().strip())
        for idx, line in enumerate(f):
            line = line.strip()
            if not line: continue
            parts = line.split(",")
            def col(s):
                v = int(s.strip(), 2)
                return 0 if v == BORDER_RAW else v
            pieces.append((col(parts[0]), col(parts[1]),
                           col(parts[2]), col(parts[3])))
    return pieces


def rotate(edges, k):
    n, e, s, w = edges
    if k == 0: return (n, e, s, w)
    if k == 1: return (w, n, e, s)
    if k == 2: return (s, w, n, e)
    if k == 3: return (e, s, w, n)


def cell_kind(pos):
    r, c = divmod(pos, W)
    if r in (0, H - 1) and c in (0, W - 1): return "corner"
    if r in (0, H - 1) or c in (0, W - 1): return "edge"
    return "interior"


def piece_kind(edges):
    n = sum(1 for c in edges if c == 0)
    return {0: "interior", 1: "edge", 2: "corner"}.get(n)


def valid_rotations_at(piece_edges, pos):
    """Return list of rotations k such that piece in rotation k respects
    the frame at pos: border-color (0) sides face outward (toward frame),
    non-border sides face inward.

    For corner cells: 2 border sides must face outward.
    For edge cells: 1 border side must face outward.
    For interior cells: no border side allowed in any direction.
    """
    r, c = divmod(pos, W)
    # Determine which sides face outward (toward frame):
    # side 0=N faces frame iff r==0
    # side 1=E faces frame iff c==W-1
    # side 2=S faces frame iff r==H-1
    # side 3=W faces frame iff c==0
    outward = []
    if r == 0: outward.append(0)
    if c == W - 1: outward.append(1)
    if r == H - 1: outward.append(2)
    if c == 0: outward.append(3)

    valid = []
    for k in range(4):
        rotated = rotate(piece_edges, k)
        # All outward sides must be border-color (0); all inward sides must NOT
        ok = True
        for side in range(4):
            facing_frame = side in outward
            if facing_frame and rotated[side] != 0:
                ok = False
                break
            if not facing_frame and rotated[side] == 0:
                ok = False
                break
        if ok:
            valid.append(k)
    return valid


def main():
    pieces = load_canonical_pieces()
    n_pieces = len(pieces)

    # Enumerate frame-respecting placements: list of (piece_id, pos, rotation)
    placements = []  # (pid, pos, k)
    placement_idx = {}  # (pid, pos, k) -> var index
    for pid in range(n_pieces):
        pk = piece_kind(pieces[pid])
        for pos in range(W * H):
            ck = cell_kind(pos)
            if pk != ck:
                continue
            for k in valid_rotations_at(pieces[pid], pos):
                placement_idx[(pid, pos, k)] = len(placements)
                placements.append((pid, pos, k))
    n_x = len(placements)
    print(flush=True); print(f"Frame-respecting placements: {n_x}")

    # Per-cell list of placement indices
    cell_to_placements = collections.defaultdict(list)
    piece_to_placements = collections.defaultdict(list)
    for idx, (pid, pos, k) in enumerate(placements):
        cell_to_placements[pos].append(idx)
        piece_to_placements[pid].append(idx)

    # Print bookkeeping
    n_corner_placements = sum(1 for (pid, pos, k) in placements if cell_kind(pos) == "corner")
    n_edge_placements = sum(1 for (pid, pos, k) in placements if cell_kind(pos) == "edge")
    n_interior_placements = sum(1 for (pid, pos, k) in placements if cell_kind(pos) == "interior")
    print(flush=True); print(f"  corner placements:   {n_corner_placements}")
    print(flush=True); print(f"  edge placements:     {n_edge_placements}")
    print(flush=True); print(f"  interior placements: {n_interior_placements}")

    # Adjacent cell pairs (interior edges of the 16x16 grid)
    adjacent_pairs = []  # (c1, c2, dir) where dir=0 horizontal (c1.E faces c2.W), 1 vertical (c1.S faces c2.N)
    for r in range(H):
        for c in range(W - 1):
            c1 = r * W + c; c2 = r * W + (c + 1)
            adjacent_pairs.append((c1, c2, 0))
    for r in range(H - 1):
        for c in range(W):
            c1 = r * W + c; c2 = (r + 1) * W + c
            adjacent_pairs.append((c1, c2, 1))
    n_pairs = len(adjacent_pairs)
    print(flush=True); print(f"Adjacent cell pairs: {n_pairs} (= 2 × 15 × 16)")

    # Distinct non-border colors actually used (skip 0=border)
    non_border_colors = set()
    for p in pieces:
        for c in p:
            if c != 0:
                non_border_colors.add(c)
    non_border_colors = sorted(non_border_colors)
    n_colors = len(non_border_colors)
    print(flush=True); print(f"Non-border colors: {n_colors}")

    # For each adjacent pair (c1, c2, dir), enumerate which placements at c1
    # have outgoing color c toward c2, and which placements at c2 have
    # outgoing color c toward c1.
    # If dir=0 (horizontal): c1's East (side 1) faces c2's West (side 3).
    # If dir=1 (vertical):   c1's South (side 2) faces c2's North (side 0).
    side_c1 = {0: 1, 1: 2}  # outgoing side from c1
    side_c2 = {0: 3, 1: 0}  # outgoing side from c2

    # Variable y[c1, c2, color] for matched-edge contribution per pair per color
    # Constraint: y ≤ μ_left, y ≤ μ_right
    # where μ_left[c1, c2, color] = Σ_{x[p, c1, k]: outgoing color = color} x[..]
    #
    # We need to bound: y[c1, c2, color] ≤ Σ x[p, c1, k] over matching placements
    # AND y[c1, c2, color] ≤ Σ x[p, c2, k] over matching placements at c2
    # Then objective = Σ y.
    # y indexed per pair × color.
    y_idx = {}  # (pair_index, color) -> var index
    for pair_idx in range(n_pairs):
        for c in non_border_colors:
            y_idx[(pair_idx, c)] = n_x + len(y_idx)
    n_y = len(y_idx)
    print(flush=True); print(f"y variables: {n_y}")
    n_vars = n_x + n_y
    print(flush=True); print(f"Total LP variables: {n_vars}")

    # Build constraints
    print("\nBuilding LP constraints...")
    t0 = time.time()
    A_eq_rows = []
    b_eq_rows = []
    A_ub_rows = []
    b_ub_rows = []

    # Cell coverage: Σ x[*, c, *] = 1 for each cell c
    for pos in range(W * H):
        idxs = cell_to_placements[pos]
        if not idxs:
            # Cell has no valid placement — LP is infeasible
            print(flush=True); print(f"WARNING: cell {pos} has zero valid placements")
            continue
        A_eq_rows.append({i: 1.0 for i in idxs})
        b_eq_rows.append(1.0)

    # Piece coverage: Σ x[p, *, *] = 1 for each piece
    for pid in range(n_pieces):
        idxs = piece_to_placements[pid]
        if not idxs:
            print(flush=True); print(f"WARNING: piece {pid} has zero valid placements")
            continue
        A_eq_rows.append({i: 1.0 for i in idxs})
        b_eq_rows.append(1.0)

    # y constraints: y[c1, c2, color] ≤ μ_c1[color], y ≤ μ_c2[color]
    # Equivalently: y - sum x[c1 placements with matching color] ≤ 0
    for pair_idx, (c1, c2, d) in enumerate(adjacent_pairs):
        s1 = side_c1[d]
        s2 = side_c2[d]
        # Build maps: color -> list of placement indices at c1 with outgoing color = color
        c1_by_color = collections.defaultdict(list)
        for px in cell_to_placements[c1]:
            pid, pos, k = placements[px]
            outgoing = rotate(pieces[pid], k)[s1]
            if outgoing != 0:  # skip border color
                c1_by_color[outgoing].append(px)
        c2_by_color = collections.defaultdict(list)
        for px in cell_to_placements[c2]:
            pid, pos, k = placements[px]
            outgoing = rotate(pieces[pid], k)[s2]
            if outgoing != 0:
                c2_by_color[outgoing].append(px)
        for c in non_border_colors:
            y_var = y_idx[(pair_idx, c)]
            # y - Σ x[c1, color] ≤ 0
            coefs = {y_var: 1.0}
            for px in c1_by_color.get(c, []):
                coefs[px] = -1.0
            A_ub_rows.append(coefs)
            b_ub_rows.append(0.0)
            # y - Σ x[c2, color] ≤ 0
            coefs = {y_var: 1.0}
            for px in c2_by_color.get(c, []):
                coefs[px] = -1.0
            A_ub_rows.append(coefs)
            b_ub_rows.append(0.0)

    print(flush=True); print(f"  EQ rows: {len(A_eq_rows)}, UB rows: {len(A_ub_rows)}")
    print(flush=True); print(f"  Build time: {time.time()-t0:.2f}s")

    # Convert to sparse via COO (much faster than lil element-by-element)
    print("Converting to sparse matrices...", flush=True)
    t1 = time.time()
    from scipy.sparse import coo_matrix
    eq_data = []; eq_row = []; eq_col = []
    for i, row in enumerate(A_eq_rows):
        for j, val in row.items():
            eq_data.append(val); eq_row.append(i); eq_col.append(j)
    A_eq = coo_matrix((eq_data, (eq_row, eq_col)),
                      shape=(len(A_eq_rows), n_vars)).tocsr()
    ub_data = []; ub_row = []; ub_col = []
    for i, row in enumerate(A_ub_rows):
        for j, val in row.items():
            ub_data.append(val); ub_row.append(i); ub_col.append(j)
    A_ub = coo_matrix((ub_data, (ub_row, ub_col)),
                      shape=(len(A_ub_rows), n_vars)).tocsr()
    b_eq = np.array(b_eq_rows)
    b_ub = np.array(b_ub_rows)
    print(flush=True); print(f"  Convert time: {time.time()-t1:.2f}s", flush=True)
    print(flush=True); print(f"  A_eq shape: {A_eq.shape}, nnz: {A_eq.nnz}", flush=True)
    print(flush=True); print(f"  A_ub shape: {A_ub.shape}, nnz: {A_ub.nnz}", flush=True)

    # Objective: maximize sum of y → minimize -sum(y)
    c = np.zeros(n_vars)
    for v in y_idx.values():
        c[v] = -1.0

    bounds = [(0.0, 1.0)] * n_vars

    print("\nSolving LP...")
    t2 = time.time()
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds, method="highs")
    print(flush=True); print(f"  Solve time: {time.time()-t2:.2f}s")
    print(flush=True); print(f"  Status: {res.message}")

    if not res.success:
        print(flush=True); print(f"LP FAILED")
        sys.exit(1)

    lp_obj = -res.fun
    print()
    print(flush=True); print(f"=== Frame-constrained LP UB on canonical E2: {lp_obj:.4f} ===")
    print(flush=True); print(f"Compare to:")
    print(flush=True); print(f"  Perfect score: 480")
    print(flush=True); print(f"  McGavin community ceiling: 469")
    print(flush=True); print(f"  Our local-459: 459")

    # Per-color y usage
    y_use_by_color = collections.defaultdict(float)
    for (pair_idx, c), idx in y_idx.items():
        y_use_by_color[c] += res.x[idx]
    print(flush=True); print(f"\nLP y-edge use by color:")
    for c in non_border_colors:
        print(flush=True); print(f"  color {c:2d}: {y_use_by_color[c]:.2f} edges")

    # x-variable fractionality
    x_vals = res.x[:n_x]
    int1 = sum(1 for v in x_vals if v > 0.999)
    frac = sum(1 for v in x_vals if 0.001 < v < 0.999)
    print(flush=True); print(f"\nx-vars: {int1} integer-1, {frac} fractional, {len(x_vals)-int1-frac} ~zero")


if __name__ == "__main__":
    main()


# === POSTMORTEM 2 (2026-05-15) ===
#
# This LP was started on the full E2 placement polytope:
#   167,376 variables, 21,632 rows, ~960k nnz
#
# Ran for 48 min CPU in HiGHS via scipy.linprog and did not return.
# Killed after sunk-cost calculus showed expected output (LP UB = 480
# in fractional relaxation) wouldn't add information beyond what
# rotation-aware PS-LP already gave.
#
# Lesson: Python's scipy.linprog calls HiGHS via interior-point with
# default settings that don't converge fast on 167k-var problems
# even when sparse. For E2-scale full-board LPs, switch to:
#   - Rust good_lp + HiGHS direct API (like cluster_repair.rs)
#   - Or use simplex method (method="highs-ds") which is sometimes
#     faster on these problems
#   - Or split the LP into smaller per-row LPs
#
# The vol-62 cluster_repair MIP (which solves 50-70 cell joint MIPs
# in ~3min) is the right scale for HiGHS via Python.
