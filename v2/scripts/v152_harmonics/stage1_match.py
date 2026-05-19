#!/usr/bin/env python3
"""V152-T1 HARMONICS Stage 1 — perfect matching on the demand graph.

For each piece-side (p, s) where the color is non-border, we want to
pair it with another piece-side (q, t) such that:
  - color(p, s) == color(q, t)
  - p != q
  - each (p, s) appears in exactly one pair

This is a perfect matching on the 960-node "interior demand graph"
where edges connect same-color piece-sides on DIFFERENT pieces.

If a perfect matching exists, output it. Then check necessary
grid-embeddability conditions on the induced piece-pairing graph.
"""

from __future__ import annotations
import argparse
import sys
from collections import defaultdict, Counter
from pathlib import Path

import networkx as nx

REPO = Path(__file__).resolve().parents[2]


def load_canonical_pieces(path):
    with open(path) as f:
        lines = [l.strip() for l in f if l.strip()]
    size = int(lines[0])
    pieces = []
    for line in lines[1:]:
        parts = line.split(",")
        cw = lambda s: (lambda v: 0 if v == 65535 else v)(int(s.strip(), 2))
        t, r, b, l = cw(parts[0]), cw(parts[1]), cw(parts[2]), cw(parts[3])
        pieces.append((t, r, b, l))
    return size, pieces


SIDE_NAMES = ["N", "E", "S", "W"]


