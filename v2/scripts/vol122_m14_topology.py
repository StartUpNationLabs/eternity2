#!/usr/bin/env python3
"""Vol-122 M14 — Simple TDA: cycle rank of matched-edge graph.

For each board, the matched-edge graph has betti number β_1 (# independent
cycles) = |E| - |V| + #components.

Higher β_1 = more cycles = more REDUNDANT matched edges = more 'robust'
network. Could indicate basin productivity for ALNS-style search.
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


def board_to_match_graph(board_path, pieces):
    placement = load_placement(board_path)
    n = SIDE * SIDE
    edges = set()
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
                        j = r * SIDE + (c+1)
                        edges.add((min(i, j), max(i, j)))
            if r + 1 < SIDE and placement[r+1][c]:
                pid2, rot2 = placement[r+1][c]
                if pid2 < len(pieces):
                    nT, nR, nB, nL = rot_edges(pieces[pid2], rot2)
                    if B == nT and B != 0:
                        j = (r+1) * SIDE + c
                        edges.add((min(i, j), max(i, j)))
    rows, cols = [], []
    for (a, b) in edges:
        rows.append(a); cols.append(b)
        rows.append(b); cols.append(a)
    A = csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n))
    return A, len(edges)


def betti_numbers(A, n_edges):
    n_comp, _ = connected_components(A, directed=False)
    # Vertices with at least one edge = active vertices
    n_active = (A.sum(axis=0) > 0).sum()
    # β_0 = #components (we count only active components since isolated
    # vertices contribute 0 to homology)
    # Actually β_0 = # components of the active subgraph.
    # β_1 = |E| - |V| + β_0 (for the active subgraph)
    beta_0 = n_comp
    beta_1 = n_edges - n_active + (256 - n_active)  # rough
    # better: count components including isolated vertices = n_comp
    # so β_1 = |E| - 256 + n_comp
    beta_1 = n_edges - 256 + n_comp
    return beta_0, beta_1, n_active


def main():
    pieces = load_pieces()
    candidates = [
        ("Standing 459 (vol-60)", "output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json", 459),
        ("Vol-32 RECORD 458", "output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json", 458),
        ("Vol-35 RECORD TIE 458", "output/vol-35/records/RECORD_TIE_458_vol35_deep458_winning5_seed5.json", 458),
        ("457 blackwood seed10", "output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed10.json", 457),
        ("457 vol-34 seed1", "output/vol-34/t3_signal/RECORD_TIE_457_vol34_t3_t01_seed1.json", 457),
        ("J1-FLH 447 raw", "output/vol-122/j1_rust_flh.json", 447),
        ("J1-hinted-v2 ALNS s7", "output/v17_alns_only/basic_sa_t1_s7_1779025321_699358000_p14813.json", 445),
    ]
    print(f"\nMatched-edge graph cycle structure (β_1 = redundant matched edges):")
    print(f"{'Board':<40} {'matched':>8} {'|E|':>5} {'β_0':>5} {'β_1':>5}")
    for label, path, mexpected in candidates:
        if not os.path.exists(path):
            print(f"{label:<40} {mexpected:>8} NOT FOUND")
            continue
        try:
            A, n_edges = board_to_match_graph(path, pieces)
            b0, b1, n_active = betti_numbers(A, n_edges)
            print(f"{label:<40} {mexpected:>8} {n_edges:>5} {b0:>5} {b1:>5}")
        except Exception as e:
            print(f"{label:<40} {mexpected:>8} ERROR: {e}")


if __name__ == "__main__":
    main()
