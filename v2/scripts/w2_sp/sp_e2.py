"""W2 — Survey Propagation for Eternity II (SP-Lagrangian).

Implementation of SP adapted for E2's structured factor graph.
See vault/concepts/w2-sp-for-e2-derivation.md for the math.

Algorithm:
  1. Build factor graph: variables = cells (multi-class over (pid, rot)),
     factors = color-match constraints between adjacent cells.
  2. Run message-passing:
     - Factor-to-variable msg: η_{F → c}[(p,r)] = sum over matching values
       at neighboring cell, weighted by their factor messages.
     - Variable-to-factor msg: χ_{c → F}[(p,r)] = prod of incoming factor
       messages from OTHER factors at c, times exp(-mu_p) Lagrangian.
  3. Compute beliefs (per-cell marginals): b_c[(p,r)] = prod of all
     incoming factor msgs at c times exp(-mu_p).
  4. Update Lagrangian μ: q_p = sum_c b_c projected to piece p; μ_p ← μ_p + η(q_p - 1).
  5. Iterate until convergence.

This is NOT classical SP (which works on CNF) — it's a multi-class SP variant
for structured factor graphs. Conceptually closer to BP with cluster awareness.

Usage:
  python3 sp_e2.py <puzzle.csv> [--max-iter 100] [--eta 0.3]
"""
from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'w1_peps'))
from puzzle_loader import Puzzle, load_puzzle, BORDER


