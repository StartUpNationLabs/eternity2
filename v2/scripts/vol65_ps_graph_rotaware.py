#!/usr/bin/env python3
"""Vol-65 — Build the ROTATION-AWARE Piece-Side-Matching graph.

In the rotation-aware view, any piece-side can face any world-direction
(N/E/S/W) under appropriate rotation. So the PS-graph edges are between
two piece-sides with the SAME color, on DIFFERENT pieces — regardless
of their canonical side-labels.

This gives a much larger candidate edge set than the canonical-fixed
version (5,206 edges → much more). The matching bound here should
approach 480 since rotation absorbs the direction asymmetry.

The interesting constraints to add layer-by-layer:
1. Side-coverage: each piece-side in ≤ 1 matching edge.
2. Piece-budget: each piece has ≤ 4 matched sides (its 4 piece-sides).
3. Frame respect: border pieces only on perimeter, corners on corners.
4. Piece-rotation consistency: 4 matched sides of one piece must be
   a rotation of (N,E,S,W) (each direction used exactly once).

Day 2 just does (1)+(2). Day 3 adds (3). Day 4 adds (4).
"""

import collections
import csv
import json
import sys
from pathlib import Path

PUZZLE_CSV = "../data/puzzles/size_16_official_eternity.csv"


def load_pieces(csv_path):
    """Return list of pieces as (id, [N, E, S, W color]) tuples."""
    BORDER_RAW = 65535
    pieces = []
    with open(csv_path) as f:
        size = int(f.readline().strip())
        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            def col(s):
                v = int(s.strip(), 2)
                return 0 if v == BORDER_RAW else v
            top = col(parts[0])
            right = col(parts[1])
            bottom = col(parts[2])
            left = col(parts[3])
            pieces.append((idx, [top, right, bottom, left]))
    return pieces


def piece_kind(edges):
    """Return 'corner', 'edge', or 'interior' based on # border-color sides."""
    n_border = sum(1 for c in edges if c == 0)
    if n_border == 2:
        return "corner"
    if n_border == 1:
        return "edge"
    if n_border == 0:
        return "interior"
    raise ValueError(f"piece has {n_border} border sides; unexpected")


def main():
    pieces = load_pieces(PUZZLE_CSV)
    n_pieces = len(pieces)

    # Classify pieces.
    kinds = collections.Counter()
    piece_kinds = []
    for p, edges in pieces:
        k = piece_kind(edges)
        kinds[k] += 1
        piece_kinds.append(k)
    print(f"Pieces: {n_pieces}")
    print(f"  corners: {kinds['corner']}")
    print(f"  edges:   {kinds['edge']}")
    print(f"  interior:{kinds['interior']}")

    # Rotation-aware PS-graph: nodes = (piece, side) where side is the
    # canonical side label (N/E/S/W as 0/1/2/3) on the piece. Edges
    # connect two (p1, s1) ≠ (p2, s2) on different pieces if colors
    # match.
    side_color = {}  # (p, s) -> color
    for p, edges in pieces:
        for s in range(4):
            side_color[(p, s)] = edges[s]

    # Build inverted index: color -> list of (p, s)
    color_to_nodes = collections.defaultdict(list)
    for (p, s), c in side_color.items():
        color_to_nodes[c].append((p, s))

    # Edges: same color, different pieces. NO direction constraint.
    edges = []
    edges_set = set()
    for col, nodes in color_to_nodes.items():
        if col == 0:
            # Border color: 64 sides (60 edge-pieces + 4 corners × 2).
            # In an assembled board border-color sides face the FRAME,
            # not another piece. So border-color is NOT matched in M.
            # Skip these.
            continue
        for i, (p1, s1) in enumerate(nodes):
            for j in range(i + 1, len(nodes)):
                p2, s2 = nodes[j]
                if p1 == p2:
                    continue
                u, v = ((p1, s1), (p2, s2)) if (p1, s1) < (p2, s2) else ((p2, s2), (p1, s1))
                if (u, v) in edges_set:
                    continue
                edges_set.add((u, v))
                edges.append((u, v, col))

    n_edges = len(edges)
    print(f"\nRotation-aware PS-graph:")
    print(f"  nodes: {n_pieces * 4} (incl border-color sides — to be excluded in matching)")
    nonborder_nodes = sum(1 for c in side_color.values() if c != 0)
    print(f"  non-border nodes: {nonborder_nodes}")
    print(f"  edges: {n_edges}  (vs 5,206 in canonical-orientation)")

    # Per-node degree (non-border)
    degrees = collections.defaultdict(int)
    for u, v, _ in edges:
        degrees[u] += 1
        degrees[v] += 1
    nonzero = [d for d in degrees.values() if d > 0]
    print(f"  degree min/median/max: {min(nonzero)}/{sorted(nonzero)[len(nonzero)//2]}/{max(nonzero)}")

    # Total interior-edges in the assembled 16×16 = 2*15*16 = 480
    print(f"\nTotal interior edges in 16x16: {2 * 15 * 16}")
    print(f"Total piece-sides needed in matching: {2 * 480} = 960")
    print(f"Available non-border piece-sides: {nonborder_nodes}")
    # The 960 vs 192 (256 interior + 60 edge + 4 corner pieces' non-border sides)
    # 4 corner pieces × 2 non-border sides = 8
    # 60 edge pieces × 3 non-border sides = 180
    # 196 interior pieces × 4 non-border sides = 784
    # Total = 8 + 180 + 784 = 972. Close to 960 (480 edges × 2 sides).
    # Off by ~12 (60 edge pieces are placed with 1 non-border side facing
    # the frame, not another piece). Let me recompute:
    # 60 edge pieces × 1 frame-facing non-border side = 60 not matched
    # Available for matching: 972 - 60 = 912? Hmm.
    # Actually let me reconsider:
    # - 4 corners: 2 non-border sides each = 8 sides, all interior-facing.
    # - 60 edges: 3 non-border sides, but the one OPPOSITE the border-side
    #   faces a piece (interior cell); the two adjacent ones face the
    #   border-piece neighbors. So all 3 non-border sides ARE interior-facing.
    #   → 60 × 3 = 180.
    # - 196 interior: 4 non-border sides, all face other pieces.
    #   → 196 × 4 = 784.
    # Total non-border sides used in matching = 8 + 180 + 784 = 972.
    # 480 edges × 2 sides = 960 used.
    # Diff = 12. Probably the corner-piece "outward edges" — each corner
    # has 2 border-color sides AND 2 non-border, all interior-facing.
    # Hmm, 4 corners × 2 non-border = 8, no diff there.
    # Maybe I miscounted edge pieces: actually 60 edge piece positions
    # in a 16x16 (perimeter minus corners = 4(16-2) = 56, plus 4 corners =
    # 60). So 4 corners + 56 edges + 196 interior = 256 pieces.
    # 4*2 + 56*3 + 196*4 = 8 + 168 + 784 = 960. Matches!
    print(f"\nExpected non-border-side count from piece geometry:")
    print(f"  4 corners * 2 + 56 edges * 3 + 196 interior * 4 = {4*2 + 56*3 + 196*4}")
    # Save
    out_path = "output/vol-65/ps_graph_rotaware.json"
    Path("output/vol-65").mkdir(parents=True, exist_ok=True)
    out = {
        "n_pieces": n_pieces,
        "n_nodes_total": n_pieces * 4,
        "n_nodes_nonborder": nonborder_nodes,
        "n_edges": n_edges,
        "piece_kinds": piece_kinds,
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
