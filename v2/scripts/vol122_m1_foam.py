#!/usr/bin/env python3
"""Vol-122 M1 — Foam topology / Plateau angle analysis.

Cross-domain physics lens (per K12 brainstorm). Treat mismatched edges
as 'walls' of bubbles. Identify junctions where 3+ mismatched edges
meet. In foam physics, equilibrium has 120° junctions (Plateau's law).

Measure for each board:
- # of cells with ≥3 mismatched edges
- # of cells with exactly 4 mismatched edges (4-way junctions, anomalous)
- Distribution of "junction degree" (how many mismatched edges touch a cell)

Higher-score boards should have FEWER 4-way junctions if Plateau's
law applies.
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


def board_to_mismatch_per_cell(board_path, pieces):
    """Per-cell count of mismatched edges (0-4)."""
    with open(board_path) as f:
        data = json.load(f)
    placement = [[None] * SIDE for _ in range(SIDE)]
    for p in data['placement']:
        pos = p['pos']
        r, c = pos // SIDE, pos % SIDE
        if p['piece_id'] >= len(pieces): continue
        placement[r][c] = rot_edges(pieces[p['piece_id']], p['rotation'])

    counts = np.zeros((SIDE, SIDE), dtype=int)
    for r in range(SIDE):
        for c in range(SIDE):
            if placement[r][c] is None: continue
            T, R, B, L = placement[r][c]
            # Top neighbor
            if r > 0 and placement[r-1][c]:
                nT, nR, nB, nL = placement[r-1][c]
                if T != nB or T == 0:
                    counts[r][c] += 1
            # Bottom
            if r < SIDE-1 and placement[r+1][c]:
                nT, nR, nB, nL = placement[r+1][c]
                if B != nT or B == 0:
                    counts[r][c] += 1
            # Left
            if c > 0 and placement[r][c-1]:
                nT, nR, nB, nL = placement[r][c-1]
                if L != nR or L == 0:
                    counts[r][c] += 1
            # Right
            if c < SIDE-1 and placement[r][c+1]:
                nT, nR, nB, nL = placement[r][c+1]
                if R != nL or R == 0:
                    counts[r][c] += 1
    return counts


def junction_stats(counts):
    """Distribution of cell degrees in the mismatch incidence graph."""
    flat = counts.flatten()
    hist = [0] * 5
    for v in flat:
        if v < 5:
            hist[v] += 1
    return hist


def main():
    pieces = load_pieces()
    candidates = [
        ("Standing 459 (vol-60)", "output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json", 459),
        ("Vol-32 RECORD 458", "output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json", 458),
        ("457 blackwood seed10 (high λ_2)", "output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed10.json", 457),
        ("457 vol-34 seed1", "output/vol-34/t3_signal/RECORD_TIE_457_vol34_t3_t01_seed1.json", 457),
        ("J1-hinted-v2 ALNS s7", "output/v17_alns_only/basic_sa_t1_s7_1779025321_699358000_p14813.json", 445),
        ("J1-FLH 447 raw", "output/vol-122/j1_rust_flh.json", 447),
    ]
    print(f"\nFoam junction degree histograms (# cells with K mismatched edges):")
    print(f"{'Board':<40} {'matched':>8} {'K=0':>5} {'K=1':>5} {'K=2':>5} {'K=3':>5} {'K=4':>5}")
    for label, path, mexpected in candidates:
        if not os.path.exists(path):
            print(f"{label:<40} {mexpected:>8} NOT FOUND")
            continue
        try:
            counts = board_to_mismatch_per_cell(path, pieces)
            hist = junction_stats(counts)
            print(f"{label:<40} {mexpected:>8} {hist[0]:>5} {hist[1]:>5} {hist[2]:>5} {hist[3]:>5} {hist[4]:>5}")
        except Exception as e:
            print(f"{label:<40} {mexpected:>8} ERROR: {e}")


if __name__ == "__main__":
    main()
