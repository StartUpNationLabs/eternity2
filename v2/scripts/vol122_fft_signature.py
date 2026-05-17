#!/usr/bin/env python3
"""Vol-122 K8 — FFT signature of E2 boards.

Cross-domain lens: treat a complete E2 board as a 16x16 image with 4
color channels (top, right, bottom, left edges of each cell). Apply 2D
FFT to each channel. Compare frequency signatures of:
- A 459 record board
- A randomly-piece-permuted board
- A J1-hinted-v2-ALNS 445 board

Hypothesis: high-score boards have specific low-frequency dominance
(periodic color smoothness). If so, we have a NEW SCORING FUNCTION
for partial boards: FFT-energy as a quality predictor.

Usage:
  python3 scripts/vol122_fft_signature.py
"""
import json
import sys
import os
sys.path.insert(0, '/usr/local/lib/python3.11/site-packages')
try:
    import numpy as np
except ImportError:
    print("numpy not available; install via pip3")
    sys.exit(1)

SIDE = 16
PUZZLE = "../data/puzzles/size_16_official_eternity.csv"


def parse_color(s):
    """Parse the binary one-hot color encoding."""
    if s == "1" * 16:
        return 0  # BORDER
    v = int(s, 2)
    if v == 0:
        return 0
    return v.bit_length()  # 1-indexed


def load_pieces():
    pieces = []
    with open(PUZZLE) as f:
        for ln in f.readlines()[1:]:
            parts = ln.strip().split(',')
            if len(parts) < 7:
                continue
            t, r, bt, l = (parse_color(parts[i]) for i in range(4))
            pieces.append((t, r, bt, l))
    return pieces


def rot_edges(e, r):
    if r == 0: return e
    if r == 1: return (e[3], e[0], e[1], e[2])
    if r == 2: return (e[2], e[3], e[0], e[1])
    return (e[1], e[2], e[3], e[0])


def board_to_color_tensor(board_path, pieces):
    """Return a 16x16x4 tensor of edge colors for each cell."""
    with open(board_path) as f:
        data = json.load(f)
    tensor = np.zeros((SIDE, SIDE, 4))
    for p in data['placement']:
        pos = p['pos']
        pid = p['piece_id']
        rot = p['rotation']
        r, c = pos // SIDE, pos % SIDE
        if pid >= len(pieces):
            continue
        edges = rot_edges(pieces[pid], rot)
        for k, e in enumerate(edges):
            tensor[r, c, k] = e
    return tensor


def fft_energy_signature(tensor):
    """Per-channel FFT, return mean of |F|^2 over low vs high frequencies."""
    sig = {}
    for k, name in enumerate(['top', 'right', 'bottom', 'left']):
        F = np.fft.fft2(tensor[:, :, k])
        P = np.abs(F) ** 2  # power spectrum
        # DC + 4 lowest non-DC frequencies
        # Low: indices (0,0), (0,1), (1,0), (1,1), (0,15), (15,0)
        low_mask = np.zeros_like(P, dtype=bool)
        for fi in range(3):
            for fj in range(3):
                low_mask[fi, fj] = True
                low_mask[-fi-1 % SIDE, -fj-1 % SIDE] = True
        sig[f'{name}_low_energy'] = P[low_mask].sum()
        sig[f'{name}_high_energy'] = P[~low_mask].sum()
        sig[f'{name}_low_frac'] = sig[f'{name}_low_energy'] / P.sum()
    sig['total_low_frac'] = np.mean([sig[f'{n}_low_frac'] for n in ['top','right','bottom','left']])
    return sig


def main():
    pieces = load_pieces()
    print(f"Loaded {len(pieces)} pieces")

    candidates = [
        ("J1-hinted-v2 ALNS s7 (445)", "output/v17_alns_only/basic_sa_t1_s7_1779025321_699358000_p14813.json"),
        ("J1-hinted-v2 ALNS s42 (444)", "output/v17_alns_only/basic_sa_t1_s42_1779025321_735369000_p14814.json"),
        ("J1-FLH 447 raw", "output/vol-122/j1_rust_flh.json"),
        ("J1-hinted-v2 414 raw", "output/vol-122/j1_chain_hinted_v2_b100k.json"),
    ]
    # Try to find a 459 record
    record_candidates = [
        "output/cross_machine/RECORD_TIE_459_p06.json",
        "output/cross_machine/RECORD_p06.json",
    ]
    for rc in record_candidates:
        if os.path.exists(rc):
            candidates.insert(0, (f"459 record: {rc}", rc))
            break

    print(f"\nFFT Signatures (lower 'low_frac' = more diffuse color distribution):")
    print(f"{'Board':<50} {'matched':>8} {'low_frac':>10}")
    for label, path in candidates:
        if not os.path.exists(path):
            print(f"{label:<50} {'NOT FOUND':>8}")
            continue
        try:
            tensor = board_to_color_tensor(path, pieces)
            sig = fft_energy_signature(tensor)
            # Try to extract matched if available
            with open(path) as f:
                d = json.load(f)
            matched = d.get('matched_edges', '?')
            print(f"{label:<50} {str(matched):>8} {sig['total_low_frac']:>10.4f}")
        except Exception as e:
            print(f"{label:<50} ERROR: {e}")


if __name__ == "__main__":
    main()