class SPSolver:
    def __init__(self, puzzle: Puzzle, pinned: dict | None = None):
        self.puzzle = puzzle
        self.size = puzzle.size
        self.n_cells = self.size * self.size
        self.pinned = pinned or {}

        # Compute per-cell domain: list of (pid, rot) choices for each cell.
        self.cell_choices: list[list[tuple[int, int]]] = []
        pinned_pids = {pid for pid, _ in self.pinned.values()}
        for pos in range(self.n_cells):
            if pos in self.pinned:
                self.cell_choices.append([self.pinned[pos]])
                continue
            y, x = pos // self.size, pos % self.size
            n_b = y == 0
            e_b = x == self.size - 1
            s_b = y == self.size - 1
            w_b = x == 0
            choices = []
            for pid in range(puzzle.n_pieces):
                if pid in pinned_pids: continue
                for rot in range(4):
                    sig = puzzle.piece_edges(pid, rot)
                    cN, cE, cS, cW = sig
                    if n_b and cN != BORDER: continue
                    if e_b and cE != BORDER: continue
                    if s_b and cS != BORDER: continue
                    if w_b and cW != BORDER: continue
                    if not n_b and cN == BORDER: continue
                    if not e_b and cE == BORDER: continue
                    if not s_b and cS == BORDER: continue
                    if not w_b and cW == BORDER: continue
                    choices.append((pid, rot))
            self.cell_choices.append(choices)

        # Per-cell, per-side: emitted color for each choice.
        # cell_emit[pos][side][choice_idx] = color.
        self.cell_emit: list[list[list[int]]] = []
        for pos, choices in enumerate(self.cell_choices):
            emits = [[], [], [], []]  # N, E, S, W
            for pid, rot in choices:
                sig = puzzle.piece_edges(pid, rot)
                for s in range(4):
                    emits[s].append(int(sig[s]))
            self.cell_emit.append(emits)

        # Edges between adjacent cells: (cell_a, side_a, cell_b, side_b, edge_id).
        # side_a=E (1), side_b=W (3) for horizontal; side_a=S (2), side_b=N (0) for vertical.
        self.edges = []
        for y in range(self.size):
            for x in range(self.size):
                pos = y * self.size + x
                if x + 1 < self.size:
                    self.edges.append((pos, 1, pos + 1, 3))
                if y + 1 < self.size:
                    self.edges.append((pos, 2, pos + self.size, 0))

        # Build index: per cell, list of (edge_id, my_side) that touch this cell.
        self.cell_edges: list[list[tuple[int, int]]] = [[] for _ in range(self.n_cells)]
        for eid, (ca, sa, cb, sb) in enumerate(self.edges):
            self.cell_edges[ca].append((eid, sa))
            self.cell_edges[cb].append((eid, sb))

        # Per-piece, count piece-rotation slots across all cells (for Lagrangian).
        self.piece_slots = np.zeros(puzzle.n_pieces, dtype=np.int64)
        for pos, choices in enumerate(self.cell_choices):
            for pid, _rot in choices:
                self.piece_slots[pid] += 1

        # Messages: per edge, per direction, per cell-choice → float.
        # We'll use dicts indexed by (edge_id, direction) → numpy array of size domain.
        # Direction 0: cell_a → cell_b (i.e., msg from a sent through edge).
        # Direction 1: cell_b → cell_a.
        # Initialize to uniform.

    def initialize_messages(self):
        """Initialize all messages to uniform 1/domain_size."""
        self.msg_fwd = []  # msg[e] = array of size domain at cell_b
        self.msg_bwd = []  # msg[e] = array of size domain at cell_a
        for eid, (ca, sa, cb, sb) in enumerate(self.edges):
            n_a = len(self.cell_choices[ca])
            n_b = len(self.cell_choices[cb])
            self.msg_fwd.append(np.ones(n_b, dtype=np.float64) / max(1, n_b))
            self.msg_bwd.append(np.ones(n_a, dtype=np.float64) / max(1, n_a))

    def iterate(self, mu: np.ndarray, damping: float = 0.0) -> float:
        """One pass of BP-style message updates.

        Returns max change in any message (for convergence check).

        Update rule:
          msg_factor_e_from_a_to_b[(p_b, r_b)] = sum_{(p_a, r_a)} delta(color_match) * belief_a_marginal
        where belief_a_marginal is the cell-a belief INCLUDING all factors EXCEPT this edge.
        """
        max_change = 0.0
        new_msg_fwd = [None] * len(self.edges)
        new_msg_bwd = [None] * len(self.edges)

        # Pre-compute per-cell exp(-mu) per choice
        cell_lagrange: list[np.ndarray] = []
        for pos, choices in enumerate(self.cell_choices):
            la = np.array([np.exp(-mu[pid]) for pid, _ in choices], dtype=np.float64)
            cell_lagrange.append(la)

        # For each edge, compute new messages.
        for eid, (ca, sa, cb, sb) in enumerate(self.edges):
            n_a = len(self.cell_choices[ca])
            n_b = len(self.cell_choices[cb])

            # Compute "cell a's belief except this edge": product of msgs from all OTHER
            # factors at cell a, times Lagrangian.
            ba = cell_lagrange[ca].copy()
            for (eid2, side2) in self.cell_edges[ca]:
                if eid2 == eid: continue
                # Which direction msg arrives at cell ca?
                ca2, _sa2, cb2, _sb2 = self.edges[eid2]
                if cb2 == ca:
                    # msg_fwd[eid2] arrives at ca
                    ba *= self.msg_fwd[eid2]
                else:
                    # msg_bwd[eid2] arrives at ca
                    ba *= self.msg_bwd[eid2]

            # Compute "cell b's belief except this edge"
            bb = cell_lagrange[cb].copy()
            for (eid2, side2) in self.cell_edges[cb]:
                if eid2 == eid: continue
                ca2, _sa2, cb2, _sb2 = self.edges[eid2]
                if cb2 == cb:
                    bb *= self.msg_fwd[eid2]
                else:
                    bb *= self.msg_bwd[eid2]

            # Forward msg (a → b via edge): for each (p_b, r_b) at cell b, sum over
            # (p_a, r_a) at cell a where color matches.
            emit_a = self.cell_emit[ca][sa]  # list of color emitted by cell a on side sa, per choice
            emit_b = self.cell_emit[cb][sb]  # list of color emitted by cell b on side sb, per choice

            # For each value v_b at cell b: sum over v_a at cell a where emit_a[v_a] == emit_b[v_b].
            # Group cell a's belief by emit_a color.
            color_to_sum_a = defaultdict(float)
            for ia, color in enumerate(emit_a):
                color_to_sum_a[color] += ba[ia]
            # New msg fwd at cell b: per value at b, look up sum at matching color.
            new_fwd = np.array([color_to_sum_a[emit_b[ib]] for ib in range(n_b)], dtype=np.float64)
            # Normalize to prevent numerical overflow/underflow
            tot = new_fwd.sum()
            if tot > 0:
                new_fwd /= tot

            # Backward msg (b → a)
            color_to_sum_b = defaultdict(float)
            for ib, color in enumerate(emit_b):
                color_to_sum_b[color] += bb[ib]
            new_bwd = np.array([color_to_sum_b[emit_a[ia]] for ia in range(n_a)], dtype=np.float64)
            tot = new_bwd.sum()
            if tot > 0:
                new_bwd /= tot

            # Apply damping
            if damping > 0:
                new_fwd = damping * self.msg_fwd[eid] + (1 - damping) * new_fwd
                new_bwd = damping * self.msg_bwd[eid] + (1 - damping) * new_bwd

            # Track change
            change_fwd = float(np.max(np.abs(new_fwd - self.msg_fwd[eid])))
            change_bwd = float(np.max(np.abs(new_bwd - self.msg_bwd[eid])))
            max_change = max(max_change, change_fwd, change_bwd)
            new_msg_fwd[eid] = new_fwd
            new_msg_bwd[eid] = new_bwd

        self.msg_fwd = new_msg_fwd
        self.msg_bwd = new_msg_bwd
        return max_change

    def compute_beliefs(self, mu: np.ndarray) -> list[np.ndarray]:
        """For each cell, compute marginal belief over its choices."""
        cell_lagrange = []
        for pos, choices in enumerate(self.cell_choices):
            la = np.array([np.exp(-mu[pid]) for pid, _ in choices], dtype=np.float64)
            cell_lagrange.append(la)

        beliefs = []
        for pos in range(self.n_cells):
            b = cell_lagrange[pos].copy()
            for (eid, side) in self.cell_edges[pos]:
                ca, _sa, cb, _sb = self.edges[eid]
                if cb == pos:
                    b *= self.msg_fwd[eid]
                else:
                    b *= self.msg_bwd[eid]
            tot = b.sum()
            if tot > 0:
                b /= tot
            beliefs.append(b)
        return beliefs

    def piece_usage(self, beliefs: list[np.ndarray]) -> np.ndarray:
        """Expected usage of each piece across all cells."""
        q = np.zeros(self.puzzle.n_pieces, dtype=np.float64)
        for pos, choices in enumerate(self.cell_choices):
            b = beliefs[pos]
            for i, (pid, _rot) in enumerate(choices):
                q[pid] += b[i]
        return q


