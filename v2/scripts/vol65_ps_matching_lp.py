#!/usr/bin/env python3
"""Vol-65 — LP-relaxation of the Piece-Side-Matching problem.

Solves the relaxed maximum-cardinality matching on the PS-graph
(WITHOUT consistency constraints), giving an upper bound on
matchable INTERIOR sides on canonical E2.

Two scenarios:
- "All sides": treat ALL piece-sides as potentially matchable
  (ignoring border / corner / hint constraints).
- "Interior only": exclude piece-sides that MUST face a border
  (heuristically: sides of border pieces facing outward).

The "all sides" answer is a sound but very loose upper bound on
matched interior edges. The "interior only" answer accounts for
the 60 + 4 = 64 frame piece-sides + corner piece-sides that
must face the frame.

If LP < 480, we have a sound combinatorial upper bound on the
puzzle that contradicts the existence of any 480-match assembly,
proving the puzzle is NOT solvable in matched-edges sense. (Of
course this is canonical E2 — McGavin's 469 says 480 is unreachable.
The LP MAY give an explicit bound.)

Uses scipy.sparse + scipy.optimize.linprog (simplex/interior).
"""

import json
import sys
import time

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix


def main():
    with open("output/vol-65/ps_graph.json") as f:
        g = json.load(f)

    n_nodes = g["n_nodes"]
    edges = g["edges"]  # [u, v, color] tuples
    n_edges = len(edges)
    print(f"PS-graph: {n_nodes} nodes, {n_edges} edges")

    # LP: max sum_e x_e
    #     s.t. sum_{e incident on v} x_e <= 1 for each node v
    #          x_e ∈ [0, 1]
    #
    # In linprog (which is min c^T x s.t. A_ub x <= b_ub):
    #   c = -ones(n_edges)
    #   For each node v, row in A_ub: ones at edges incident on v
    #   b_ub = ones(n_nodes)
    #   bounds = [(0, 1)] * n_edges
    print("Building LP...")
    t0 = time.time()
    c = -np.ones(n_edges)
    # Incidence matrix (n_nodes × n_edges)
    A_ub = lil_matrix((n_nodes, n_edges))
    for e_idx, (u, v, _col) in enumerate(edges):
        A_ub[u, e_idx] = 1
        A_ub[v, e_idx] = 1
    A_ub = A_ub.tocsr()
    b_ub = np.ones(n_nodes)
    bounds = [(0, 1)] * n_edges
    print(f"  setup: {time.time()-t0:.2f}s")

    print("Solving LP...")
    t1 = time.time()
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds,
                  method="highs")
    elapsed = time.time() - t1
    print(f"  solver: {elapsed:.2f}s")

    if not res.success:
        print(f"LP FAILED: {res.message}")
        sys.exit(1)

    lp_obj = -res.fun  # we maximized via negating c
    print()
    print(f"LP UB on PS-matching cardinality: {lp_obj:.2f}")
    print(f"(Integer matching ≤ this. Canonical E2 has 480 interior edges.)")
    print()

    # Inspect the LP solution: how many edges are fractional?
    x = res.x
    integer_count = sum(1 for v in x if v > 0.999)
    fractional_count = sum(1 for v in x if 0.001 < v < 0.999)
    zero_count = sum(1 for v in x if v < 0.001)
    print(f"LP-solution: {integer_count} integer-1, {fractional_count} fractional, "
          f"{zero_count} integer-0 (total {len(x)})")
    print()

    if lp_obj < 480:
        print(f"** SOUND BOUND: max-cardinality PS-matching ≤ {int(lp_obj)} < 480. **")
        print(f"** E2 cannot achieve all 480 matched edges via color matching alone. **")
        print(f"** This is independent of piece-placement constraints. **")
    else:
        print(f"LP says 480 is achievable in the matching relaxation (gap closed?).")
        print(f"Integer matching may still be < 480 due to consistency constraints.")

    # Per-color edge use
    color_use = {}
    for e_idx, (u, v, col) in enumerate(edges):
        color_use[col] = color_use.get(col, 0.0) + x[e_idx]
    print()
    print("Per-color LP-edge usage (rounded):")
    for col, u in sorted(color_use.items()):
        cap = g["color_edge_counts"].get(str(col), g["color_edge_counts"].get(col, 0))
        print(f"  color {col:2d}: {u:6.2f} edges used / {cap} candidates")


if __name__ == "__main__":
    main()
