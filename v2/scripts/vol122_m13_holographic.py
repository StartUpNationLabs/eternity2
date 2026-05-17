#!/usr/bin/env python3
"""Vol-122 M13 — Holographic / compressed-sensing reconstruction.

Cross-domain optics lens (per user note: hologram might have been good).

Approach: treat the mismatch indicator on the 16x16 board as a SPARSE
SIGNAL. The 459 record has ~21 mismatches in 480 edges = 4.4% density.

For each board:
1. Compute the 2D mismatch indicator field (cell-level: # mismatched edges
   touching each cell, normalized to [0,1]).
2. Apply 2D DFT.
3. Measure SPARSITY in the frequency domain (e.g., number of nonzero
   coefficients above threshold).
4. Apply low-pass filter and reconstruct. Does the reconstruction
   resemble the original?

Hypothesis: high-score boards have SPATIALLY CONCENTRATED mismatch
distributions → COMPRESSIBLE in frequency domain. Low-score boards
have scattered mismatches → less compressible.

This is a different angle from K11.4 (zlib of edge bytes); here we
work in the FREQUENCY domain with continuous values.
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


def board_to_mismatch_density(board_path, pieces):
    """Per-cell mismatch density: # mismatched edges touching this cell (0-4)."""
    with open(board_path) as f:
        data = json.load(f)
    placement = [[None] * SIDE for _ in range(SIDE)]
    for p in data['placement']:
        pos = p['pos']
        r, c = pos // SIDE, pos % SIDE
        if p['piece_id'] >= len(pieces): continue
        placement[r][c] = rot_edges(pieces[p['piece_id']], p['rotation'])

    density = np.zeros((SIDE, SIDE), dtype=float)
    for r in range(SIDE):
        for c in range(SIDE):
            if placement[r][c] is None: continue
            T, R, B, L = placement[r][c]
            # Check 4 neighbors
            if r > 0 and placement[r-1][c]:
                if T != placement[r-1][c][2] or T == 0:
                    density[r][c] += 1
            if r < SIDE-1 and placement[r+1][c]:
                if B != placement[r+1][c][0] or B == 0:
                    density[r][c] += 1
            if c > 0 and placement[r][c-1]:
                if L != placement[r][c-1][1] or L == 0:
                    density[r][c] += 1
            if c < SIDE-1 and placement[r][c+1]:
                if R != placement[r][c+1][3] or R == 0:
                    density[r][c] += 1
    return density


def fft_sparsity(density):
    F = np.fft.fft2(density)
    P = np.abs(F)
    # Sparsity ≈ # coefficients > 5% of max
    threshold = P.max() * 0.05
    sparse_count = (P > threshold).sum()
    # Cumulative energy in top-k frequencies
    P_sorted = np.sort(P.flatten())[::-1]
    total = P.sum()
    energy_top10 = P_sorted[:10].sum() / total if total > 0 else 0
    return sparse_count, energy_top10


def low_pass_reconstruct(density, keep_frac):
    """FFT, keep top-keep_frac coefficients, inverse FFT."""
    F = np.fft.fft2(density)
    P = np.abs(F)
    # Find threshold to keep top fraction
    sorted_p = np.sort(P.flatten())[::-1]
    n_keep = int(keep_frac * sorted_p.size)
    threshold = sorted_p[n_keep] if n_keep < sorted_p.size else 0
    F_filtered = F * (P > threshold)
    reconstruction = np.real(np.fft.ifft2(F_filtered))
    error = np.abs(reconstruction - density).mean()
    return reconstruction, error


def main():
    pieces = load_pieces()
    candidates = [
        ("Standing 459 (vol-60)", "output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json", 459),
        ("Vol-32 RECORD 458", "output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json", 458),
        ("Vol-35 RECORD TIE 458", "output/vol-35/records/RECORD_TIE_458_vol35_deep458_winning5_seed5.json", 458),
        ("457 blackwood seed10 (high λ_2)", "output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed10.json", 457),
        ("457 vol-34 seed1", "output/vol-34/t3_signal/RECORD_TIE_457_vol34_t3_t01_seed1.json", 457),
        ("J1-hinted-v2 ALNS s7", "output/v17_alns_only/basic_sa_t1_s7_1779025321_699358000_p14813.json", 445),
        ("J1-FLH 447 raw", "output/vol-122/j1_rust_flh.json", 447),
        ("J1-FLH 444 raw", "output/vol-122/j1_rust_chain.json", 444),
    ]
    print(f"\nHolographic / FFT-sparsity of mismatch density (per cell):")
    print(f"{'Board':<40} {'matched':>8} {'#sparse':>10} {'top10/total':>12} {'err_5%':>9} {'err_1%':>9}")
    for label, path, mexpected in candidates:
        if not os.path.exists(path):
            print(f"{label:<40} {mexpected:>8} NOT FOUND")
            continue
        try:
            density = board_to_mismatch_density(path, pieces)
            sparse_n, top10 = fft_sparsity(density)
            _, err5 = low_pass_reconstruct(density, 0.05)
            _, err1 = low_pass_reconstruct(density, 0.01)
            print(f"{label:<40} {mexpected:>8} {sparse_n:>10} {top10:>12.4f} {err5:>9.4f} {err1:>9.4f}")
        except Exception as e:
            print(f"{label:<40} {mexpected:>8} ERROR: {e}")


if __name__ == "__main__":
    main()
