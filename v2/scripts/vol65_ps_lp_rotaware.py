#!/usr/bin/env python3
"""Vol-65 day 2 — LP on rotation-aware PS-graph.

Solves max-cardinality matching on the rotation-aware PS-graph:
- Variables: x_e in [0, 1] for each edge e
- Constraint: each non-border piece-side in at most one matched edge
- Objective: maximize sum of x_e

Optionally enforces "piece-budget": each piece has exactly 4 non-border
sides; in a valid assembly, ALL 4 must be matched (interior pieces)
or 3 (edge pieces) or 2 (corner pieces). We can add this as a
LOWER bound on the per-piece matched-side count.

Two scenarios:
- baseline:    side-coverage <= 1 per node, no piece-budget
- with-budget: each interior piece's 4 sides MUST have sum_matched >= 4
"""

import json
import sys
import time

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix, vstack as sp_vstack


def build_lp(g, with_budget=False):
    n_pieces = g["n_pieces"]
    edges = g["edges"]  # [u, v, color] where u, v are p*4 + s
    n_edges = len(edges)
    piece_kinds = g["piece_kinds"]  # 'corner' | 'edge' | 'interior'

    # 1024 total side-nodes; some have color 0 (border) — we EXCLUDE their constraints
    # but the edge list already only includes non-border edges, so border-color
    # nodes will simply have 0 edges incident.
    # We use indices 0..1023 for side-nodes (p*4+s).

    c_obj = -np.ones(n_edges)

    # Side-coverage rows: for each side-node (p, s), sum of incident x_e <= 1
    A_side = lil_matrix((n_pieces * 4, n_edges))
    for e_idx, (u, v, _col) in enumerate(edges):
        A_side[u, e_idx] = 1
        A_side[v, e_idx] = 1
    A_side = A_side.tocsr()
    b_side = np.ones(n_pieces * 4)

    A_ub = A_side
    b_ub = b_side

    if with_budget:
        # Per-piece budget: interior piece must have sum of edges adjacent
        # to its 4 sides >= 4 (each side matched). For edges pieces >= 3 (border-side unmatched).
        # For corners >= 2.
        # Reformulate as: -sum_e(adjacent to piece p) <= -required.
        A_budget = lil_matrix((n_pieces, n_edges))
        b_budget = np.zeros(n_pieces)
        for p in range(n_pieces):
            required = {"interior": 4, "edge": 3, "corner": 2}[piece_kinds[p]]
            b_budget[p] = -required
            # For each edge adjacent to piece p, add -1 (because each edge
            # uses 1 side of piece p; the sum over edges incident on any of p's
            # 4 sides equals piece-p's matched-side count).
        # Build coefficients
        for e_idx, (u, v, _col) in enumerate(edges):
            pu, _ = divmod(u, 4)
            pv, _ = divmod(v, 4)
            A_budget[pu, e_idx] = -1
            A_budget[pv, e_idx] = -1
        A_budget = A_budget.tocsr()
        A_ub = sp_vstack([A_ub, A_budget]).tocsr()
        b_ub = np.concatenate([b_ub, b_budget])

    bounds = [(0, 1)] * n_edges
    return c_obj, A_ub, b_ub, bounds


def main():
    with open("output/vol-65/ps_graph_rotaware.json") as f:
        g = json.load(f)

    print(f"PS-graph (rotation-aware):")
    print(f"  n_pieces: {g['n_pieces']}")
    print(f"  n_edges:  {g['n_edges']}")
    print()

    # Scenario 1: baseline
    print(f"=== Scenario 1: baseline (side-coverage only) ===")
    t = time.time()
    c, Aub, bub, bounds = build_lp(g, with_budget=False)
    print(f"  LP build: {time.time()-t:.2f}s, vars={len(c)}, rows={Aub.shape[0]}")
    t = time.time()
    res = linprog(c, A_ub=Aub, b_ub=bub, bounds=bounds, method="highs")
    print(f"  LP solve: {time.time()-t:.2f}s")
    if res.success:
        ub = -res.fun
        x = res.x
        frac = sum(1 for v in x if 0.001 < v < 0.999)
        intone = sum(1 for v in x if v > 0.999)
        print(f"  LP UB: {ub:.2f}")
        print(f"  Solution: {intone} integer-1, {frac} fractional")
        if ub >= 480:
            print(f"  ✓ Rotation absorbs the canonical-orientation 307 bound.")
        else:
            print(f"  ! LP says LESS than 480 achievable: {int(ub)} <= 480")
    else:
        print(f"  FAILED: {res.message}")

    # Scenario 2: with piece-budget
    print()
    print(f"=== Scenario 2: with piece-budget (interior=4, edge=3, corner=2) ===")
    t = time.time()
    c, Aub, bub, bounds = build_lp(g, with_budget=True)
    print(f"  LP build: {time.time()-t:.2f}s, vars={len(c)}, rows={Aub.shape[0]}")
    t = time.time()
    res = linprog(c, A_ub=Aub, b_ub=bub, bounds=bounds, method="highs")
    print(f"  LP solve: {time.time()-t:.2f}s")
    if res.success:
        ub = -res.fun
        x = res.x
        frac = sum(1 for v in x if 0.001 < v < 0.999)
        intone = sum(1 for v in x if v > 0.999)
        print(f"  LP UB: {ub:.2f}")
        print(f"  Solution: {intone} integer-1, {frac} fractional")
    else:
        print(f"  FAILED: {res.message}")
        print(f"  → If infeasible, piece-budget contradicts side-coverage,")
        print(f"    proving NO 480-match assembly exists.")


if __name__ == "__main__":
    main()
