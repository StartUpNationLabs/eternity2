#!/usr/bin/env python3
"""Dump BP marginals after convergence in a Rust-loadable JSON format.

Output: output/v11_sp/bp_marginals.json with structure:
{
  "schema_version": 1,
  "size": 16,
  "n_cells": 256,
  "marginals": [
    {
      "pos": 0,
      "x": 0, "y": 0,
      "class": "corner",
      "states": [
        {"piece_id": 3, "rotation": 3, "marginal": 0.301, "rank": 0},
        ...
      ]
    },
    ...
  ]
}

States are sorted by descending marginal. Only states with marginal > 1e-6
are kept. The Rust side can use this to implement a ValueOrder::BPMarginal
that orders domain rows by BP-rank.
"""
from __future__ import annotations

import sys
import json
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from v11_load_e2 import load
from v11_factor_graph import build_domains, adjacency_pairs, cell_class, SIZE, N
from v11_bp_uniq import (
    bp_iteration_with_uniqueness, compute_beliefs_with_uniqueness,
    piece_availability
)
from v11_bp import precompute_state_info, build_message_index, cell_entropies

MIN_MARGINAL = 1e-6


def main():
    puzzle = load()
    domains = build_domains(puzzle)
    edges_per_cell, pids_per_cell = precompute_state_info(puzzle, domains)
    pairs, m_var2fac, cell_to_pairs = build_message_index(domains)

    avail = np.ones(256, dtype=np.float64)
    t0 = time.time()

    print("Converging BP+softUniqueness...")
    for outer in range(20):
        for it in range(200):
            change = bp_iteration_with_uniqueness(
                domains, edges_per_cell, pids_per_cell, pairs, m_var2fac,
                cell_to_pairs, avail, damping=0.3,
            )
            if change < 5e-4:
                break
        beliefs = compute_beliefs_with_uniqueness(
            domains, edges_per_cell, pids_per_cell, pairs, m_var2fac,
            cell_to_pairs, avail,
        )
        new_avail = piece_availability(beliefs, pids_per_cell)
        d_avail = np.abs(new_avail - avail).max()
        avail = 0.5 * avail + 0.5 * new_avail
        if d_avail < 1e-4:
            break

    beliefs = compute_beliefs_with_uniqueness(
        domains, edges_per_cell, pids_per_cell, pairs, m_var2fac,
        cell_to_pairs, avail,
    )
    H = cell_entropies(beliefs)
    elapsed = time.time() - t0
    print(f"BP converged in {elapsed:.1f}s. Mean H: corner={H[[p for p in range(N) if cell_class(p)=='corner']].mean():.3f}, "
          f"edge={H[[p for p in range(N) if cell_class(p)=='edge']].mean():.3f}, "
          f"interior={H[[p for p in range(N) if cell_class(p)=='interior']].mean():.3f}")

    out_marginals = []
    for pos in range(N):
        b = beliefs[pos]
        D = domains[pos]
        states = []
        ranked = np.argsort(-b)
        for rank, s_idx in enumerate(ranked):
            marg = float(b[s_idx])
            if marg < MIN_MARGINAL:
                break
            pid, rot = D[s_idx]
            states.append({"piece_id": int(pid), "rotation": int(rot),
                           "marginal": marg, "rank": int(rank)})
        x, y = pos % SIZE, pos // SIZE
        out_marginals.append({
            "pos": int(pos), "x": int(x), "y": int(y),
            "class": cell_class(pos),
            "entropy": float(H[pos]),
            "n_states": len(D),
            "n_kept_states": len(states),
            "states": states,
        })

    out = {
        "schema_version": 1,
        "size": SIZE,
        "n_cells": N,
        "bp_config": {"damping": 0.3, "uniqueness_outer_rounds": "until convergence",
                      "min_marginal_kept": MIN_MARGINAL},
        "stats": {
            "convergence_time_s": elapsed,
            "mean_H_corner": float(H[[p for p in range(N) if cell_class(p)=='corner']].mean()),
            "mean_H_edge": float(H[[p for p in range(N) if cell_class(p)=='edge']].mean()),
            "mean_H_interior": float(H[[p for p in range(N) if cell_class(p)=='interior']].mean()),
        },
        "marginals": out_marginals,
    }
    OUT = ROOT / "output" / "v11_sp" / "bp_marginals.json"
    with OUT.open("w") as f:
        json.dump(out, f)
    sz = OUT.stat().st_size
    print(f"Saved {OUT.relative_to(ROOT)} ({sz/1024:.1f} KiB)")


if __name__ == "__main__":
    main()
