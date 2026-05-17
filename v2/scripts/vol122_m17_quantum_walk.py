#!/usr/bin/env python3
"""Vol-122 M17 — Quantum walk on matched-edge graph.

Cross-domain QM lens: continuous-time quantum walk
|ψ(t)⟩ = exp(-iAt) |ψ(0)⟩ where A is the adjacency matrix.

Start from a localized state at one hint position. Measure:
- Return probability at t=1 (how 'sticky' is the initial cell).
- Mean position spread (how fast the walk spreads).
- Probability of reaching all hint positions at t=10.

Higher 'connectedness' of matched-edge graph → faster spread → lower
return probability.
"""
import json
import os
import sys

sys.path.insert(0, 'scripts')
try:
    import numpy as np
    from scipy.linalg import expm
    from vol122_fft_signature import load_pieces, rot_edges, SIDE
    from vol122_k11_4_compression import load_placement
except ImportError as e:
    print("Import error:", e)
    sys.exit(1)


def board_to_match_adjacency(placement, pieces):
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


def quantum_walk(board_path, pieces, t=1.0, start_pos=135):
    """Compute |ψ(t)|² at all cells starting from start_pos."""
    placement = load_placement(board_path)
    A = board_to_match_adjacency(placement, pieces)
    n = A.shape[0]
    psi0 = np.zeros(n, dtype=complex)
    psi0[start_pos] = 1.0 + 0j
    # Use eigendecomp for efficient exp
    eigvals, eigvecs = np.linalg.eigh(A)
    psi_t = eigvecs @ (np.exp(-1j * t * eigvals) * (eigvecs.T @ psi0))
    p = np.abs(psi_t) ** 2
    return p


def board_walk_metrics(board_path, pieces, hint_positions, t_short=1.0, t_long=10.0):
    """For each hint position, compute return probabilities and spread."""
    placement = load_placement(board_path)
    A = board_to_match_adjacency(placement, pieces)
    n = A.shape[0]
    eigvals, eigvecs = np.linalg.eigh(A)
    metrics = {}
    for hp in hint_positions:
        psi0 = np.zeros(n, dtype=complex)
        psi0[hp] = 1.0
        eVT_short = np.exp(-1j * t_short * eigvals)
        eVT_long = np.exp(-1j * t_long * eigvals)
        psi_short = eigvecs @ (eVT_short * (eigvecs.T @ psi0))
        psi_long = eigvecs @ (eVT_long * (eigvecs.T @ psi0))
        p_short = np.abs(psi_short) ** 2
        p_long = np.abs(psi_long) ** 2
        # Probability concentrated at OTHER hints at t_long
        other_hints = [h for h in hint_positions if h != hp]
        p_at_hints = sum(p_long[h] for h in other_hints)
        # Spread
        sigma_sq = 0
        h_r, h_c = hp // SIDE, hp % SIDE
        for i, prob in enumerate(p_long):
            r, c = i // SIDE, i % SIDE
            sigma_sq += prob * ((r - h_r)**2 + (c - h_c)**2)
        metrics[hp] = {
            'p_return_t1': float(p_short[hp].real),
            'p_other_hints_t10': float(p_at_hints),
            'spread_t10': float(sigma_sq ** 0.5),
        }
    return metrics


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
    hint_positions = [34, 45, 135, 210, 221]
    print(f"\nQuantum walk: avg over 5 hint start-positions, t=1, t=10:")
    print(f"{'Board':<40} {'matched':>8} {'avgPret':>10} {'avgPother':>12} {'avgSpread':>10}")
    for label, path, mexpected in candidates:
        if not os.path.exists(path):
            print(f"{label:<40} {mexpected:>8} NOT FOUND")
            continue
        try:
            m = board_walk_metrics(path, pieces, hint_positions, t_short=1.0, t_long=10.0)
            avg_pret = np.mean([m[h]['p_return_t1'] for h in hint_positions])
            avg_pother = np.mean([m[h]['p_other_hints_t10'] for h in hint_positions])
            avg_spread = np.mean([m[h]['spread_t10'] for h in hint_positions])
            print(f"{label:<40} {mexpected:>8} {avg_pret:>10.6f} {avg_pother:>12.6f} {avg_spread:>10.4f}")
        except Exception as e:
            print(f"{label:<40} {mexpected:>8} ERROR: {e}")


if __name__ == "__main__":
    main()
