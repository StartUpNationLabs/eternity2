#!/usr/bin/env python3
"""Survey propagation (1RSB cavity method) for E2.

Reference: Mézard, Parisi, Zecchina 2002 "Analytic and Algorithmic Solution
of Random Satisfiability Problems"; Braunstein-Mézard-Zecchina 2005 "SP-y
and SP-decimation".

Adaptation to pairwise-CSP form (each factor is a binary edge-equality):

For each directed edge (variable v -> factor f), define a *cavity field*
η_{v→f}: a positive number representing the probability that v "must
take" the value(s) supporting f-satisfaction in the absence of f. (In
the SAT formulation η is a probability of being a "frozen literal".)

The SP update for binary CSP factors is:

  η_{f→v}(x) = "probability that factor f's other variable u sends a
                forbidden message about x" = product over u→f's
                non-supporting states.

For pairwise equality factor f = (v, u) with v exposing color c_v and
u exposing color c_u, factor satisfied iff c_v == c_u.

For each value x ∈ Domain[v], the factor's warning toward v is "f
forbids x" if every state of u that v=x demands has been excluded by
other factors. Concretely: warning probability =
  Pr[no compatible u-state] = ∏_{u-states s.t. c_u == c_v(x)} (1 -
  presence-of-state-s probability in u)

We track per-state η_{v→f}(x) ∈ [0,1]. SP updates:
  η_{v→f}(x) = (∏_{g ≠ f neighbors of v} weight_g(v,x))
                normalized.

For practical E2, this collapses to a per-color form on each edge:
  w_{v→f}(c) = ∑_{x : edge-c color of x = c} η_{v→f}(x)
We bucket by color exactly like BP. The 1RSB twist is the Parisi
parameter `m` ∈ (0, 1] that re-weights cluster mass:
  weight_g = w_g^m

Setting m = 1 → BP. Setting m → 0 → maximum-cluster-size (RS limit).
Standard SP for k-SAT uses m solved from a self-consistency equation;
for engineering, m ∈ {0.5, 0.8, 0.95} are typical sweep points.

This implementation: SP-m with m as a hyperparameter.
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
from v11_bp import precompute_state_info, build_message_index, cell_entropies, EPS


def sp_iteration(
    domains, edges_per_cell, pids_per_cell, pairs, m_var2fac, cell_to_pairs,
    avail: np.ndarray, m_parisi: float = 0.5, damping: float = 0.3,
) -> float:
    """SP iteration with Parisi parameter m_parisi.

    Compared to BP:
      - The bucketed factor sums are raised to the m_parisi power before
        multiplying into the belief log.
    """
    new_m_var2fac: Dict[Tuple[int, int], np.ndarray] = {}
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

    total_change = 0.0
    for pos in range(N):
        D = len(domains[pos])
        if D == 0:
            continue
        log_belief = np.zeros(D, dtype=np.float64)
        # State prior with availability and Parisi power.
        log_prior = m_parisi * np.log(np.maximum(avail[pids_per_cell[pos]], EPS))
        log_belief += log_prior

        incoming_msgs: List[Tuple[int, int, np.ndarray]] = []
        for (pair_idx, who, my_side, _other) in cell_to_pairs[pos]:
            other_who = 1 - who
            my_colors = edges_per_cell[pos][:, my_side]
            m_f_to_pos = bucketed[(pair_idx, other_who)][my_colors]
            np.maximum(m_f_to_pos, EPS, out=m_f_to_pos)
            # Parisi reweighting:
            log_belief += m_parisi * np.log(m_f_to_pos)
            incoming_msgs.append((pair_idx, who, m_f_to_pos))

        for pair_idx, who, m_f_to_pos in incoming_msgs:
            log_outgoing = log_belief - m_parisi * np.log(np.maximum(m_f_to_pos, EPS))
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


def compute_beliefs_sp(
    domains, edges_per_cell, pids_per_cell, pairs, m_var2fac, cell_to_pairs,
    avail, m_parisi=0.5,
):
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
        log_b = m_parisi * np.log(np.maximum(avail[pids_per_cell[pos]], EPS))
        for (pair_idx, who, my_side, _other) in cell_to_pairs[pos]:
            other_who = 1 - who
            my_colors = edges_per_cell[pos][:, my_side]
            m_f_to_pos = bucketed[(pair_idx, other_who)][my_colors]
            np.maximum(m_f_to_pos, EPS, out=m_f_to_pos)
            log_b += m_parisi * np.log(m_f_to_pos)
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
    avail = np.ones(256, dtype=np.float64)

    # Sweep over m_parisi to see how the marginals shift
    results = []
    print(f"E2 SP sweep over Parisi parameter m ∈ [0.1, 1.0]")
    print()
    for m_parisi in [1.0, 0.8, 0.5, 0.3, 0.15]:
        # Reset messages each sweep
        for pair_idx, (a, b, side_ab) in enumerate(pairs):
            m_var2fac[(pair_idx, 0)] = np.full(len(domains[a]), 1.0 / max(1, len(domains[a])))
            m_var2fac[(pair_idx, 1)] = np.full(len(domains[b]), 1.0 / max(1, len(domains[b])))
        avail = np.ones(256, dtype=np.float64)

        t0 = time.time()
        for it in range(1, 200):
            change = sp_iteration(domains, edges_per_cell, pids_per_cell,
                                  pairs, m_var2fac, cell_to_pairs, avail,
                                  m_parisi=m_parisi, damping=0.3)
            if change < 1e-3:
                break
        elapsed = time.time() - t0
        beliefs = compute_beliefs_sp(
            domains, edges_per_cell, pids_per_cell, pairs, m_var2fac,
            cell_to_pairs, avail, m_parisi=m_parisi
        )
        H = cell_entropies(beliefs)
        Hc = {cls: np.mean([H[p] for p in range(N) if cell_class(p) == cls])
              for cls in ("corner", "edge", "interior")}
        max_logD_int = np.log(max(len(domains[p]) for p in range(N) if cell_class(p) == "interior"))
        reduction = 1 - Hc["interior"] / max_logD_int
        print(f"  m={m_parisi:.2f}: iters={it} t={elapsed:.1f}s  H_corner={Hc['corner']:.3f} "
              f"H_edge={Hc['edge']:.3f} H_interior={Hc['interior']:.3f} "
              f"interior_reduction={reduction:.1%}")
        results.append((m_parisi, it, Hc, reduction))


if __name__ == "__main__":
    main()
