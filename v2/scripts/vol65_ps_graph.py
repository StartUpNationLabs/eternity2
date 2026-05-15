#!/usr/bin/env python3
"""Vol-65 — build the Piece-Side-Matching graph for canonical E2.

Per `vault/concepts/piece-side-matching.md`:

Nodes: piece-sides (p, s) for p in [0, 256) and s in {N, E, S, W}.
       1024 nodes total.
Edges: (p1, s1) — (p2, s2) with col(p1, s1) = col(p2, s2)
       AND (s1, s2) ∈ {(N, S), (S, N), (E, W), (W, E)}.

Reads the canonical puzzle CSV and outputs:
- exact |E(G_PS)|
- per-node degree distribution
- adjacency dump as JSON (for downstream LP)
"""

import collections
import csv
import json
import sys
from pathlib import Path

PUZZLE_CSV = "../data/puzzles/size_16_official_eternity.csv"


def load_pieces(csv_path):
    """Return list of pieces as (id, [N, E, S, W color]) tuples.

    Canonical CSV format (per puzzle-io/src/lib.rs):
      line 1: board size N
      lines 2..N²+1: top,right,bottom,left,x,y,rotation
      colors are 16-bit zero-padded binary strings.
      65535 (1111111111111111) = BORDER color.
    """
    pieces = []
    BORDER_RAW = 65535
    BORDER_ENCODED = 0  # we use 0 as the border-color sentinel here
    with open(csv_path) as f:
        size = int(f.readline().strip())
        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            # parts[0..3] = top, right, bottom, left as 16-bit binary
            def col(s):
                v = int(s.strip(), 2)
                return BORDER_ENCODED if v == BORDER_RAW else v
            top = col(parts[0])
            right = col(parts[1])
            bottom = col(parts[2])
            left = col(parts[3])
            # piece id = idx (0-based). N=top, E=right, S=bottom, W=left
            pieces.append((idx, [top, right, bottom, left]))
    return pieces


def main():
    pieces = load_pieces(PUZZLE_CSV)
    n_pieces = len(pieces)
    print(f"Loaded {n_pieces} pieces from {PUZZLE_CSV}")

    # Nodes: list of (p, s) with s in {0=N, 1=E, 2=S, 3=W}
    # Build inverted index: color -> list of (p, s)
    side_names = ["N", "E", "S", "W"]
    color_to_nodes = collections.defaultdict(list)
    for p, edges in pieces:
        for s, col in enumerate(edges):
            color_to_nodes[col].append((p, s))

    print(f"Total nodes (piece-sides): {n_pieces * 4}")
    print(f"Distinct colors: {len(color_to_nodes)}")
    print(f"Color cardinalities:")
    for c, nodes in sorted(color_to_nodes.items()):
        print(f"  color {c:2d}: {len(nodes)} sides")

    # Edges: (p1, s1) - (p2, s2) iff color matches AND (s1, s2) facing pair
    # Facing pairs: (N, S), (S, N), (E, W), (W, E)
    # Equivalently: s1 + s2 ∈ {2, 4} where N=0, E=1, S=2, W=3
    # → N(0)+S(2)=2 ✓; E(1)+W(3)=4 ✓; others mixed
    # Simpler: (s1, s2) opposing iff (s1 - s2) % 2 == 0 AND s1 != s2

    facing_pairs = {(0, 2), (2, 0), (1, 3), (3, 1)}
    edges = []
    edges_set = set()  # canonical (u < v) representation
    for col, nodes in color_to_nodes.items():
        for i, (p1, s1) in enumerate(nodes):
            for j, (p2, s2) in enumerate(nodes):
                if i == j:
                    continue
                if p1 == p2:
                    continue  # can't pair piece with itself
                if (s1, s2) not in facing_pairs:
                    continue
                u, v = sorted([(p1, s1), (p2, s2)])
                if (u, v) in edges_set:
                    continue
                edges_set.add((u, v))
                edges.append((u, v, col))

    print()
    print(f"Total edges in G_PS: {len(edges)}")

    # Per-node degree
    degrees = collections.defaultdict(int)
    for u, v, _ in edges:
        degrees[u] += 1
        degrees[v] += 1
    degree_dist = collections.Counter(degrees.values())
    print(f"Degree distribution:")
    for d, n in sorted(degree_dist.items()):
        print(f"  deg {d:2d}: {n:4d} nodes")

    # All nodes covered?
    all_nodes = set((p, s) for p in range(n_pieces) for s in range(4))
    isolated = all_nodes - set(degrees.keys())
    print(f"Isolated nodes (no compatible partner): {len(isolated)}")
    if isolated:
        print(f"  Examples: {list(isolated)[:5]}")
        # Group by color
        iso_by_color = collections.Counter()
        for p, s in isolated:
            iso_by_color[pieces[p][1][s]] += 1
        print(f"  By color: {dict(iso_by_color)}")

    # Sanity: count edges by color
    color_edge_count = collections.Counter()
    for _, _, col in edges:
        color_edge_count[col] += 1
    print()
    print("Edges per color (top 5 and bottom 5):")
    sorted_colors = sorted(color_edge_count.items(), key=lambda x: -x[1])
    for c, n in sorted_colors[:5]:
        print(f"  color {c:2d}: {n:5d} edges (between {len(color_to_nodes[c])} nodes)")
    for c, n in sorted_colors[-5:]:
        print(f"  color {c:2d}: {n:5d} edges (between {len(color_to_nodes[c])} nodes)")

    # Save adjacency dump for LP downstream
    out_path = "output/vol-65/ps_graph.json"
    Path("output/vol-65").mkdir(parents=True, exist_ok=True)
    out = {
        "n_pieces": n_pieces,
        "n_nodes": n_pieces * 4,
        "n_edges": len(edges),
        "color_cardinalities": {c: len(ns) for c, ns in color_to_nodes.items()},
        "isolated_nodes": [list(n) for n in isolated],
        "color_edge_counts": dict(color_edge_count),
        # edges stored as (p1*4+s1, p2*4+s2, color) for compactness
        "edges": [
            [u[0] * 4 + u[1], v[0] * 4 + v[1], col]
            for u, v, col in edges
        ],
    }
    with open(out_path, "w") as f:
        json.dump(out, f)
    print(f"\nWrote {out_path} ({Path(out_path).stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
