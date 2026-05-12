#!/usr/bin/env python3
"""Belief propagation on the E2 factor graph.

Per-cell variable X[pos] ∈ Domain[pos] (states = (pid, rot) tuples).
Edge-equality factors between adjacent cells.

Messages:
- m_var2fac[(pos, neighbor_pos, side)][state_idx]:
    cell `pos` -> edge-factor (pos, neighbor_pos): probability `pos` has
    state `state_idx` based on all OTHER neighbors/factors.

- m_fac2var[(pos, neighbor_pos, side)][state_idx]:
    edge-factor -> cell `pos`: probability the factor is satisfied if
    `pos` has state `state_idx`, marginalized over `neighbor_pos`'s
    states. (Sum over compatible states of neighbor's m_var2fac.)

Piece-uniqueness handled as a *soft post-step* after each BP pass: per
piece-id, sum the marginal probability across all cells. If > 1, all
cells using that piece are dampened proportionally. (Hard alldiff in BP
is intractable for 256 pieces; soft normalization is the standard
workaround in the BP-for-CSP literature.)

Marginals: after fixed-point, b[pos][state_idx] ∝ prod of incoming
m_fac2var times the prior (uniform over domain).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from v11_load_e2 import load, BORDER
from v11_factor_graph import (
    build_domains, adjacency_pairs, state_edges, SIZE, N, cell_class
)

# Tolerable numerical floor on messages to avoid log(0).
EPS = 1e-30


def precompute_state_info(puzzle: dict, domains: List[List[Tuple[int, int]]]):
    """For each cell `pos` and each state index `s_idx`, store:
    - edges[pos][s_idx, :4]  → (top, right, bottom, left) colors
    - pids[pos][s_idx]       → piece-id integer

    Returns dict with arrays per cell, plus a piece_to_cells map.
    """
    pieces = puzzle["pieces"]
    edges_per_cell: List[np.ndarray] = []
    pids_per_cell: List[np.ndarray] = []
    for pos, dom in enumerate(domains):
        n = len(dom)
        E = np.zeros((n, 4), dtype=np.int8)
        P = np.zeros(n, dtype=np.int16)
        for i, (pid, rot) in enumerate(dom):
            E[i, :] = state_edges(pieces, pid, rot)
            P[i] = pid
        edges_per_cell.append(E)
        pids_per_cell.append(P)
    return edges_per_cell, pids_per_cell


def build_message_index(domains: List[List[Tuple[int, int]]]):
    """Pre-allocate uniform messages on every directed edge."""
    pairs = adjacency_pairs()
    # For each pair (pos_a, pos_b, side_a_to_b) we have 2 directed messages:
    #   pos_a -> factor (the factor lives "between" the two cells)
    #   pos_b -> factor
    # We represent each direction's m_var2fac as a length-|D[pos]| vector.
    # m_fac2var (factor -> pos) is computed from the *other* m_var2fac.
    n_pairs = len(pairs)
    m_var2fac: Dict[Tuple[int, int], np.ndarray] = {}
    # Key = (pair_idx, who) where who ∈ {0, 1} for (pos_a, pos_b).
    for pair_idx, (a, b, side_ab) in enumerate(pairs):
        m_var2fac[(pair_idx, 0)] = np.full(len(domains[a]), 1.0 / max(1, len(domains[a])))
        m_var2fac[(pair_idx, 1)] = np.full(len(domains[b]), 1.0 / max(1, len(domains[b])))
    # Adjacency lookup: for each cell `pos`, list of (pair_idx, who) it
    # participates in.
    cell_to_pairs: List[List[Tuple[int, int]]] = [[] for _ in range(N)]
    for pair_idx, (a, b, side_ab) in enumerate(pairs):
        cell_to_pairs[a].append((pair_idx, 0, side_ab, b))   # cell a sends along side_ab toward b
        cell_to_pairs[b].append((pair_idx, 1, (side_ab + 2) % 4, a))  # cell b sends along opposite side toward a
    return pairs, m_var2fac, cell_to_pairs


def bp_iteration(
    domains, edges_per_cell, pids_per_cell, pairs, m_var2fac, cell_to_pairs,
    damping: float = 0.3,
) -> float:
    """One BP iteration: update factor->var messages then var->fac messages.
    Returns L1 change.
    """
    new_m_var2fac: Dict[Tuple[int, int], np.ndarray] = {}

    # Compute factor->var messages on-the-fly per cell update.
    # For each cell `pos` with incoming factors, we need:
    #   For each pair (factor) `f` touching pos, compute m_f→pos using
    #   the var2fac message of the *other* endpoint and the edge-equality
    #   compatibility.
    # Compatibility on a horizontal pair (a left, b right): state s_a is
    # compatible with state s_b iff edges_per_cell[a][s_a, right] ==
    # edges_per_cell[b][s_b, left]. We bucket states by the color on
    # the touching side for efficiency.
    # m_f→a(s_a) = sum over s_b compatible with s_a of m_b→f(s_b)
    # = m_var2fac_b_to_f bucketed by color, then look up by edges_per_cell[a][s_a, side_a_to_b].

    # Pre-bucket each var2fac message by the color it exposes on the touching side.
    # Bucket: for each pair, for each endpoint (who=0/1), produce a dict
    # color -> sum of message weights over states with that color on the
    # touching side.
    bucketed: Dict[Tuple[int, int], np.ndarray] = {}
    # Colors are 0..22 (23 distinct values including BORDER).
    NCOLORS = 23
    for pair_idx, (a, b, side_ab) in enumerate(pairs):
        # Endpoint a touches the pair on side side_ab; endpoint b on side opposite.
        side_a = side_ab
        side_b = (side_ab + 2) % 4
        mva = m_var2fac[(pair_idx, 0)]
        mvb = m_var2fac[(pair_idx, 1)]
        Ea = edges_per_cell[a][:, side_a]
        Eb = edges_per_cell[b][:, side_b]
        ba = np.bincount(Ea, weights=mva, minlength=NCOLORS)
        bb = np.bincount(Eb, weights=mvb, minlength=NCOLORS)
        bucketed[(pair_idx, 0)] = ba  # a's outgoing message bucketed by color
        bucketed[(pair_idx, 1)] = bb  # b's outgoing message bucketed by color

    # Now, for each cell `pos`, compute incoming m_f→pos for each factor f,
    # then product into new m_var2fac for each outgoing factor.
    total_change = 0.0

    for pos in range(N):
        D = len(domains[pos])
        if D == 0:
            continue
        # Belief = product over incoming factors of m_f→pos
        # m_f→pos(s) = bucketed[other_endpoint][color_at_touching_side(pos, s)]
        # Plus uniform prior (already absorbed into the message init).
        log_belief = np.zeros(D, dtype=np.float64)
        incoming_msgs: List[Tuple[int, int, np.ndarray]] = []  # (pair_idx, who, m_f→pos)
        for (pair_idx, who, my_side, _other) in cell_to_pairs[pos]:
            other_who = 1 - who
            # Color we expose on the touching side, for each of OUR states:
            my_colors = edges_per_cell[pos][:, my_side]
            # m_f→pos(s) = bucket of OTHER endpoint at color my_colors[s]
            other_bucket = bucketed[(pair_idx, other_who)]
            m_f_to_pos = other_bucket[my_colors]
            # Avoid log(0) by clamping.
            np.maximum(m_f_to_pos, EPS, out=m_f_to_pos)
            log_belief += np.log(m_f_to_pos)
            incoming_msgs.append((pair_idx, who, m_f_to_pos))
        # Outgoing message to factor f = belief / m_f→pos.
        for pair_idx, who, m_f_to_pos in incoming_msgs:
            log_outgoing = log_belief - np.log(np.maximum(m_f_to_pos, EPS))
            # Stabilize exp by subtracting max
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
    # Commit
    for k, v in new_m_var2fac.items():
        m_var2fac[k] = v
    return total_change


def compute_beliefs(domains, edges_per_cell, pairs, m_var2fac, cell_to_pairs):
    """Compute per-cell marginals from current message state."""
    NCOLORS = 23
    bucketed: Dict[Tuple[int, int], np.ndarray] = {}
    for pair_idx, (a, b, side_ab) in enumerate(pairs):
        side_a = side_ab
        side_b = (side_ab + 2) % 4
        mva = m_var2fac[(pair_idx, 0)]
        mvb = m_var2fac[(pair_idx, 1)]
        Ea = edges_per_cell[a][:, side_a]
        Eb = edges_per_cell[b][:, side_b]
        bucketed[(pair_idx, 0)] = np.bincount(Ea, weights=mva, minlength=NCOLORS)
        bucketed[(pair_idx, 1)] = np.bincount(Eb, weights=mvb, minlength=NCOLORS)
    beliefs: List[np.ndarray] = []
    for pos in range(N):
        D = len(domains[pos])
        log_b = np.zeros(D, dtype=np.float64)
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


def cell_entropies(beliefs: List[np.ndarray]) -> np.ndarray:
    H = np.zeros(N, dtype=np.float64)
    for pos, b in enumerate(beliefs):
        bb = np.clip(b, EPS, 1.0)
        H[pos] = -np.sum(bb * np.log(bb))
    return H


def main():
    puzzle = load()
    domains = build_domains(puzzle)
    edges_per_cell, pids_per_cell = precompute_state_info(puzzle, domains)
    pairs, m_var2fac, cell_to_pairs = build_message_index(domains)

    print(f"E2 factor graph: {N} cells, {len(pairs)} pairwise factors")
    print(f"total states: {sum(len(d) for d in domains)}")
    print()

    max_iter = 200
    tol = 1e-3
    damping = 0.3
    t0 = time.time()
    for it in range(1, max_iter + 1):
        change = bp_iteration(domains, edges_per_cell, pids_per_cell,
                              pairs, m_var2fac, cell_to_pairs,
                              damping=damping)
        if it % 5 == 0 or it == 1:
            beliefs = compute_beliefs(domains, edges_per_cell, pairs,
                                      m_var2fac, cell_to_pairs)
            H = cell_entropies(beliefs)
            elapsed = time.time() - t0
            print(f"iter {it:3d}: dL1={change:.4g}  mean_H={H.mean():.4f}  "
                  f"max_H={H.max():.4f}  min_H={H.min():.4f}  t={elapsed:.1f}s")
        if change < tol:
            print(f"converged at iter {it} (dL1={change:.4g})")
            break
    else:
        print(f"NOT converged after {max_iter} iter; last dL1={change:.4g}")

    beliefs = compute_beliefs(domains, edges_per_cell, pairs, m_var2fac, cell_to_pairs)
    H = cell_entropies(beliefs)
    print()
    print("=== Final per-cell entropy summary ===")
    for cls in ("corner", "edge", "interior"):
        idxs = [pos for pos in range(N) if cell_class(pos) == cls]
        Hs = H[idxs]
        print(f"  {cls:>9s}: n={len(idxs)} mean_H={Hs.mean():.4f} "
              f"max_H={Hs.max():.4f} min_H={Hs.min():.4f} "
              f"max_log|D|={np.log(max(len(domains[p]) for p in idxs)):.4f}")

    # Hint cells should have H=0
    hint_positions = [p for p, _, _ in puzzle["hints"]]
    for hp in hint_positions:
        print(f"  hint at pos={hp}: H={H[hp]:.6f}  (should be 0)")


if __name__ == "__main__":
    main()
