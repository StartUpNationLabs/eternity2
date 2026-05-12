#!/usr/bin/env python3
"""BP with soft piece-uniqueness re-weighting between iterations.

After each BP pass, we compute per-piece total occupancy = sum across cells
of marginal probability. If a piece's total exceeds 1, the cells using
that piece are dampened (multiplied by 1/occ[pid]).

This is the classic soft-alldiff trick from BP-for-CSP literature
(Maneva-Mossel-Wainwright 2007 used a similar reweighting for SAT).

We inject the reweighting as a *factor* applied to the var2fac messages
(multiplying state probabilities by piece-availability) so it propagates
naturally through BP rather than being a hard external rescale.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from v11_load_e2 import load
from v11_factor_graph import build_domains, adjacency_pairs, cell_class, SIZE, N
from v11_bp import precompute_state_info, build_message_index, compute_beliefs, cell_entropies, EPS


def piece_availability(beliefs, pids_per_cell) -> np.ndarray:
    """Per-piece availability factor: 1 / max(1, occupancy)."""
    occ = np.zeros(256, dtype=np.float64)
    for pos, b in enumerate(beliefs):
        P = pids_per_cell[pos]
        np.add.at(occ, P, b)
    # availability[p] in (0, 1]: a piece occupied 2x gets factor 0.5
    avail = 1.0 / np.maximum(1.0, occ)
    return avail


def bp_iteration_with_uniqueness(
    domains, edges_per_cell, pids_per_cell, pairs, m_var2fac, cell_to_pairs,
    avail: np.ndarray,
    damping: float = 0.3,
) -> float:
    """One BP iteration that includes a per-state availability factor."""
    new_m_var2fac: Dict[Tuple[int, int], np.ndarray] = {}
    NCOLORS = 23

    # Bucket var2fac messages by color (as before), but weight each state by
    # its current availability factor (avail[pid]) so the soft-uniqueness
    # constraint is folded into the bucketed sum.
    bucketed: Dict[Tuple[int, int], np.ndarray] = {}
    for pair_idx, (a, b, side_ab) in enumerate(pairs):
        side_a = side_ab
        side_b = (side_ab + 2) % 4
        mva = m_var2fac[(pair_idx, 0)]
        mvb = m_var2fac[(pair_idx, 1)]
        Ea = edges_per_cell[a][:, side_a]
        Eb = edges_per_cell[b][:, side_b]
        avA = avail[pids_per_cell[a]]
        avB = avail[pids_per_cell[b]]
        bucketed[(pair_idx, 0)] = np.bincount(Ea, weights=mva * avA, minlength=NCOLORS)
        bucketed[(pair_idx, 1)] = np.bincount(Eb, weights=mvb * avB, minlength=NCOLORS)

    total_change = 0.0
    for pos in range(N):
        D = len(domains[pos])
        if D == 0:
            continue
        log_belief = np.zeros(D, dtype=np.float64)
        # State prior includes piece availability: a state's probability is
        # discounted if its piece is already heavily claimed elsewhere.
        log_prior = np.log(np.maximum(avail[pids_per_cell[pos]], EPS))
        log_belief += log_prior

        incoming_msgs: List[Tuple[int, int, np.ndarray]] = []
        for (pair_idx, who, my_side, _other) in cell_to_pairs[pos]:
            other_who = 1 - who
            my_colors = edges_per_cell[pos][:, my_side]
            m_f_to_pos = bucketed[(pair_idx, other_who)][my_colors]
            np.maximum(m_f_to_pos, EPS, out=m_f_to_pos)
            log_belief += np.log(m_f_to_pos)
            incoming_msgs.append((pair_idx, who, m_f_to_pos))

        for pair_idx, who, m_f_to_pos in incoming_msgs:
            log_outgoing = log_belief - np.log(np.maximum(m_f_to_pos, EPS))
            log_outgoing -= log_outgoing.max()
            new_msg = np.exp(log_outgoing)
            s = new_msg.sum()
            if s > 0:
                new_msg /= s
            old = m_var2fac[(pair_idx, who)]
            damped = (1.0 - damping) * old + damping * new_msg
            ds = damped.sum()
            if ds > 0:
                damped /= ds
            change = np.abs(damped - old).sum()
            total_change += change
            new_m_var2fac[(pair_idx, who)] = damped
    for k, v in new_m_var2fac.items():
        m_var2fac[k] = v
    return total_change


def compute_beliefs_with_uniqueness(
    domains, edges_per_cell, pids_per_cell, pairs, m_var2fac, cell_to_pairs,
    avail: np.ndarray,
):
    """Beliefs that include the availability factor."""
    NCOLORS = 23
    bucketed: Dict[Tuple[int, int], np.ndarray] = {}
    for pair_idx, (a, b, side_ab) in enumerate(pairs):
        side_a = side_ab
        side_b = (side_ab + 2) % 4
        mva = m_var2fac[(pair_idx, 0)]
        mvb = m_var2fac[(pair_idx, 1)]
        Ea = edges_per_cell[a][:, side_a]
        Eb = edges_per_cell[b][:, side_b]
        avA = avail[pids_per_cell[a]]
        avB = avail[pids_per_cell[b]]
        bucketed[(pair_idx, 0)] = np.bincount(Ea, weights=mva * avA, minlength=NCOLORS)
        bucketed[(pair_idx, 1)] = np.bincount(Eb, weights=mvb * avB, minlength=NCOLORS)
    beliefs: List[np.ndarray] = []
    for pos in range(N):
        D = len(domains[pos])
        log_b = np.log(np.maximum(avail[pids_per_cell[pos]], EPS))
        for (pair_idx, who, my_side, _other) in cell_to_pairs[pos]:
            other_who = 1 - who
            my_colors = edges_per_cell[pos][:, my_side]
            m_f_to_pos = bucketed[(pair_idx, other_who)][my_colors]
            np.maximum(m_f_to_pos, EPS, out=m_f_to_pos)
            log_b += np.log(m_f_to_pos)
        log_b -= log_b.max()
        b = np.exp(log_b)
        if b.sum() > 0:
            b /= b.sum()
        beliefs.append(b)
    return beliefs


def main():
    puzzle = load()
    domains = build_domains(puzzle)
    edges_per_cell, pids_per_cell = precompute_state_info(puzzle, domains)
    pairs, m_var2fac, cell_to_pairs = build_message_index(domains)

    print(f"E2 BP+softUniqueness: {N} cells, {len(pairs)} pairs, "
          f"{sum(len(d) for d in domains)} states")

    avail = np.ones(256, dtype=np.float64)  # start unconstrained
    max_iter = 500
    tol = 1e-3
    damping = 0.3
    t0 = time.time()

    # Outer loop: BP to convergence, update avail, repeat until avail stable.
    outer_rounds = 12
    for outer in range(1, outer_rounds + 1):
        for it in range(1, max_iter + 1):
            change = bp_iteration_with_uniqueness(
                domains, edges_per_cell, pids_per_cell,
                pairs, m_var2fac, cell_to_pairs, avail,
                damping=damping
            )
            if change < tol:
                break
        beliefs = compute_beliefs_with_uniqueness(
            domains, edges_per_cell, pids_per_cell, pairs, m_var2fac,
            cell_to_pairs, avail
        )
        H = cell_entropies(beliefs)
        new_avail = piece_availability(beliefs, pids_per_cell)
        # Damped availability update too.
        avail = 0.5 * avail + 0.5 * new_avail
        elapsed = time.time() - t0
        # Stats
        occ = np.zeros(256)
        for pos, b in enumerate(beliefs):
            np.add.at(occ, pids_per_cell[pos], b)
        max_occ = occ.max()
        print(f"outer {outer:2d}: inner_iters={it} mean_H={H.mean():.4f} "
              f"max_occ={max_occ:.4f} avg_occ={occ.mean():.4f} t={elapsed:.1f}s")

    # Final stats
    beliefs = compute_beliefs_with_uniqueness(
        domains, edges_per_cell, pids_per_cell, pairs, m_var2fac,
        cell_to_pairs, avail
    )
    H = cell_entropies(beliefs)
    print()
    print("=== Final per-cell entropy summary ===")
    for cls in ("corner", "edge", "interior"):
        idxs = [pos for pos in range(N) if cell_class(pos) == cls]
        Hs = H[idxs]
        max_logD = np.log(max(len(domains[p]) for p in idxs))
        print(f"  {cls:>9s}: n={len(idxs)} mean_H={Hs.mean():.4f} "
              f"max_H={Hs.max():.4f} min_H={Hs.min():.4f} max_log|D|={max_logD:.4f} "
              f"reduction_vs_uniform={1 - Hs.mean()/max_logD:.1%}")

    # Save final marginals for downstream use
    import json
    out = {
        "mean_H_per_class": {
            cls: float(np.mean([H[p] for p in range(N) if cell_class(p) == cls]))
            for cls in ("corner", "edge", "interior")
        },
        "max_piece_occupancy": float(piece_availability.__globals__["np"].max(
            np.array([sum(beliefs[pos][s] for pos in range(N) for s, pid in enumerate(pids_per_cell[pos]) if pid == p) for p in range(256)])
        )) if False else None,
    }
    # Simpler save
    occ = np.zeros(256)
    for pos, b in enumerate(beliefs):
        np.add.at(occ, pids_per_cell[pos], b)
    out["max_piece_occupancy"] = float(occ.max())
    out["per_cell_entropy"] = H.tolist()
    out["non_hint_occ_summary"] = {
        "min": float(occ[occ > 0].min()),
        "max": float(occ.max()),
        "mean": float(occ.mean()),
        "median": float(np.median(occ)),
    }
    OUT = ROOT / "output" / "v11_sp" / "bp_uniq_results.json"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved results to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