def lagrangian_sp_loop(
    solver: SPSolver,
    eta: float = 0.3,
    max_outer_iter: int = 50,
    max_inner_iter: int = 100,
    inner_tol: float = 1e-3,
    outer_tol: float = 0.05,
    damping: float = 0.5,
    verbose: bool = True,
) -> tuple[np.ndarray, list[np.ndarray], np.ndarray]:
    """SP-Lagrangian outer loop."""
    n_pieces = solver.puzzle.n_pieces
    mu = np.zeros(n_pieces)
    solver.initialize_messages()

    t0 = time.time()
    for outer in range(max_outer_iter):
        # Inner SP loop: iterate messages until convergence
        for inner in range(max_inner_iter):
            change = solver.iterate(mu, damping=damping)
            if change < inner_tol:
                break

        beliefs = solver.compute_beliefs(mu)
        q = solver.piece_usage(beliefs)
        gap = q - 1.0
        gap_inf = float(np.max(np.abs(gap)))

        if verbose and (outer < 5 or outer % 5 == 0):
            elapsed = time.time() - t0
            print(f"  outer {outer:3d}: inner={inner+1}  |q-1|∞={gap_inf:.5f}  "
                  f"max(q)={q.max():.3f}  min(q)={q.min():.3f}  t={elapsed:.1f}s",
                  flush=True)

        if gap_inf < outer_tol:
            print(f"  converged at outer={outer}", flush=True)
            break

        mu = mu + eta * gap

    return mu, beliefs, q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle")
    ap.add_argument("--eta", type=float, default=0.3)
    ap.add_argument("--max-iter", type=int, default=50)
    ap.add_argument("--max-inner", type=int, default=100)
    ap.add_argument("--tol", type=float, default=0.05)
    ap.add_argument("--damping", type=float, default=0.5)
    ap.add_argument("--use-hints", action='store_true')
    args = ap.parse_args()

    p = load_puzzle(args.puzzle)
    print(f"Puzzle: size={p.size} pieces={p.n_pieces} K={p.n_colors}", flush=True)

    pinned = {}
    if args.use_hints:
        for h in p.hints:
            pinned[h.position] = (h.piece_id, h.rotation)
        print(f"Pinning {len(pinned)} hints", flush=True)

    solver = SPSolver(p, pinned=pinned)
    sizes = [len(c) for c in solver.cell_choices]
    print(f"Cell domains: min={min(sizes)} mean={sum(sizes)/len(sizes):.1f} max={max(sizes)}")
    print(f"Edges: {len(solver.edges)}")
    print(f"Running SP-Lagrangian (eta={args.eta}, damping={args.damping})...")

    mu, beliefs, q = lagrangian_sp_loop(
        solver, eta=args.eta, max_outer_iter=args.max_iter,
        max_inner_iter=args.max_inner, outer_tol=args.tol,
        damping=args.damping,
    )

    print(f"\nFinal: max(q)={q.max():.4f} min(q)={q.min():.4f}")
    print(f"Belief entropy: top-cell maxprob = {max(b.max() for b in beliefs):.4f}")
    print(f"            mean maxprob = {np.mean([b.max() for b in beliefs]):.4f}")
    print(f"            min maxprob = {np.min([b.max() for b in beliefs]):.4f}")


if __name__ == "__main__":
    main()
