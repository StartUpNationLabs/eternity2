#!/usr/bin/env python3
"""Diagnose BP behavior on E2: where are the polarized cells? How badly is
piece-uniqueness violated in the BP marginals?
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from v11_load_e2 import load
from v11_factor_graph import (
    build_domains, adjacency_pairs, cell_class, SIZE, N
)
from v11_bp import (
    precompute_state_info, build_message_index, bp_iteration,
    compute_beliefs, cell_entropies
)


def piece_occupancy(beliefs, pids_per_cell, hints):
    """For each piece-id, sum its marginal probability across all cells.
    Hint pieces should sum to 1.0 (fully claimed by their cell);
    others should ideally sum to ≤ 1.0 (used at most once).
    """
    occ = np.zeros(256, dtype=np.float64)
    for pos, b in enumerate(beliefs):
        P = pids_per_cell[pos]
        # b[s] is probability cell pos chose state s = (pid P[s], rot ...)
        # Aggregate by pid.
        for s, pid in enumerate(P):
            occ[pid] += b[s]
    return occ


def main():
    puzzle = load()
    domains = build_domains(puzzle)
    edges_per_cell, pids_per_cell = precompute_state_info(puzzle, domains)
    pairs, m_var2fac, cell_to_pairs = build_message_index(domains)

    # Run BP to convergence
    for it in range(1, 201):
        change = bp_iteration(domains, edges_per_cell, pids_per_cell,
                              pairs, m_var2fac, cell_to_pairs, damping=0.3)
        if change < 1e-3:
            break
    print(f"BP converged at iter {it}, dL1={change:.4g}")

    beliefs = compute_beliefs(domains, edges_per_cell, pairs, m_var2fac, cell_to_pairs)
    H = cell_entropies(beliefs)

    # Piece occupancy
    occ = piece_occupancy(beliefs, pids_per_cell, puzzle["hints"])
    hint_pids = {pid for _, pid, _ in puzzle["hints"]}
    non_hint_occ = occ.copy()
    for pid in hint_pids:
        non_hint_occ[pid] = 0
    print()
    print("=== Piece occupancy (sum of marginal across cells) ===")
    print(f"hint pieces: " + ", ".join(f"{pid}:{occ[pid]:.4f}" for pid in sorted(hint_pids)))
    print(f"non-hint pieces: total mass = {non_hint_occ.sum():.2f} (should be ≤ 251 if every piece used once)")
    print(f"  min={non_hint_occ[non_hint_occ > 0].min():.4f} "
          f"max={non_hint_occ.max():.4f} "
          f"mean={non_hint_occ.mean():.4f} "
          f"median={np.median(non_hint_occ):.4f}")
    # Distribution histogram
    bins = [0, 0.5, 0.9, 1.0, 1.1, 1.5, 2.0, 5.0, 10.0, 100.0]
    hist, _ = np.histogram(non_hint_occ, bins=bins)
    for lo, hi, h in zip(bins[:-1], bins[1:], hist):
        print(f"  occ ∈ [{lo:>4.2f},{hi:>5.2f}): {h} pieces")
    # Most over-claimed pieces
    top_idx = np.argsort(-non_hint_occ)[:10]
    print(f"  top-10 over-claimed: " + ", ".join(f"{pid}:{non_hint_occ[pid]:.3f}" for pid in top_idx))

    # Most polarized non-hint cell
    print()
    print("=== Most polarized cells (lowest entropy, non-hint) ===")
    hint_positions = {p for p, _, _ in puzzle["hints"]}
    candidates = [(H[p], p) for p in range(N) if p not in hint_positions]
    candidates.sort()
    for h, p in candidates[:10]:
        x, y = p % SIZE, p // SIZE
        b = beliefs[p]
        D = len(domains[p])
        top = np.argsort(-b)[:3]
        cls = cell_class(p)
        print(f"  pos=({x:2d},{y:2d}) cls={cls:>8s} D={D:>4d} H={h:.4f} "
              f"top3=[{','.join(f'{int(domains[p][s][0])}r{int(domains[p][s][1])}:{b[s]:.3f}' for s in top)}]")

    # Color-marginal at the most polarized edge cell
    print()
    print("=== Per-side color marginals at polarized cells ===")
    for h, p in candidates[:3]:
        x, y = p % SIZE, p // SIZE
        cls = cell_class(p)
        b = beliefs[p]
        Ep = edges_per_cell[p]
        color_marg = np.zeros((4, 23))
        for s in range(len(b)):
            for side in range(4):
                color_marg[side, Ep[s, side]] += b[s]
        sides = "TRBL"
        print(f"  pos=({x},{y}) cls={cls}:")
        for side in range(4):
            top_c = np.argsort(-color_marg[side])[:5]
            print(f"    side {sides[side]}: " + ", ".join(f"c{c}:{color_marg[side, c]:.3f}" for c in top_c))


if __name__ == "__main__":
    main()
