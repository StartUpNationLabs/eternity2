#!/usr/bin/env python3
"""V131-T1 — PRISM-LP: LP relaxation of E2 as a chromatic decomposition.

Cast E2 as an integer program and solve its LP relaxation. The LP
gives a SOUND upper bound on matched-edges; comparing it to the
backtrack-found integer optimum reveals the integrality gap.

Variables:
  x[c, p, r] ∈ [0,1]  for cell c, piece p, rotation r
  Cell constraint: sum_{p,r} x[c, p, r] = 1 for each c
  Piece constraint: sum_{c, r} x[c, p, r] = 1 for each p

  match[e, color] ∈ [0,1]
  For each edge e=(c1,c2,s1,s2) and color C:
    match[e, C] ≤ sum_{p,r : edges[p,r,s1]==C} x[c1, p, r]
    match[e, C] ≤ sum_{p,r : edges[p,r,s2]==C} x[c2, p, r]

Objective: maximize sum_e sum_{C != 0} match[e, C]
"""

from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path
import numpy as np
import scipy.sparse as sp
from scipy.optimize import linprog

REPO = Path(__file__).resolve().parents[1]


def load_puzzle_csv(csv_path):
    BORDER_RAW = 65535
    pieces = []
    with open(csv_path) as f:
        size = int(f.readline().strip())
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split(",")
            sides = []
            for s in parts[:4]:
                v = int(s.strip(), 2)
                sides.append(0 if v == BORDER_RAW else v)
            pieces.append(tuple(sides))
    return size, pieces


def rotate_piece(piece, r):
    N, E, S, W = piece
    return [(N, E, S, W), (E, S, W, N), (S, W, N, E), (W, N, E, S)][r]


def build_edges_3d(pieces):
    P = len(pieces)
    R = 4
    out = np.zeros((P, R, 4), dtype=np.int16)
    for p in range(P):
        for r in range(R):
            out[p, r] = rotate_piece(pieces[p], r)
    return out


def adjacent_pairs(size):
    W = size
    for r in range(size):
        for c in range(size):
            i = r * W + c
            if c < W - 1:
                yield (i, i + 1, 1, 3)
            if r < size - 1:
                yield (i, i + W, 2, 0)


def build_and_solve_lp(size, pieces, verbose=True):
    P = len(pieces)
    R = 4
    N = size * size
    edges3d = build_edges_3d(pieces)
    n_colors = int(edges3d.max()) + 1
    adj = list(adjacent_pairs(size))
    n_edges = len(adj)
    n_x = N * P * R
    n_m = n_edges * n_colors
    n_vars = n_x + n_m

    def x_idx(c, p, r): return c * P * R + p * R + r
    def m_idx(e_idx, color): return n_x + e_idx * n_colors + color

    if verbose:
        print(f"Vars: x={n_x}, m={n_m}, total={n_vars}", flush=True)

    # Equality constraints A_eq @ x = b_eq
    n_eq = N + P
    Aeq_rows, Aeq_cols, Aeq_vals = [], [], []
    for c in range(N):
        for p in range(P):
            for r in range(R):
                Aeq_rows.append(c)
                Aeq_cols.append(x_idx(c, p, r))
                Aeq_vals.append(1.0)
    for p in range(P):
        for c in range(N):
            for r in range(R):
                Aeq_rows.append(N + p)
                Aeq_cols.append(x_idx(c, p, r))
                Aeq_vals.append(1.0)
    A_eq = sp.csr_matrix((Aeq_vals, (Aeq_rows, Aeq_cols)), shape=(n_eq, n_vars))
    b_eq = np.ones(n_eq)

    # Inequality constraints
    Aub_rows, Aub_cols, Aub_vals = [], [], []
    row_count = 0
    for e_idx, (c1, c2, s1, s2) in enumerate(adj):
        for color in range(n_colors):
            Aub_rows.append(row_count)
            Aub_cols.append(m_idx(e_idx, color))
            Aub_vals.append(1.0)
            for p in range(P):
                for r in range(R):
                    if edges3d[p, r, s1] == color:
                        Aub_rows.append(row_count)
                        Aub_cols.append(x_idx(c1, p, r))
                        Aub_vals.append(-1.0)
            row_count += 1
            Aub_rows.append(row_count)
            Aub_cols.append(m_idx(e_idx, color))
            Aub_vals.append(1.0)
            for p in range(P):
                for r in range(R):
                    if edges3d[p, r, s2] == color:
                        Aub_rows.append(row_count)
                        Aub_cols.append(x_idx(c2, p, r))
                        Aub_vals.append(-1.0)
            row_count += 1
    A_ub = sp.csr_matrix((Aub_vals, (Aub_rows, Aub_cols)),
                         shape=(row_count, n_vars))
    b_ub = np.zeros(row_count)

    c_obj = np.zeros(n_vars)
    for e_idx in range(n_edges):
        for color in range(1, n_colors):
            c_obj[m_idx(e_idx, color)] = -1.0  # minimize -sum

    bounds = [(0.0, 1.0)] * n_vars
    if verbose:
        print(f"LP: {n_vars} vars, {n_eq} eq, {row_count} ub", flush=True)

    t0 = time.time()
    result = linprog(c_obj, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                     bounds=bounds, method='highs')
    elapsed = time.time() - t0

    if result.status != 0:
        print(f"LP failed: {result.message}", flush=True)
        return None

    lp_obj = -result.fun
    print(f"\nLP value: {lp_obj:.4f} / {n_edges} = {lp_obj/n_edges*100:.1f}%", flush=True)
    print(f"Elapsed: {elapsed:.2f}s", flush=True)

    return {"lp_obj": float(lp_obj), "n_edges": n_edges, "elapsed_s": elapsed,
            "n_vars": n_vars, "n_eq": n_eq, "n_ub": row_count}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", type=str, required=True)
    args = ap.parse_args()
    csv_path = Path(args.puzzle)
    size, pieces = load_puzzle_csv(csv_path)
    print(f"Puzzle: {csv_path.name}  size={size}×{size}  pieces={len(pieces)}", flush=True)
    res = build_and_solve_lp(size, pieces, verbose=True)
    out_path = csv_path.parent / f"prism_lp_{csv_path.stem}.json"
    with open(out_path, "w") as f:
        json.dump(res, f, indent=2)
    print(f"Wrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
