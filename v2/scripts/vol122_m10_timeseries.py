#!/usr/bin/env python3
"""Vol-122 M10 — time-series view of E2 boards.

For each row r of a board, the sequence of (T,R,B,L)-color tuples is a
"time series". Compute autocorrelation at lag 1-7 for each row, then
average over rows. Higher autocorrelation = more local color smoothness.

Alternative: compute the discrete Fourier transform of the per-row
color sum and measure spectral density.
"""
import json
import os
import sys

sys.path.insert(0, 'scripts')
try:
    import numpy as np
    from vol122_fft_signature import load_pieces, rot_edges, SIDE
    from vol122_k11_4_compression import load_placement
except ImportError as e:
    print("Import error:", e)
    sys.exit(1)


def board_to_row_color_sequences(board_path, pieces):
    """Returns SIDE rows, each a sequence of 16 'color tuples' (T+R+B+L sum)."""
    placement = load_placement(board_path)
    rows = []
    for r in range(SIDE):
        row_seq = []
        for c in range(SIDE):
            if placement[r][c] is None: continue
            pid, rot = placement[r][c]
            if pid >= len(pieces): continue
            T, R, B, L = rot_edges(pieces[pid], rot)
            row_seq.append((T, R, B, L))
        rows.append(row_seq)
    return rows


def autocorrelation_avg(rows, lag=1):
    """Per-row autocorrelation of the 'top color' sequence; average over rows."""
    accs = []
    for row in rows:
        if len(row) < lag + 1: continue
        top_seq = np.array([e[0] for e in row])
        if top_seq.std() < 1e-9: continue
        x = top_seq - top_seq.mean()
        denom = (x * x).sum()
        num = (x[:-lag] * x[lag:]).sum()
        accs.append(num / denom if denom > 1e-9 else 0)
    return float(np.mean(accs)) if accs else 0


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
    print(f"\nTop-color autocorrelation by row (avg over 16 rows):")
    print(f"{'Board':<40} {'matched':>8} {'acf(1)':>10} {'acf(2)':>10} {'acf(3)':>10}")
    for label, path, mexpected in candidates:
        if not os.path.exists(path):
            print(f"{label:<40} {mexpected:>8} NOT FOUND")
            continue
        rows = board_to_row_color_sequences(path, pieces)
        a1 = autocorrelation_avg(rows, 1)
        a2 = autocorrelation_avg(rows, 2)
        a3 = autocorrelation_avg(rows, 3)
        print(f"{label:<40} {mexpected:>8} {a1:>10.4f} {a2:>10.4f} {a3:>10.4f}")


if __name__ == "__main__":
    main()
