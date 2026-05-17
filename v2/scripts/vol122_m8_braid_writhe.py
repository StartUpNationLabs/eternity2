#!/usr/bin/env python3
"""Vol-122 M8 — Braid writhe analysis of E2 boards.

Cross-domain topology lens: each board row's bottom-edge color sequence
can be thought of as a braid where each cell's "strand" has color =
piece's bottom edge. Adjacent rows must "join" via matching strands.

We compute: at each row-to-row interface, count how many strand-pairs
are CROSSING (mismatched, i.e., color_below != color_above). Each
crossing contributes +1 or -1 to a 'writhe' depending on chirality.

For simplicity, define writhe per interface = (#mismatched horizontal
crossings at this interface) modulo some chirality count.

Total writhe = sum over 15 inter-row interfaces.

Hypothesis: high-score boards have LOW total writhe = closer to identity
braid = more 'untangled' arrangement.
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


def board_to_braid_writhe(board_path, pieces):
    """Compute total 'writhe' as sum of vertical mismatched crossings.

    Refined: at each inter-row interface r, the bottoms of row r should
    match the tops of row r+1. For each column, if bot[r][c] != top[r+1][c],
    that's a CROSSING. The signed crossing = sign of (bot - top) gives
    chirality.
    """
    placement = load_placement(board_path)
    total_writhe = 0
    writhe_per_interface = []
    for r in range(SIDE - 1):
        interface_writhe = 0
        for c in range(SIDE):
            if placement[r][c] is None or placement[r+1][c] is None:
                continue
            pid1, rot1 = placement[r][c]
            pid2, rot2 = placement[r+1][c]
            if pid1 >= len(pieces) or pid2 >= len(pieces): continue
            e1 = rot_edges(pieces[pid1], rot1)
            e2 = rot_edges(pieces[pid2], rot2)
            bot = e1[2]
            top = e2[0]
            if bot != top:
                # Signed crossing: + if bot > top, - if bot < top
                interface_writhe += 1 if bot > top else -1
        writhe_per_interface.append(interface_writhe)
        total_writhe += interface_writhe
    return total_writhe, writhe_per_interface


def board_to_horizontal_writhe(board_path, pieces):
    """Same but for column-to-column adjacencies (horizontal direction)."""
    placement = load_placement(board_path)
    total_writhe = 0
    for r in range(SIDE):
        for c in range(SIDE - 1):
            if placement[r][c] is None or placement[r][c+1] is None: continue
            pid1, rot1 = placement[r][c]
            pid2, rot2 = placement[r][c+1]
            if pid1 >= len(pieces) or pid2 >= len(pieces): continue
            e1 = rot_edges(pieces[pid1], rot1)
            e2 = rot_edges(pieces[pid2], rot2)
            right = e1[1]
            left = e2[3]
            if right != left:
                total_writhe += 1 if right > left else -1
    return total_writhe


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
    print(f"\nBraid writhe (signed mismatch count):")
    print(f"{'Board':<40} {'matched':>8} {'V-writhe':>10} {'H-writhe':>10} {'|writhe|':>10}")
    for label, path, mexpected in candidates:
        if not os.path.exists(path):
            print(f"{label:<40} {mexpected:>8} NOT FOUND")
            continue
        try:
            wv, _ = board_to_braid_writhe(path, pieces)
            wh = board_to_horizontal_writhe(path, pieces)
            abs_w = abs(wv) + abs(wh)
            print(f"{label:<40} {mexpected:>8} {wv:>10} {wh:>10} {abs_w:>10}")
        except Exception as e:
            print(f"{label:<40} {mexpected:>8} ERROR: {e}")


if __name__ == "__main__":
    main()
