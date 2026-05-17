#!/usr/bin/env python3
"""Vol-122 K11.1 — Wave-mechanics Hamiltonian eigenmode analysis.

Approach: instead of analyzing the CONFIGURATION-INDEPENDENT piece-piece
compatibility graph (vol-122 J3 already did this), build a
CONFIGURATION-AWARE Hamiltonian for a specific board.

The Hamiltonian:
H[i][j] = -1 if cells i, j are grid-adjacent AND share a matched edge
        = +1 if cells i, j are grid-adjacent AND share a mismatched edge
        = 0 otherwise

This is a SIGNED adjacency matrix. Eigenvalues reveal:
- Most-negative eigval: cluster of strongly-matched cells (good).
- Most-positive eigval: cluster of strongly-mismatched cells (bad).
- Zero eigvals: degenerate / disconnected.

Hypothesis: 459 has a different spectral distribution from 458 (we've
seen K11.2 confirms λ_2 already). Going further: SPECTRAL GAP (= λ_2 - λ_1
of the signed laplacian) might be a sharper signature.
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


def board_to_signed_adjacency(board_path, pieces):
    """Signed adjacency matrix: A[i][j] = ±1 for matched/mismatched
    grid-neighbor edges, 0 otherwise."""
    with open(board_path) as f:
        data = json.load(f)
    placement = [[None] * SIDE for _ in range(SIDE)]
    for p in data['placement']:
        pos = p['pos']
        r, c = pos // SIDE, pos % SIDE
        if p['piece_id'] >= len(pieces): continue
        placement[r][c] = rot_edges(pieces[p['piece_id']], p['rotation'])

    n = SIDE * SIDE
    A = np.zeros((n, n))
    for r in range(SIDE):
        for c in range(SIDE):
            if placement[r][c] is None: continue
            T, R, B, L = placement[r][c]
            i = r * SIDE + c
            if c + 1 < SIDE and placement[r][c+1]:
                nT, nR, nB, nL = placement[r][c+1]
                j = r * SIDE + (c+1)
                if R == nL and R != 0:
                    A[i][j] = A[j][i] = -1  # matched
                else:
                    A[i][j] = A[j][i] = +1  # mismatched
            if r + 1 < SIDE and placement[r+1][c]:
                nT, nR, nB, nL = placement[r+1][c]
                j = (r+1) * SIDE + c
                if B == nT and B != 0:
                    A[i][j] = A[j][i] = -1
                else:
                    A[i][j] = A[j][i] = +1
    return A


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
    print(f"\nSigned-adjacency Hamiltonian spectrum:")
    print(f"{'Board':<40} {'matched':>8} {'λ_min':>10} {'λ_max':>10} {'λ_+gap':>10}")
    for label, path, mexpected in candidates:
        if not os.path.exists(path):
            print(f"{label:<40} {mexpected:>8} NOT FOUND")
            continue
        try:
            A = board_to_signed_adjacency(path, pieces)
            eigvals = np.linalg.eigvalsh(A)
            # spectral gap above zero (= "next-mode" hardness)
            pos_eigvals = eigvals[eigvals > 0.001]
            spectral_gap_pos = (pos_eigvals[1] - pos_eigvals[0]) if len(pos_eigvals) >= 2 else 0
            print(f"{label:<40} {mexpected:>8} {eigvals[0]:>10.4f} {eigvals[-1]:>10.4f} {spectral_gap_pos:>10.4f}")
        except Exception as e:
            print(f"{label:<40} {mexpected:>8} ERROR: {e}")


if __name__ == "__main__":
    main()
