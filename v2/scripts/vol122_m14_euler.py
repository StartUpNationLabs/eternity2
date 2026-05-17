#!/usr/bin/env python3
"""Vol-122 M14 — Euler characteristic of matched-edge graph.

The matched-edge subgraph is planar (embedded in 16x16 grid). Its
Euler characteristic χ = V - E + F partitions the board into:
- Vertices: # placed cells with matched-edges (=256 for complete board)
- Edges: # matched edges in graph
- Faces: # bounded regions

For a connected planar graph, χ = 1.
For disconnected planar graphs, χ = # components.

For our matched-edge subgraph (which is a SUBGRAPH of the grid), we
can compute χ to identify TOPOLOGICAL changes between boards.
"""
import json
import os
import sys

sys.path.insert(0, 'scripts')
try:
    import numpy as np
    from scipy.sparse.csgraph import connected_components
    from scipy.sparse import csr_matrix
    from vol122_fft_signature import load_pieces, rot_edges, SIDE
    from vol122_k11_4_compression import load_placement
except ImportError as e:
    print("Import error:", e)
    sys.exit(1)


def build_match_subgraph(board_path, pieces):
    """Return (V_set, E_list) of the matched-edge subgraph.
    Cells with at least one matched edge are vertices."""
    placement = load_placement(board_path)
    edges = []
    for r in range(SIDE):
        for c in range(SIDE):
            if placement[r][c] is None: continue
            pid, rot = placement[r][c]
            if pid >= len(pieces): continue
            T, R, B, L = rot_edges(pieces[pid], rot)
            i = r * SIDE + c
            if c + 1 < SIDE and placement[r][c+1]:
                pid2, rot2 = placement[r][c+1]
                if pid2 < len(pieces):
                    nT, nR, nB, nL = rot_edges(pieces[pid2], rot2)
                    if R == nL and R != 0:
                        edges.append((i, r * SIDE + (c+1)))
            if r + 1 < SIDE and placement[r+1][c]:
                pid2, rot2 = placement[r+1][c]
                if pid2 < len(pieces):
                    nT, nR, nB, nL = rot_edges(pieces[pid2], rot2)
                    if B == nT and B != 0:
                        edges.append((i, (r+1) * SIDE + c))
    vertices = set()
    for u, v in edges:
        vertices.add(u); vertices.add(v)
    return vertices, edges


def count_faces(vertices, edges, side=SIDE):
    """Count bounded faces of the planar subgraph embedded in the grid.

    The 'faces' here are 1x1 cells of the grid whose 4 boundary edges
    are ALL in the matched-edge set. We're counting MATCHED-EDGE-BOUNDED
    UNIT SQUARES."""
    edge_set = set()
    for u, v in edges:
        edge_set.add((min(u, v), max(u, v)))
    faces = 0
    for r in range(side - 1):
        for c in range(side - 1):
            # 4 corners
            tl = r * side + c
            tr = r * side + (c+1)
            bl = (r+1) * side + c
            br = (r+1) * side + (c+1)
            # 4 edges
            e_top = (min(tl, tr), max(tl, tr))
            e_right = (min(tr, br), max(tr, br))
            e_bottom = (min(bl, br), max(bl, br))
            e_left = (min(tl, bl), max(tl, bl))
            if (e_top in edge_set and e_right in edge_set and
                e_bottom in edge_set and e_left in edge_set):
                faces += 1
    return faces


def euler_chi(vertices, edges):
    """χ = V - E (for planar graph drawn in plane, no enclosed unbounded face count)."""
    return len(vertices) - len(edges)


def main():
    pieces = load_pieces()
    candidates = [
        ("Standing 459 (vol-60)", "output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json", 459),
        ("Vol-32 RECORD 458", "output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json", 458),
        ("457 blackwood seed10", "output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed10.json", 457),
        ("457 vol-34 seed1", "output/vol-34/t3_signal/RECORD_TIE_457_vol34_t3_t01_seed1.json", 457),
        ("J1-FLH 447 raw", "output/vol-122/j1_rust_flh.json", 447),
        ("J1-hinted-v2 ALNS s7", "output/v17_alns_only/basic_sa_t1_s7_1779025321_699358000_p14813.json", 445),
    ]
    print(f"\nMatched-edge subgraph topology:")
    print(f"{'Board':<40} {'matched':>8} {'V':>4} {'E':>4} {'faces':>6} {'χ=V-E':>7}")
    for label, path, mexpected in candidates:
        if not os.path.exists(path):
            print(f"{label:<40} {mexpected:>8} NOT FOUND")
            continue
        try:
            V, E = build_match_subgraph(path, pieces)
            F = count_faces(V, E)
            chi = euler_chi(V, E)
            print(f"{label:<40} {mexpected:>8} {len(V):>4} {len(E):>4} {F:>6} {chi:>7}")
        except Exception as e:
            print(f"{label:<40} {mexpected:>8} ERROR: {e}")


if __name__ == "__main__":
    main()
