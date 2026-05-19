#!/usr/bin/env python3
"""V152-T1b — HARMONICS Stage 1 v2: iterative triangle removal.

V152-T1 (stage1_match.py) found a perfect matching with the right
degree sequence but NOT bipartite (7 triangles in H).

Idea: iteratively forbid the matching-edges that participate in
triangles, recompute matching, repeat until H is bipartite.

If the loop converges with |M|=480 + bipartite, we have a strong
candidate for grid-iso.

If the loop fails to find a perfect matching at some iteration,
the underlying demand graph doesn't admit a triangle-free perfect
matching — i.e., HARMONICS is structurally impossible on this piece
set.
"""

from __future__ import annotations
import argparse
import sys
import time
from collections import defaultdict, Counter
from pathlib import Path

import networkx as nx

REPO = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(REPO / "scripts/v152_harmonics"))
from stage1_match import load_canonical_pieces, build_demand_graph


def find_triangle_edges(M_set, H):
    """Given a set of matching edges (as a set of (u,v) pairs) and the
    multigraph H of piece-pairings, find edges that participate in
    triangles in H.simple."""
    H_simple = nx.Graph()
    for u, v in H.edges():
        H_simple.add_edge(u, v)
    # Triangles in H_simple.
    tri_edges = set()
    triangles_list = []
    for n in H_simple.nodes():
        nbrs = list(H_simple.neighbors(n))
        for i in range(len(nbrs)):
            for j in range(i + 1, len(nbrs)):
                if H_simple.has_edge(nbrs[i], nbrs[j]):
                    if n < nbrs[i] and n < nbrs[j]:
                        triangles_list.append((n, nbrs[i], nbrs[j]))
                        tri_edges.add(tuple(sorted([n, nbrs[i]])))
                        tri_edges.add(tuple(sorted([n, nbrs[j]])))
                        tri_edges.add(tuple(sorted([nbrs[i], nbrs[j]])))
    return tri_edges, triangles_list


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", type=str,
                    default=str(REPO.parent / "data/puzzles/size_16_official_eternity.csv"))
    ap.add_argument("--max-iters", type=int, default=20)
    args = ap.parse_args()

    size, pieces = load_canonical_pieces(args.puzzle)
    print(f"[v152-t1b] puzzle: {size}×{size}, {len(pieces)} pieces", flush=True)

    G = build_demand_graph(pieces)
    print(f"[v152-t1b] demand graph: |V|={G.number_of_nodes()} |E|={G.number_of_edges()}", flush=True)

    forbidden_pairs: set = set()
    history = []
    perfect_bipartite = None

    for it in range(args.max_iters):
        # Remove forbidden edges from G_iter.
        G_iter = G.copy()
        # forbidden_pairs is a set of (pid_a, pid_b) tuples (sorted)
        for u in list(G_iter.nodes()):
            for v in list(G_iter.neighbors(u)):
                pa = u[0]; pb = v[0]
                if tuple(sorted([pa, pb])) in forbidden_pairs:
                    G_iter.remove_edge(u, v)

        t0 = time.time()
        M = nx.algorithms.matching.max_weight_matching(G_iter, maxcardinality=True)
        t_match = time.time() - t0
        print(f"\n[iter {it}] forbidden_pairs={len(forbidden_pairs)} |M|={len(M)} (in {t_match:.1f}s)", flush=True)

        if len(M) < 480:
            print(f"[iter {it}] MATCHING NOT PERFECT ({len(M)} < 480). Triangle removal converged to infeasibility.", flush=True)
            break

        # Build H.
        H = nx.MultiGraph()
        for pid in range(len(pieces)):
            H.add_node(pid)
        M_edges = []
        for (pa, sa), (pb, sb) in M:
            H.add_edge(pa, pb, slots=(sa, sb))
            M_edges.append((pa, pb, sa, sb))

        # Check.
        deg_count = Counter([H.degree(n) for n in H.nodes()])
        H_simple = nx.Graph(H)
        bipartite = nx.is_bipartite(H_simple)
        triangles = sum(nx.triangles(H_simple).values()) // 3
        history.append((it, len(forbidden_pairs), bipartite, triangles, dict(deg_count)))
        print(f"[iter {it}] degree dist: {dict(sorted(deg_count.items()))}", flush=True)
        print(f"[iter {it}] bipartite={bipartite} triangles={triangles}", flush=True)

        if bipartite and triangles == 0:
            print(f"\n[v152-t1b] SUCCESS at iter {it}: perfect bipartite matching!", flush=True)
            perfect_bipartite = M_edges
            break

        # Find triangle edges in H; forbid them in next iter.
        tri_edges, tri_list = find_triangle_edges(set((pa, pb) for pa, pb, _, _ in M_edges), H)
        print(f"[iter {it}] triangles found: {len(tri_list)} ({len(tri_edges)} unique edges)", flush=True)
        # Forbid one edge per triangle (the one in M).
        added = 0
        for t in tri_list[:50]:  # cap per iter for speed
            # Find which 2 of the 3 edges are in M.
            in_M = [e for e in [(t[0], t[1]), (t[1], t[2]), (t[0], t[2])]
                    if tuple(sorted(e)) in {tuple(sorted([pa, pb])) for pa, pb, _, _ in M_edges}]
            if in_M:
                e = tuple(sorted(in_M[0]))
                if e not in forbidden_pairs:
                    forbidden_pairs.add(e)
                    added += 1
        print(f"[iter {it}] forbade {added} new piece-pair edges", flush=True)
        if added == 0:
            print(f"[iter {it}] no new forbid edges — stuck. Halt.", flush=True)
            break

    if perfect_bipartite:
        print(f"\n[v152-t1b] FOUND grid-degree + bipartite matching ({len(perfect_bipartite)} pairs).")
        print(f"[v152-t1b] Next: check 4-cycle count, then attempt grid-iso embed (Stage 2).")
    else:
        print(f"\n[v152-t1b] Did not converge. History:")
        for h in history:
            print(f"  iter {h[0]}: forbidden={h[1]} bipartite={h[2]} triangles={h[3]}")


if __name__ == "__main__":
    main()
