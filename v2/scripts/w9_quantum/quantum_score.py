"""W9 — Quantum-amplitude scoring for E2.

For each interior edge with colors c_a and c_b, contribute
  e^{i θ_{c_a}} + e^{i θ_{c_b}}
to the total amplitude. The board score is |sum of edge amplitudes|².

This is a continuous, gradient-friendly alternative to the discrete
matched-edge count.

Phases θ_c can be chosen uniformly (2π c / K) or learned via gradient
descent to maximize discrimination.

Phase 1: validate that for a complete solution, score = 4 * 480 (since
every edge contributes amplitude 2·e^{iθ} and |2e^{iθ}|² = 4).
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'w1_peps'))
from puzzle_loader import Puzzle, load_puzzle, BORDER


def compute_amplitude_score(
    puzzle: Puzzle,
    placement: dict[int, tuple[int, int]],
    phases: np.ndarray,
) -> tuple[complex, float]:
    """For each interior edge, compute the per-edge amplitude and aggregate.

    Per-edge amplitude: A_e = e^{iθ_c_a} + e^{iθ_c_b}.
      - If matched (c_a == c_b): A_e = 2 e^{iθ_c}, |A_e|² = 4.
      - If mismatched: |A_e|² = 2 + 2 cos(θ_c_a - θ_c_b) < 4.

    Returns:
      sum_of_amplitudes (complex)
      sum of |A_e|² (real, this is the discriminating score)
    """
    size = puzzle.size
    total = 0.0 + 0.0j
    score = 0.0

    for pos in range(size * size):
        if pos not in placement: continue
        pid, rot = placement[pos]
        edges = puzzle.piece_edges(pid, rot)
        y, x = pos // size, pos % size

        if x + 1 < size:
            right_pos = y * size + (x + 1)
            if right_pos in placement:
                rpid, rrot = placement[right_pos]
                redges = puzzle.piece_edges(rpid, rrot)
                c_left = edges[1]
                c_right = redges[3]
                amp = np.exp(1j * phases[c_left]) + np.exp(1j * phases[c_right])
                total += amp
                score += float(abs(amp) ** 2)

        if y + 1 < size:
            bot_pos = (y + 1) * size + x
            if bot_pos in placement:
                bpid, brot = placement[bot_pos]
                bedges = puzzle.piece_edges(bpid, brot)
                c_top = edges[2]
                c_bot = bedges[0]
                amp = np.exp(1j * phases[c_top]) + np.exp(1j * phases[c_bot])
                total += amp
                score += float(abs(amp) ** 2)

    return total, score


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle")
    ap.add_argument("board_json")
    ap.add_argument("--phase-mode", choices=['uniform', 'spread'], default='uniform')
    args = ap.parse_args()

    p = load_puzzle(args.puzzle)
    data = json.load(open(args.board_json))
    placement = {pp['pos']: (pp['piece_id'], pp['rotation']) for pp in data['placement']}
    print(f"Puzzle: size={p.size} K={p.n_colors}")
    print(f"Placement: {len(placement)} cells")

    # Phases
    K = p.n_colors
    if args.phase_mode == 'uniform':
        # phases[0] = 0 (BORDER), phases[c] = 2π c / (K-1) for c = 1..K-1
        phases = np.zeros(K)
        for c in range(1, K):
            phases[c] = 2 * np.pi * (c - 1) / (K - 1)
    elif args.phase_mode == 'spread':
        # Random phases for variety
        np.random.seed(42)
        phases = np.random.uniform(0, 2 * np.pi, K)
        phases[BORDER] = 0
    else:
        raise ValueError

    print(f"Phase mode: {args.phase_mode}")
    print(f"Phases: {phases}")

    # Compute scores
    amp, score = compute_amplitude_score(p, placement, phases)
    print(f"\nTotal amplitude: {amp}")
    print(f"Score |A|² = {score:.4f}")

    # Compare with discrete matched-edge count
    matched = 0
    for pos in range(p.size * p.size):
        if pos not in placement: continue
        pid, rot = placement[pos]
        edges = puzzle.piece_edges(pid, rot) if False else p.piece_edges(pid, rot)
        y, x = pos // p.size, pos % p.size
        if x + 1 < p.size:
            rp = y * p.size + (x + 1)
            if rp in placement:
                redges = p.piece_edges(*placement[rp])
                if edges[1] == redges[3] and edges[1] != BORDER:
                    matched += 1
        if y + 1 < p.size:
            bp = (y + 1) * p.size + x
            if bp in placement:
                bedges = p.piece_edges(*placement[bp])
                if edges[2] == bedges[0] and edges[2] != BORDER:
                    matched += 1
    print(f"Discrete matched edges: {matched}")

    # Theoretical max for a perfect solution
    # Each matched edge contributes |2·e^{iθ}|² = 4.
    # But this is the per-edge contribution; the total amplitude is SUM of these,
    # not sum of moduli.
    # |sum_e A_e|² = sum_e |A_e|² + cross-terms.
    # For all matched + same color: A_e = 2·e^{iθ_c} for all e at that color
    #   → sum is huge and constructive.
    # For all matched but different colors: sum is smaller (phases cancel).
    # Hmm — the score is sensitive to the COLOR DISTRIBUTION, not just count.

    print(f"\n|A|² / (4 × matched) = {score / (4 * matched):.4f} (= 1 if perfect constructive)")


if __name__ == "__main__":
    main()
