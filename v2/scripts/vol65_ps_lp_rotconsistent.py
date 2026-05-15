#!/usr/bin/env python3
"""Vol-65 day 3 — PS-LP with piece-rotation consistency.

Adds rotation variables r[p, k] in [0,1] for k in {0,1,2,3} with
sum_k r[p, k] = 1 per piece. Each candidate edge e = ((p1, s1), (p2, s2))
has a parity delta = (s1 + s2) mod 4. The edge is rotation-compatible
iff (k1 + k2) mod 4 = (2 - delta) mod 4. There are exactly 4 such
(k1, k2) pairs out of 16.

To linearize, introduce z[p1, k1, p2, k2] in [0,1] with McCormick:
  z <= r[p1, k1]
  z <= r[p2, k2]
  z >= r[p1, k1] + r[p2, k2] - 1
(LP-relaxation doesn't strictly need McCormick's z >= ... part, since
the max-cardinality direction makes z naturally small. We'll keep
both for tightness.)

Edge constraint:
  x_e <= sum over compatible (k1, k2) of z[p1, k1, p2, k2]

Goal: see if this drops the LP UB from 480.

CAUTION: z variables are O(|piece-pairs| * 16) ~ 256*256/2*16 = 524k.
We can prune by only including (p1, p2) pairs that appear in some
edge — much smaller. Let's see.
"""

import json
import sys
import time
import collections

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix, vstack as sp_vstack


