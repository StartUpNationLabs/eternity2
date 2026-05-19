#!/usr/bin/env python3
"""V127-T3 — CONCRETION step 3: border-ring Hamiltonian structure.

The 60 border pieces (4 corners + 56 edge pieces) form a cycle around
the perimeter. Each pair of adjacent border-ring positions shares one
edge carrying a non-border color (rare or medium).

For each border piece, identify its "ring-facing" sides — the two sides
that touch other border pieces in the ring. (For corners: 2 ring-facing
sides; for edges: 2 ring-facing sides, one in each direction.)

Then build an undirected graph G where:
- Vertices = border pieces
- Edges: (p, q) with weight = number of (rotation, position) configurations
  where p and q can sit adjacently in the border ring.

Find: which pairs are FORCED to be adjacent (i.e., have a unique partner)?

The output is a piece-pair frequency matrix and a list of pieces that
have UNIQUE adjacency options under the canonical hint constraint.
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from collections import defaultdict, Counter

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


def is_corner(p):
    return sum(1 for s in p if s == 0) == 2


def is_edge_piece(p):
    return sum(1 for s in p if s == 0) == 1


def main():
    csv_path = REPO.parent / "data/puzzles/size_16_official_eternity.csv"
    size, pieces = load_puzzle_csv(csv_path)
    N_pieces = len(pieces)

    corner_ids = [pid for pid, p in enumerate(pieces) if is_corner(p)]
    edge_ids = [pid for pid, p in enumerate(pieces) if is_edge_piece(p)]
    interior_ids = [pid for pid, p in enumerate(pieces) if 0 not in p]
    print(f"Corners: {len(corner_ids)}  Edges: {len(edge_ids)}  Interior: {len(interior_ids)}", flush=True)
    border_ids = corner_ids + edge_ids
    print(f"Border (corner+edge): {len(border_ids)}", flush=True)

    # For each border piece, in each rotation, identify:
    #   - which side is the "outer" border side (color 0)
    #   - the two "ring" sides (left ring-neighbor, right ring-neighbor)
    # The third side (interior-facing) has a non-border color.
    # For corners: TWO outer sides (color 0). One ring-neighbor on each
    # adjacent non-zero side.

    # For each (border_piece, rotation), if the piece's NORTH side is 0
    # (canonical "top of board" border placement), then ring neighbors are E and W.
    # In general, the placement determines which sides face the ring.
    # The simplest tractable analysis: enumerate all (p, r) where p is an edge
    # piece and rotation r places it with N=0 (border facing up).
    # Then its E-side faces the next edge piece (clockwise around the ring), and
    # its W-side faces the previous one.

    # Step 1: For each EDGE piece p, find rotations r where rotate_piece(p, r)[0] == 0
    # (i.e., N is the border). That's the canonical orientation for the TOP row.
    top_orientations = defaultdict(list)  # piece → list of (rot, E_color, W_color)
    for pid in edge_ids:
        for r in range(4):
            p_r = rotate_piece(pieces[pid], r)
            if p_r[0] == 0 and p_r[2] != 0:
                top_orientations[pid].append((r, p_r[1], p_r[3]))

    # Count how many TOP rotations per piece.
    print(f"\nTop-row rotation count per edge piece:", flush=True)
    rot_dist = Counter(len(rs) for rs in top_orientations.values())
    print(f"  {dict(rot_dist)}", flush=True)

    # For the TOP ROW, each edge piece needs:
    #   - W color matches predecessor's E color
    # So a piece P at rotation r_P contributes (E=e, W=w). Its W must match
    # the previous piece's E.
    # Build forward-graph: edges (p, q) where some (r_P, r_Q) makes P.E == Q.W.

    # Count adjacency-multiplicity per piece pair.
    adj_count = defaultdict(int)  # (p, q) → # of (r_p, r_q) combos
    p_to_e_color_choices = defaultdict(set)  # piece → set of E colors achievable
    p_to_w_color_choices = defaultdict(set)
    for pid in edge_ids:
        for (r, e, w) in top_orientations[pid]:
            p_to_e_color_choices[pid].add(e)
            p_to_w_color_choices[pid].add(w)
    # For each pair (p, q), can p's E meet q's W?
    pieces_to_check = edge_ids
    for p in pieces_to_check:
        for q in pieces_to_check:
            if p == q: continue
            shared = p_to_e_color_choices[p] & p_to_w_color_choices[q]
            if shared:
                adj_count[(p, q)] = len(shared)

    print(f"\nTotal directed edge-piece pairs with potential top-row adjacency: {len(adj_count)}", flush=True)
    # For each edge piece, who CAN follow?
    out_degree = defaultdict(int)
    in_degree = defaultdict(int)
    for (p, q), n in adj_count.items():
        out_degree[p] += 1
        in_degree[q] += 1
    print(f"\nOut-degree distribution (top-row edge pieces):", flush=True)
    od = Counter(out_degree[p] for p in edge_ids if out_degree[p] > 0)
    print(f"  {dict(sorted(od.items()))}", flush=True)
    print(f"\nIn-degree distribution:", flush=True)
    id_ = Counter(in_degree[p] for p in edge_ids if in_degree[p] > 0)
    print(f"  {dict(sorted(id_.items()))}", flush=True)

    # Pieces with UNIQUE successor (out-degree=1) are FORCED edges.
    unique_successor = [p for p in edge_ids if out_degree[p] == 1]
    unique_predecessor = [p for p in edge_ids if in_degree[p] == 1]
    print(f"\nEdge pieces with UNIQUE top-row successor: {len(unique_successor)}", flush=True)
    print(f"Edge pieces with UNIQUE top-row predecessor: {len(unique_predecessor)}", flush=True)
    if unique_successor:
        for p in unique_successor[:10]:
            successors = [q for (px, q) in adj_count if px == p]
            print(f"  p={p} (sides={pieces[p]}) → q={successors[0]} (sides={pieces[successors[0]]})", flush=True)

    # Save.
    out_dir = REPO / "output/vol-127"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "border_hamilton.json"
    with open(out_path, "w") as f:
        json.dump({
            "n_edge_pieces": len(edge_ids),
            "edge_piece_ids": edge_ids,
            "n_potential_adjacencies": len(adj_count),
            "out_degree": {str(p): out_degree[p] for p in edge_ids},
            "in_degree": {str(p): in_degree[p] for p in edge_ids},
            "unique_successor_pieces": unique_successor,
            "unique_predecessor_pieces": unique_predecessor,
        }, f, indent=2)
    print(f"\nWrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
