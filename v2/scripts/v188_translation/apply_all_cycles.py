#!/usr/bin/env python3
"""V188-T3 — apply EACH cycle of π (V181→McGavin) individually and report scores."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v184_lighthouse"))
from build_bidirectional2 import load_pieces, score_full
sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
from compute_pi import load_placement, cycle_decomposition

REPO = Path(__file__).resolve().parents[2]


def main():
    pieces = load_pieces()
    pl_a, score_a = load_placement(REPO / 'output/vol-181/RECORD_460_NEW_BASIN_row_s42_cp0312.json')
    pl_b, score_b = load_placement(REPO / 'database-400-480/469_mcgavin_469_6c9a2448.json')
    pi = {pl_a[p][0]: pl_b[p][0] for p in range(256)}
    cycles = cycle_decomposition(pi)
    pos_a = {pl_a[p][0]: p for p in range(256)}

    print(f"Board A (V181 460) score: {score_a}")
    print(f"Board B (McGavin 469) score: {score_b}")
    print(f"Total cycles in π: {len(cycles)}")
    print(f"\nApplying each cycle individually:")
    print(f"{'cycle_len':>10} {'new_score':>10} {'Δ':>6} {'pieces (first 5)':>25}")

    results = []
    for c in sorted(cycles, key=len):
        new_pl = list(pl_a)
        for pid in c:
            pa = pos_a[pid]
            pb_pid = pl_b[pa][0]
            pb_rot = pl_b[pa][1]
            new_pl[pa] = (pb_pid, pb_rot)
        new_score = score_full(new_pl, pieces)
        delta = new_score - score_a
        sample = c[:5]
        print(f"{len(c):>10} {new_score:>10} {delta:>+6} {str(sample):>25}")
        results.append((len(c), new_score, delta, c))

    # Also: apply ALL cycles (full π) → should recover full McGavin 469.
    print(f"\nApply full π (all cycles together):")
    new_pl = list(pl_a)
    for pid in pi:
        pa = pos_a[pid]
        pb_pid = pl_b[pa][0]
        pb_rot = pl_b[pa][1]
        new_pl[pa] = (pb_pid, pb_rot)
    new_score = score_full(new_pl, pieces)
    print(f"  Full π applied: new_score = {new_score}/480 (sanity: should be McGavin = {score_b})")

    # Best individual cycle
    best = max(results, key=lambda x: x[1])
    print(f"\nBest individual cycle: len={best[0]}, score={best[1]}, Δ={best[2]:+}")

    # Pairs of cycles
    print(f"\nPairs of cycles (only if both bottom-confined to test partial transport):")
    bottom_positions = set(r * 16 + c for r in range(11, 16) for c in range(16))
    bottom_pieces_a = set(pl_a[p][0] for p in bottom_positions)
    bottom_pieces_b = set(pl_b[p][0] for p in bottom_positions)
    fully_bottom = [c for c in cycles
                    if all(p in bottom_pieces_a for p in c) and all(pi[p] in bottom_pieces_b for p in c)]
    print(f"  Fully bottom-confined cycles: {len(fully_bottom)}")
    for c in fully_bottom:
        print(f"    cycle len {len(c)}: {c}")

    # Try combining the bottom-confined cycles
    print(f"\nCombining all bottom-confined cycles:")
    all_bottom_pids = [p for c in fully_bottom for p in c]
    new_pl = list(pl_a)
    for pid in all_bottom_pids:
        pa = pos_a[pid]
        pb_pid = pl_b[pa][0]
        pb_rot = pl_b[pa][1]
        new_pl[pa] = (pb_pid, pb_rot)
    new_score = score_full(new_pl, pieces)
    print(f"  Combined bottom-confined apply: score = {new_score} (Δ = {new_score - score_a:+})")

    # Also: apply pairs of small cycles to test indecomposability
    print(f"\nPairs of small cycles (lengths ≤ 6):")
    small = [c for c in cycles if len(c) <= 6 and len(c) > 1]
    for i, c1 in enumerate(small):
        for c2 in small[i+1:]:
            combined = c1 + c2
            new_pl = list(pl_a)
            for pid in combined:
                pa = pos_a[pid]
                pb_pid = pl_b[pa][0]
                pb_rot = pl_b[pa][1]
                new_pl[pa] = (pb_pid, pb_rot)
            new_score = score_full(new_pl, pieces)
            delta = new_score - score_a
            print(f"  pair (len {len(c1)} + len {len(c2)}): score={new_score} Δ={delta:+}")


if __name__ == '__main__':
    main()
