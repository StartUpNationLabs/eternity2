#!/usr/bin/env python3
"""V152-T1c — HARMONICS Stage 1 v3: iterative odd-cycle removal.

v2 removed triangles but the matching still had longer odd cycles.
v3 finds ANY odd cycle and forbids one of its edges, iterates.

If we can drive triangles + odd-cycles to 0 while keeping |M|=480,
we have a bipartite perfect matching = strong grid-iso candidate.
"""

from __future__ import annotations
import argparse
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx

REPO = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(REPO / "scripts/v152_harmonics"))
from stage1_match import load_canonical_pieces, build_demand_graph


def find_odd_cycle(H_simple):
    """BFS from each component; if we find an edge between same-color
    vertices, reconstruct the cycle. Returns list of vertices forming
    a cycle, or None if bipartite."""
    color = {}
    for start in H_simple.nodes():
        if start in color:
            continue
        color[start] = 0
        parent = {start: None}
        queue = [start]
        head = 0
        while head < len(queue):
            u = queue[head]; head += 1
            for v in H_simple.neighbors(u):
                if v not in color:
                    color[v] = 1 - color[u]
                    parent[v] = u
                    queue.append(v)
                elif color[v] == color[u]:
                    # Odd cycle: trace back to LCA.
                    # Trace u and v's ancestors.
                    anc_u = []
                    x = u
                    while x is not None:
                        anc_u.append(x); x = parent[x]
                    anc_v = []
                    x = v
                    while x is not None:
                        anc_v.append(x); x = parent[x]
                    set_u = set(anc_u)
                    for i, x in enumerate(anc_v):
                        if x in set_u:
                            lca = x
                            j = anc_u.index(lca)
                            cycle = anc_u[:j + 1] + anc_v[:i][::-1]
                            return cycle
                    # Fallback: just return u,v,parent[u]
                    return [u, v]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", type=str,
                    default=str(REPO.parent / "data/puzzles/size_16_official_eternity.csv"))
    ap.add_argument("--max-iters", type=int, default=200)
    args = ap.parse_args()

    size, pieces = load_canonical_pieces(args.puzzle)
    print(f"[v152-t1c] puzzle: {size}×{size}, {len(pieces)} pieces", flush=True)

    G = build_demand_graph(pieces)
    print(f"[v152-t1c] demand graph: |V|={G.number_of_nodes()} |E|={G.number_of_edges()}", flush=True)

    forbidden_pairs: set = set()
    perfect_bipartite_M = None

    for it in range(args.max_iters):
        G_iter = G.copy()
        for u in list(G_iter.nodes()):
            for v in list(G_iter.neighbors(u)):
                if tuple(sorted([u[0], v[0]])) in forbidden_pairs:
                    G_iter.remove_edge(u, v)

        t0 = time.time()
        M = nx.algorithms.matching.max_weight_matching(G_iter, maxcardinality=True)
        t_match = time.time() - t0
        if len(M) < 480:
            print(f"[iter {it}] |M|={len(M)} < 480: INFEASIBLE under {len(forbidden_pairs)} forbidden pairs.", flush=True)
            print(f"[iter {it}] HARMONICS structurally impossible with this triangle-removal approach.", flush=True)
            break

        H = nx.MultiGraph()
        for pid in range(len(pieces)):
            H.add_node(pid)
        M_edges = []
        for (pa, sa), (pb, sb) in M:
            H.add_edge(pa, pb, slots=(sa, sb))
            M_edges.append((pa, pb, sa, sb))

        H_simple = nx.Graph(H)
        # Quick check.
        deg_count = Counter([H.degree(n) for n in H.nodes()])
        if it == 0 or it % 5 == 0 or it >= 50:
            triangles = sum(nx.triangles(H_simple).values()) // 3
            bipartite = nx.is_bipartite(H_simple)
            print(f"[iter {it}] forbidden={len(forbidden_pairs)} |M|={len(M)} deg={dict(sorted(deg_count.items()))} tri={triangles} bipartite={bipartite} (matched in {t_match:.1f}s)", flush=True)
        else:
            bipartite = nx.is_bipartite(H_simple)

        if bipartite:
            print(f"\n[v152-t1c] SUCCESS at iter {it}: bipartite perfect matching!", flush=True)
            perfect_bipartite_M = M_edges
            triangles = sum(nx.triangles(H_simple).values()) // 3
            print(f"[v152-t1c] triangles: {triangles} (must be 0)", flush=True)
            print(f"[v152-t1c] deg dist: {dict(sorted(deg_count.items()))}", flush=True)
            break

        # Find an odd cycle, forbid one matching-edge on it.
        cycle = find_odd_cycle(H_simple)
        if cycle is None:
            print(f"[iter {it}] no odd cycle found yet graph claims non-bipartite?")
            break
        # Try edges along the cycle that are IN the matching (M_edges).
        M_edge_set = set(tuple(sorted([pa, pb])) for pa, pb, _, _ in M_edges)
        added = 0
        for i in range(len(cycle)):
            u = cycle[i]; v = cycle[(i + 1) % len(cycle)]
            e = tuple(sorted([u, v]))
            if e in M_edge_set and e not in forbidden_pairs:
                forbidden_pairs.add(e)
                added += 1
                break  # forbid just one per iter
        if added == 0:
            # Maybe the cycle had no matching edge (unlikely). Try forbidding non-matching edges.
            for i in range(len(cycle)):
                u = cycle[i]; v = cycle[(i + 1) % len(cycle)]
                e = tuple(sorted([u, v]))
                if e not in forbidden_pairs:
                    forbidden_pairs.add(e)
                    added += 1
                    break
        if added == 0:
            print(f"[iter {it}] no new forbid edges. Halt.", flush=True)
            break

    if perfect_bipartite_M:
        out_path = REPO / "scripts/v152_harmonics/bipartite_matching.json"
        import json
        json.dump([{"pa": pa, "pb": pb, "sa": sa, "sb": sb}
                   for pa, pb, sa, sb in perfect_bipartite_M],
                  open(out_path, "w"))
        print(f"[v152-t1c] saved to {out_path}")
        print(f"[v152-t1c] forbidden pairs at success: {len(forbidden_pairs)}")
        print(f"[v152-t1c] Next: 4-cycle count check + Stage 2 grid-iso embed.")
    else:
        print(f"\n[v152-t1c] failed to find bipartite perfect matching in {it+1} iters.")


if __name__ == "__main__":
    main()
