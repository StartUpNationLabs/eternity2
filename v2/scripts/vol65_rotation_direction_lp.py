#!/usr/bin/env python3
"""Vol-65 — Rotation-direction-balanced LP bound.

Idea: with full rotation freedom (no piece-uniqueness conflict, no
cell-uniqueness conflict, no edge-spatial conflict), the puzzle's
matched-edge upper bound is determined by COLOR-DIRECTION BALANCE.

A horizontal match of color c at edge (left-cell, right-cell) uses
the East-color of left-cell and the West-color of right-cell, both
being c.

After rotation, each piece p chooses rotation k. The cyclic shift
of p's (N, E, S, W) tuple makes color c appear at some direction d.

Constraints:
- Per-piece: Σ_k r[p, k] = 1 (each piece has exactly one rotation)
- Per-color hor: hor_match(c) ≤ Σ pieces+rotation that have c at E
- Per-color hor: hor_match(c) ≤ Σ pieces+rotation that have c at W
- Same for vertical (N/S).

Objective: maximize Σ_c [hor_match(c) + ver_match(c)].

This is RELAXED of:
- Piece-uniqueness in CELLS (any piece can appear anywhere)
- Cell-pair adjacency (matches don't need to form a planar layout)

So the result is an UPPER BOUND on E2 score. Sound but loose.

LP size: ~1100 vars, ~344 rows. Tiny, solves in milliseconds.
"""

import collections
import csv
import json
from pathlib import Path

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix

PUZZLE_CSV = "../data/puzzles/size_16_official_eternity.csv"


def load_pieces():
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
            pieces.append((col(parts[0]), col(parts[1]), col(parts[2]), col(parts[3])))
    return pieces


def rotate(edges, k):
    n, e, s, w = edges
    if k == 0: return (n, e, s, w)
    if k == 1: return (w, n, e, s)
    if k == 2: return (s, w, n, e)
    if k == 3: return (e, s, w, n)