def build_demand_graph(pieces):
    """Build undirected graph G:
      - Nodes: (pid, side_idx) for each non-border side of each piece.
      - Edges: ((p, s1), (q, s2)) if p != q and color(p, s1) == color(q, s2).

    No rotation is considered yet: we use the piece's CANONICAL side
    indexing (N=0, E=1, S=2, W=3). Rotation choice is part of Stage 2.

    Wait — that's not quite right. If we rotate a piece, the "N" side
    moves to other positions. To match colors regardless of rotation:
    the (piece, side) node IS rotation-dependent. We need to either:
    (a) include rotation in the node identity (1024 nodes × 4 rotations
        = 4096 nodes, but only one rotation per piece is chosen),
    OR
    (b) work in the rotation-quotient space: nodes are (piece, color),
        with multiplicity = # times that color appears on that piece.

    Option (b) is cleaner. A piece with colors (c1, c2, c3, c4) has 4
    color-slots; we don't care which is N/E/S/W until we pick a
    rotation. The matching pairs up COLOR-SLOTS, not sided-slots.
    """
    G = nx.Graph()
    # Nodes: (pid, slot_index). slot_index 0..3 indicates the position
    # in piece.sides list. Color = pieces[pid][slot_index].
    # Border (color 0) slots are EXCLUDED from the matching.
    for pid, piece in enumerate(pieces):
        for s_idx, c in enumerate(piece):
            if c == 0:
                continue  # border
            G.add_node((pid, s_idx), color=c)

    # Edges: same-color same-piece-different-slot? No - matching is
    # between DIFFERENT pieces. Different pieces, same color.
    nodes_by_color = defaultdict(list)
    for n, attr in G.nodes(data=True):
        nodes_by_color[attr["color"]].append(n)
    for c, nodes in nodes_by_color.items():
        # Edges among all pairs.
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                pa, sa = nodes[i]
                pb, sb = nodes[j]
                if pa != pb:
                    G.add_edge(nodes[i], nodes[j])
    return G


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", type=str,
                    default=str(REPO.parent / "data/puzzles/size_16_official_eternity.csv"))
    args = ap.parse_args()
    size, pieces = load_canonical_pieces(args.puzzle)
    print(f"[v152-t1] puzzle: {size}×{size}, {len(pieces)} pieces", flush=True)

    # Color-occurrence summary.
    counts = Counter()
    for p in pieces:
        for c in p:
            if c != 0:
                counts[c] += 1
    print(f"[v152-t1] color counts:")
    for c, n in sorted(counts.items()):
        print(f"  color {c}: {n} occurrences {'(' + ('rare' if c <= 5 else 'med' if c <= 10 else 'common') + ')'}")

    total_interior = sum(counts.values())
    print(f"[v152-t1] total non-border sides: {total_interior} (expect 960)")
    assert total_interior == 960, f"expected 960 got {total_interior}"

    print(f"[v152-t1] building demand graph (1024-64 = {total_interior} nodes)...", flush=True)
    G = build_demand_graph(pieces)
    print(f"[v152-t1] |V|={G.number_of_nodes()} |E|={G.number_of_edges()}", flush=True)

    # Compute maximum matching (NOT maximum-weight; we just want perfect).
    print(f"[v152-t1] computing maximum matching (this may take seconds)...", flush=True)
    M = nx.algorithms.matching.max_weight_matching(G, maxcardinality=True)
    print(f"[v152-t1] |M| = {len(M)} pairs")
    print(f"[v152-t1] perfect matching? {len(M) * 2 == G.number_of_nodes()}")
    matched_nodes = set()
    for u, v in M:
        matched_nodes.add(u); matched_nodes.add(v)
    unmatched = G.number_of_nodes() - len(matched_nodes)
    print(f"[v152-t1] unmatched nodes: {unmatched}")

    if unmatched > 0:
        print(f"[v152-t1] WARN: matching is not perfect; {unmatched} unmatched slots", flush=True)

    # Build induced piece-pairing graph H.
    print(f"[v152-t1] building induced piece-pairing graph H...", flush=True)
    H = nx.MultiGraph()
    for pid in range(len(pieces)):
        H.add_node(pid)
    for (pa, sa), (pb, sb) in M:
        H.add_edge(pa, pb, slots=(sa, sb))
    print(f"[v152-t1] |V(H)|={H.number_of_nodes()} |E(H)|={H.number_of_edges()}")

    # Degree sequence.
    deg_seq = sorted([H.degree(n) for n in H.nodes()], reverse=True)
    print(f"[v152-t1] degree sequence: max={deg_seq[0]} min={deg_seq[-1]}")
    deg_count = Counter(deg_seq)
    print(f"[v152-t1] degree distribution:")
    for d, c in sorted(deg_count.items()):
        print(f"  degree {d}: {c} pieces")

    # Expected grid-graph degree sequence:
    #   4 corners (degree 2), 56 edge-pieces (degree 3), 196 interior (degree 4)
    # PLUS border-perimeter sides: 4 corners have 2 each, 56 edges have 1 each
    # = 8 + 56 = 64 border sides total. So in the piece-side matching, those
    # 64 border sides are NOT in the matching (we excluded them).
    # Therefore the degree of each piece in H = its non-border-side count.
    # Corners: 2 non-border sides; edges: 3; interior: 4.
    expected = {2: 4, 3: 56, 4: 196}
    match_ok = all(deg_count.get(d, 0) == c for d, c in expected.items())
    print(f"[v152-t1] degree-sequence matches grid? {match_ok}")

    if match_ok:
        print(f"[v152-t1] GRID-DEGREE-OK: matching is grid-degree-compatible.")
        print(f"[v152-t1] Next step: check bipartite + 4-cycle count.")

        # Bipartite check (grid is bipartite).
        # H may have multi-edges; convert to simple graph for bipartite test.
        H_simple = nx.Graph()
        for u, v in H.edges():
            H_simple.add_edge(u, v)
        bipartite = nx.is_bipartite(H_simple)
        print(f"[v152-t1] H_simple bipartite? {bipartite}")

        # 4-cycle count.
        # Use NetworkX's cycle_basis or count via square root of trace(A^4).
        # For 256-node graph this is feasible.
        # Cheap heuristic: count triangles (should be 0 in grid).
        triangles = sum(nx.triangles(H_simple).values()) // 3
        print(f"[v152-t1] triangles in H_simple: {triangles} (expect 0 in grid)")
    else:
        print(f"[v152-t1] degree sequence MISMATCH — this matching is not grid-embeddable.")
        print(f"[v152-t1] Stage 1 must enumerate alternative matchings.")


if __name__ == "__main__":
    main()
