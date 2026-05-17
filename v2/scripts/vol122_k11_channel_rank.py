#!/usr/bin/env python3
"""Vol-122 K11.2 — Optical transmission channel analysis.

Cross-domain physics lens: treat the matched-edge graph as an optical
network. Compute:
- Algebraic connectivity (Fiedler eigenvalue of matched-edge Laplacian).
- Largest connected component size (in matched-edge graph).
- Average path length in matched-edge graph.

Compare across 459/458/457 records and J1 boards.

Hypothesis: 459 has higher algebraic connectivity than 458 because its
matched-edge graph forms a more cohesive network.
"""
import json
import os
import sys

sys.path.insert(0, 'scripts')
try:
    import numpy as np
    from vol122_fft_signature import load_pieces, rot_edges, SIDE
except ImportError as e:
    print("Import error:", e)
    sys.exit(1)

try:
    from scipy.sparse.linalg import eigsh
    from scipy.sparse.csgraph import connected_components, laplacian
    from scipy.sparse import csr_matrix
except ImportError:
    print("scipy required")
    sys.exit(1)


def board_to_match_graph(board_path, pieces):
    """Return a 256x256 adjacency matrix where A[i][j]=1 iff cells i, j are
    grid-neighbors AND share a matched edge."""
    with open(board_path) as f:
        data = json.load(f)
    placement = [[None] * SIDE for _ in range(SIDE)]
    for p in data['placement']:
        pos = p['pos']
        pid = p['piece_id']
        rot = p['rotation']
        r, c = pos // SIDE, pos % SIDE
        if pid >= len(pieces): continue
        placement[r][c] = rot_edges(pieces[pid], rot)

    n = SIDE * SIDE
    rows, cols = [], []
    for r in range(SIDE):
        for c in range(SIDE):
            if placement[r][c] is None: continue
            T, R, B, L = placement[r][c]
            i = r * SIDE + c
            if c + 1 < SIDE and placement[r][c+1] is not None:
                nT, nR, nB, nL = placement[r][c+1]
                if R == nL and R != 0:
                    j = r * SIDE + (c + 1)
                    rows.append(i); cols.append(j)
                    rows.append(j); cols.append(i)
            if r + 1 < SIDE and placement[r+1][c] is not None:
                nT, nR, nB, nL = placement[r+1][c]
                if B == nT and B != 0:
                    j = (r + 1) * SIDE + c
                    rows.append(i); cols.append(j)
                    rows.append(j); cols.append(i)
    data_arr = np.ones(len(rows))
    A = csr_matrix((data_arr, (rows, cols)), shape=(n, n))
    return A


def analyze(A):
    n_components, labels = connected_components(A, directed=False)
    sizes = np.bincount(labels)
    largest = sizes.max()
    L = laplacian(A, normed=False).toarray().astype(float)
    # Fiedler eigenvalue (lambda_2)
    eigvals = np.linalg.eigvalsh(L)
    # lambda_1 = 0 always; lambda_2 = algebraic connectivity
    lambda_2 = eigvals[1] if len(eigvals) > 1 else 0
    return {
        'n_components': n_components,
        'largest_component': int(largest),
        'lambda_2': float(lambda_2),
    }


def main():
    pieces = load_pieces()
    candidates = [
        ("Standing 459 (vol-60)", "output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json", 459),
        ("Vol-32 RECORD 458", "output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json", 458),
        ("Vol-35 RECORD TIE 458", "output/vol-35/records/RECORD_TIE_458_vol35_deep458_winning5_seed5.json", 458),
        ("Vol-35 RECORD TIE 457", "output/vol-35/records/RECORD_TIE_457_vol35_deep458_diverse_seed5_3hints.json", 457),
        ("J1-hinted-v2 ALNS s7", "output/v17_alns_only/basic_sa_t1_s7_1779025321_699358000_p14813.json", 445),
        ("J1-hinted-v2 ALNS s42", "output/v17_alns_only/basic_sa_t1_s42_1779025321_735369000_p14814.json", 444),
        ("J1-FLH 447 raw", "output/vol-122/j1_rust_flh.json", 447),
        ("J1-FLH 444 raw", "output/vol-122/j1_rust_chain.json", 444),
    ]
    print(f"\nMatched-edge graph analysis:")
    print(f"{'Board':<40} {'matched':>8} {'#comps':>7} {'maxcomp':>8} {'lambda_2':>10}")
    for label, path, mexpected in candidates:
        if not os.path.exists(path):
            print(f"{label:<40} {mexpected:>8} NOT FOUND")
            continue
        try:
            A = board_to_match_graph(path, pieces)
            stats = analyze(A)
            print(f"{label:<40} {mexpected:>8} {stats['n_components']:>7} {stats['largest_component']:>8} {stats['lambda_2']:>10.4f}")
        except Exception as e:
            print(f"{label:<40} {mexpected:>8} ERROR: {e}")


if __name__ == "__main__":
    main()
