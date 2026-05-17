#!/usr/bin/env python3
"""Vol-122 M2 — Electrical circuit model.

Cross-domain lens: matched-edge graph as a network of resistors.
Compute the effective resistance between the 4 corners using the
pseudo-inverse of the graph Laplacian.

Effective resistance R_eff(i, j) = (e_i - e_j)^T L^+ (e_i - e_j)
where L^+ is the Moore-Penrose pseudo-inverse.

Lower R_eff = stronger network connection.

For each board, compute the AVERAGE pairwise R_eff among 4 corner cells.
"""
import json
import os
import sys

sys.path.insert(0, 'scripts')
try:
    import numpy as np
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import laplacian
    from vol122_fft_signature import load_pieces, rot_edges, SIDE
    from vol122_k11_4_compression import load_placement
except ImportError as e:
    print("Import error:", e)
    sys.exit(1)


def board_to_match_graph_dense(board_path, pieces):
    placement = load_placement(board_path)
    n = SIDE * SIDE
    A = np.zeros((n, n))
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
                        A[i][j] = A[j][i] = 1
            if r + 1 < SIDE and placement[r+1][c]:
                pid2, rot2 = placement[r+1][c]
                if pid2 < len(pieces):
                    nT, nR, nB, nL = rot_edges(pieces[pid2], rot2)
                    if B == nT and B != 0:
                        j = (r+1) * SIDE + c
                        A[i][j] = A[j][i] = 1
    return A


def effective_resistance_matrix(A):
    """For all pairs, compute R_eff using L^+."""
    L = np.diag(A.sum(axis=1)) - A
    L_pinv = np.linalg.pinv(L)
    n = L.shape[0]
    R = np.zeros((n, n))
    diag = np.diag(L_pinv)
    for i in range(n):
        for j in range(n):
            R[i][j] = diag[i] + diag[j] - 2 * L_pinv[i][j]
    return R


def main():
    pieces = load_pieces()
    candidates = [
        ("Standing 459 (vol-60)", "output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json", 459),
        ("Vol-32 RECORD 458", "output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json", 458),
        ("457 blackwood seed10", "output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed10.json", 457),
        ("457 vol-34 seed1", "output/vol-34/t3_signal/RECORD_TIE_457_vol34_t3_t01_seed1.json", 457),
        ("J1-FLH 447 raw", "output/vol-122/j1_rust_flh.json", 447),
    ]
    corners = [0, SIDE - 1, SIDE * (SIDE - 1), SIDE * SIDE - 1]
    print(f"\nEffective resistance among corners (lower = stronger network):")
    print(f"{'Board':<40} {'matched':>8} {'R(TL,TR)':>10} {'R(TL,BL)':>10} {'R(BL,BR)':>10} {'avg':>8}")
    for label, path, mexpected in candidates:
        if not os.path.exists(path):
            print(f"{label:<40} {mexpected:>8} NOT FOUND")
            continue
        try:
            A = board_to_match_graph_dense(path, pieces)
            R = effective_resistance_matrix(A)
            r_tl_tr = R[corners[0], corners[1]]
            r_tl_bl = R[corners[0], corners[2]]
            r_bl_br = R[corners[2], corners[3]]
            avg = (r_tl_tr + r_tl_bl + r_bl_br + R[corners[1], corners[3]]) / 4
            print(f"{label:<40} {mexpected:>8} {r_tl_tr:>10.4f} {r_tl_bl:>10.4f} {r_bl_br:>10.4f} {avg:>8.4f}")
        except Exception as e:
            print(f"{label:<40} {mexpected:>8} ERROR: {e}")


if __name__ == "__main__":
    main()