def main():
    pieces = load_pieces()
    n_pieces = len(pieces)
    non_border = sorted(set(c for p in pieces for c in p if c != 0))
    n_colors = len(non_border)
    color_idx = {c: i for i, c in enumerate(non_border)}

    # Variables:
    # r[p, k] for p in 0..n_pieces, k in 0..3: indices 0..n_pieces*4-1
    # hor[c] for each non-border color c: indices n_pieces*4..n_pieces*4 + n_colors - 1
    # ver[c]: n_pieces*4 + n_colors .. n_pieces*4 + 2*n_colors - 1
    def r_idx(p, k): return p * 4 + k
    def hor_idx(c): return n_pieces * 4 + color_idx[c]
    def ver_idx(c): return n_pieces * 4 + n_colors + color_idx[c]
    n_vars = n_pieces * 4 + 2 * n_colors

    # Objective: max Σ (hor + ver) = min -Σ
    c_obj = np.zeros(n_vars)
    for c in non_border:
        c_obj[hor_idx(c)] = -1.0
        c_obj[ver_idx(c)] = -1.0

    # Equality: Σ_k r[p, k] = 1 per piece
    eq_rows = []
    eq_cols = []
    eq_data = []
    for p in range(n_pieces):
        for k in range(4):
            eq_rows.append(p)
            eq_cols.append(r_idx(p, k))
            eq_data.append(1.0)
    A_eq = coo_matrix((eq_data, (eq_rows, eq_cols)),
                      shape=(n_pieces, n_vars)).tocsr()
    b_eq = np.ones(n_pieces)

    # Inequality: hor[c] <= Σ_{p, k: piece p rotation k has color c at E} r[p, k]
    # i.e., hor[c] - Σ r <= 0
    # Similar for W, N, S.
    ub_rows = []
    ub_cols = []
    ub_data = []
    rcount = 0
    side_E = 1; side_W = 3; side_N = 0; side_S = 2

    for c in non_border:
        # hor[c] <= sum r[p, k] where rotated piece p has c at E (side 1)
        ub_rows.append(rcount); ub_cols.append(hor_idx(c)); ub_data.append(1.0)
        for p in range(n_pieces):
            for k in range(4):
                if rotate(pieces[p], k)[side_E] == c:
                    ub_rows.append(rcount)
                    ub_cols.append(r_idx(p, k))
                    ub_data.append(-1.0)
        rcount += 1

        # hor[c] <= sum r[p, k] where rotated piece p has c at W (side 3)
        ub_rows.append(rcount); ub_cols.append(hor_idx(c)); ub_data.append(1.0)
        for p in range(n_pieces):
            for k in range(4):
                if rotate(pieces[p], k)[side_W] == c:
                    ub_rows.append(rcount)
                    ub_cols.append(r_idx(p, k))
                    ub_data.append(-1.0)
        rcount += 1

        # ver[c] <= sum r[p, k] where rotated piece p has c at N (side 0)
        ub_rows.append(rcount); ub_cols.append(ver_idx(c)); ub_data.append(1.0)
        for p in range(n_pieces):
            for k in range(4):
                if rotate(pieces[p], k)[side_N] == c:
                    ub_rows.append(rcount)
                    ub_cols.append(r_idx(p, k))
                    ub_data.append(-1.0)
        rcount += 1

        # ver[c] <= sum r[p, k] where rotated piece p has c at S (side 2)
        ub_rows.append(rcount); ub_cols.append(ver_idx(c)); ub_data.append(1.0)
        for p in range(n_pieces):
            for k in range(4):
                if rotate(pieces[p], k)[side_S] == c:
                    ub_rows.append(rcount)
                    ub_cols.append(r_idx(p, k))
                    ub_data.append(-1.0)
        rcount += 1

    A_ub = coo_matrix((ub_data, (ub_rows, ub_cols)),
                      shape=(rcount, n_vars)).tocsr()
    b_ub = np.zeros(rcount)

    print(f"LP: {n_vars} vars, {n_pieces} eq, {rcount} ub")
    bounds = [(0.0, 1.0)] * n_vars

    # NOTE: a horizontal match is BETWEEN two cells. So total horizontal
    # matches ≤ number of horizontal edges in the 16×16 grid = 15 × 16 = 240.
    # Similarly vertical ≤ 240. So we can add: Σ hor ≤ 240, Σ ver ≤ 240.
    # (Actually these are implied by other constraints but explicit helps.)
    # Also: total matches = hor + ver ≤ 480.
    # Add these as additional UB:
    extra_rows = []; extra_cols = []; extra_data = []
    extra_rcount = 0
    # Σ hor ≤ 240
    for c in non_border:
        extra_rows.append(extra_rcount); extra_cols.append(hor_idx(c))
        extra_data.append(1.0)
    extra_rcount += 1
    # Σ ver ≤ 240
    for c in non_border:
        extra_rows.append(extra_rcount); extra_cols.append(ver_idx(c))
        extra_data.append(1.0)
    extra_rcount += 1
    A_extra = coo_matrix((extra_data, (extra_rows, extra_cols)),
                         shape=(extra_rcount, n_vars)).tocsr()
    from scipy.sparse import vstack as sp_vstack
    A_ub_full = sp_vstack([A_ub, A_extra]).tocsr()
    b_ub_full = np.concatenate([b_ub, np.array([240.0, 240.0])])

    print("\nSolving LP (fractional)...")
    import time
    t0 = time.time()
    res = linprog(c_obj, A_ub=A_ub_full, b_ub=b_ub_full,
                  A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
    print(f"  Time: {time.time()-t0:.2f}s")
    print(f"  LP UB: {-res.fun:.4f}")

    # Now solve as MIP (integer r[p, k])
    print("\nSolving MIP (integer r)...")
    integrality = np.zeros(n_vars)
    for p in range(n_pieces):
        for k in range(4):
            integrality[r_idx(p, k)] = 1  # r is binary
    # hor, ver remain continuous
    t1 = time.time()
    res_mip = linprog(c_obj, A_ub=A_ub_full, b_ub=b_ub_full,
                      A_eq=A_eq, b_eq=b_eq, bounds=bounds,
                      method="highs",
                      integrality=integrality)
    print(f"  Time: {time.time()-t1:.2f}s")
    print(f"  Status: {res_mip.message}")
    if not res_mip.success:
        print(f"  MIP failed; falling back to LP")
        res = res
    else:
        res = res_mip

    lp_obj = -res.fun
    print()
    print(f"=== Rotation-direction-balanced MIP UB on canonical E2: {lp_obj:.4f} ===")

    # Per-color breakdown
    print(f"\nPer-color contributions:")
    for c in non_border:
        h = res.x[hor_idx(c)]
        v = res.x[ver_idx(c)]
        print(f"  color {c:2d}: hor={h:.2f} ver={v:.2f} sum={h+v:.2f}")
    # Rotation choices (most-likely rotation per piece)
    rot_choices = []
    for p in range(n_pieces):
        scores = [res.x[r_idx(p, k)] for k in range(4)]
        rot_choices.append(int(np.argmax(scores)))
    print(f"\nPiece-rotation parity sum mod 4 in LP solution: "
          f"{sum(rot_choices) % 4}")
    # Fractionality of r
    r_int = sum(1 for p in range(n_pieces)
                if any(res.x[r_idx(p, k)] > 0.999 for k in range(4)))
    print(f"Pieces with integer rotation in LP: {r_int}/{n_pieces}")


if __name__ == "__main__":
    main()


# === POSTMORTEM (2026-05-15) ===
#
# This LP gives 44 because it captures a misleading constraint:
# each piece-rotation contributes at most 1 to total (color, direction)
# count. With 22 colors × 4 directions = 88 (c, d) cells competing for
# 256 piece units, average is 2.9 per cell. The MIN over (E_c, W_c) for
# fixed c can be balanced at 1 per color (since LP picks halves).
#
# The LP does NOT bound actual E2 edges, because each piece contributes
# 1 to (c_E, E) AND 1 to (c_W, W) AND 1 to (c_N, N) AND 1 to (c_S, S),
# but the LP sums only over one direction at a time. The integer
# constraint adds: each piece picks one rotation, contributing 1 unit
# to each of 4 specific (c, d) tuples.
#
# The right formulation needs to count EDGES in the assembled board:
# each cell pair (c1, c2) contributes ONE edge, and that edge's match
# depends on c1.E vs c2.W (or c1.S vs c2.N). The hor[c] ≤ min(E_count(c),
# W_count(c)) idea requires modeling that the E_count and W_count are
# DEFINED PER ROW (since horizontal edges within row r need r's E and W
# pieces to align).
#
# This LP is essentially worthless for E2 bounds. Marked as a null
# result. The 307 bound from vol65_ps_matching_lp.py is the correct
# canonical-orientation-fixed bound; the 44 here is a mis-formulation.