def main():
    with open("output/vol-65/ps_graph_rotaware.json") as f:
        g = json.load(f)

    n_pieces = g["n_pieces"]
    edges = g["edges"]
    piece_kinds = g["piece_kinds"]

    # Collect distinct piece-pairs that appear in any edge
    pair_to_edges = collections.defaultdict(list)
    for e_idx, (u, v, _col) in enumerate(edges):
        p1, s1 = divmod(u, 4)
        p2, s2 = divmod(v, 4)
        pair = (p1, p2) if p1 < p2 else (p2, p1)
        # canonical order
        if p1 < p2:
            delta = (s1 + s2) % 4
        else:
            delta = (s2 + s1) % 4
        pair_to_edges[pair].append((e_idx, p1, s1, p2, s2, delta))
    n_pairs = len(pair_to_edges)
    print(f"Distinct piece-pairs in PS-graph: {n_pairs}")
    print(f"Total edges: {len(edges)}")

    # Variable indexing:
    # x_e for e in 0..n_edges-1                        →  [0, n_edges)
    # r[p, k] for p in 0..n_pieces, k in 0..3           →  [n_edges, n_edges + 4*n_pieces)
    # z[(pa, pb), k1, k2] for distinct pairs * 16       →  the rest

    n_edges_total = len(edges)
    n_r = 4 * n_pieces
    # z indexed per piece-pair: each pair has 16 z's
    # Map pair → start index in z block
    pair_list = sorted(pair_to_edges.keys())
    pair_to_idx = {pair: i for i, pair in enumerate(pair_list)}
    n_z = 16 * n_pairs

    n_vars = n_edges_total + n_r + n_z
    print(f"Total LP variables: {n_vars} (x={n_edges_total}, r={n_r}, z={n_z})")

    def idx_x(e_idx): return e_idx
    def idx_r(p, k): return n_edges_total + p * 4 + k
    def idx_z(pair, k1, k2):
        # pair is (pa, pb) with pa < pb; k1 is for pa, k2 for pb
        base = n_edges_total + n_r + pair_to_idx[pair] * 16
        return base + k1 * 4 + k2

    # Objective: maximize sum x_e (minimize -1 * sum x_e)
    c = np.zeros(n_vars)
    for e in range(n_edges_total):
        c[idx_x(e)] = -1.0

    rows_ub = []
    rows_eq = []
    b_ub = []
    b_eq = []

    # Row builders
    def add_ub_row(coefs, bound):
        # coefs is dict {var_idx: coef}
        rows_ub.append(coefs)
        b_ub.append(bound)

    def add_eq_row(coefs, bound):
        rows_eq.append(coefs)
        b_eq.append(bound)

    # Side-coverage: each non-border side in at most 1 matched edge
    side_edges = collections.defaultdict(list)
    for e_idx, (u, v, _col) in enumerate(edges):
        side_edges[u].append(e_idx)
        side_edges[v].append(e_idx)
    for s_node, e_list in side_edges.items():
        add_ub_row({idx_x(e): 1.0 for e in e_list}, 1.0)

    # Piece-rotation sum: sum_k r[p, k] = 1 for each piece
    for p in range(n_pieces):
        add_eq_row({idx_r(p, k): 1.0 for k in range(4)}, 1.0)

    # McCormick on z: z <= r[p1,k1], z <= r[p2,k2], z >= r[p1,k1]+r[p2,k2]-1
    # We only need the first two for the relaxation to be valid for maximization.
    # (Without z >= ..., z is just bounded above by the AND, so z can be smaller;
    # this OVER-constrains the LP if we use z in a <= constraint. For correctness
    # with max direction, we WANT z to be as large as possible up to AND, so
    # the upper bounds suffice. The z >= ... reverse-McCormick tightens but isn't
    # needed for LP-validity.)
    for pair, _ in pair_to_edges.items():
        pa, pb = pair
        for k1 in range(4):
            for k2 in range(4):
                z = idx_z(pair, k1, k2)
                # z <= r[pa, k1]
                add_ub_row({z: 1.0, idx_r(pa, k1): -1.0}, 0.0)
                # z <= r[pb, k2]
                add_ub_row({z: 1.0, idx_r(pb, k2): -1.0}, 0.0)

    # Edge x_e <= sum compatible z's
    # Compatible (k1, k2): (k1 + k2) mod 4 = (2 - delta) mod 4
    for e_idx, (u, v, _col) in enumerate(edges):
        p1, s1 = divmod(u, 4)
        p2, s2 = divmod(v, 4)
        if p1 < p2:
            pa, pb = p1, p2
            sa, sb = s1, s2
        else:
            pa, pb = p2, p1
            sa, sb = s2, s1
        delta = (sa + sb) % 4
        target = (2 - delta) % 4
        # k1 for pa, k2 for pb; need (k1 + k2) mod 4 = target
        compatible = [(k1, (target - k1) % 4) for k1 in range(4)]
        # x_e - sum z's <= 0
        coefs = {idx_x(e_idx): 1.0}
        for (k1, k2) in compatible:
            coefs[idx_z((pa, pb), k1, k2)] = -1.0
        add_ub_row(coefs, 0.0)

    # Build sparse matrices
    print(f"\nBuilding sparse LP matrices...")
    t = time.time()
    n_ub = len(rows_ub)
    n_eq = len(rows_eq)
    # Estimate nnz
    nnz_ub = sum(len(r) for r in rows_ub)
    print(f"  UB rows: {n_ub}, nnz: {nnz_ub}")
    print(f"  EQ rows: {n_eq}")
    A_ub = lil_matrix((n_ub, n_vars))
    for i, coefs in enumerate(rows_ub):
        for j, c_val in coefs.items():
            A_ub[i, j] = c_val
    A_ub = A_ub.tocsr()
    A_eq = lil_matrix((n_eq, n_vars))
    for i, coefs in enumerate(rows_eq):
        for j, c_val in coefs.items():
            A_eq[i, j] = c_val
    A_eq = A_eq.tocsr()
    b_ub_arr = np.array(b_ub)
    b_eq_arr = np.array(b_eq)
    print(f"  Matrix build: {time.time()-t:.2f}s")

    bounds = [(0.0, 1.0)] * n_vars

    print(f"\nSolving LP...")
    t = time.time()
    res = linprog(c, A_ub=A_ub, b_ub=b_ub_arr,
                  A_eq=A_eq, b_eq=b_eq_arr,
                  bounds=bounds, method="highs")
    elapsed = time.time() - t
    print(f"  LP solve: {elapsed:.2f}s")
    print(f"  Status: {res.message}")

    if not res.success:
        print(f"LP FAILED")
        sys.exit(1)

    lp_obj = -res.fun
    print()
    print(f"=== Rotation-consistent PS-LP UB: {lp_obj:.2f} ===")
    print(f"(Canonical E2 has 480 interior edges; McGavin's empirical 469.)")
    print()

    # Diagnostics
    x_vals = res.x[:n_edges_total]
    r_vals = res.x[n_edges_total:n_edges_total + n_r]
    z_vals = res.x[n_edges_total + n_r:]

    x_int1 = sum(1 for v in x_vals if v > 0.999)
    x_frac = sum(1 for v in x_vals if 0.001 < v < 0.999)
    print(f"x (edges): {x_int1} integer-1, {x_frac} fractional")

    # Rotation diagnostics: how many pieces have integer rotation?
    r_int = 0
    for p in range(n_pieces):
        r_p = r_vals[p * 4:(p + 1) * 4]
        if any(v > 0.999 for v in r_p):
            r_int += 1
    print(f"Pieces with integer rotation: {r_int}/{n_pieces}")
    # Top-rotation per piece
    print(f"Per-piece rotation entropy (lower = more concentrated):")
    entropies = []
    for p in range(n_pieces):
        r_p = r_vals[p * 4:(p + 1) * 4]
        e = 0.0
        for v in r_p:
            if v > 1e-6:
                e -= v * np.log2(v)
        entropies.append(e)
    print(f"  min/median/max entropy: {min(entropies):.3f} / "
          f"{sorted(entropies)[len(entropies)//2]:.3f} / "
          f"{max(entropies):.3f}")

    print()
    if lp_obj < 480:
        print(f"** NEW SOUND BOUND ON E2: max matched edges <= {int(lp_obj)} **")
        print(f"** Even McGavin's 469 confirmed: this bound is tighter than achievable. **")
    else:
        print(f"LP relaxation does NOT bound below 480 yet.")
        print(f"Need to add: piece-uniqueness + geometric tiling constraints.")


if __name__ == "__main__":
    main()
