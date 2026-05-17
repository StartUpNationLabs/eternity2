"""W1 — Export PEPS per-cell-piece-rotation marginals as a value-order
heuristic for solver-engine CSP.

Strategy: don't aim for full PEPS solve at canonical scale. Instead, run ONE
Lagrangian dual to convergence, then dump P_i(piece=p, rot=r) for every
cell × piece × rotation. The CSP backtracker uses these as value-order
(highest-probability piece-rotation first), expected to drastically prune
the search tree.

Vol-12 BP value-order gave 18.84% interior reduction. PEPS marginals should
give much more (they include piece-uniqueness, vol-13's missing piece).

Usage:
  python3 peps_marginals_export.py <puzzle.csv> [--chi 64] [--max-iter 100]
                                    [--out marginals.json]
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from puzzle_loader import Puzzle, load_puzzle, BORDER
from peps_quimb_lagrangian import (
    build_piece_signature_lookup,
    build_cell_tensor_full,
    slice_cell_tensor,
    build_quimb_2d_tn,
    compute_log_Z,
    compute_Z_open_per_cell,
    lagrangian_loop,
)


def export_marginals(
    puzzle: Puzzle,
    mu: np.ndarray,
    chi: int,
    log_Z: float,
    Z_open: dict,
    out_path: Path,
):
    """Dump per-(cell, piece, rotation) marginal probabilities to JSON."""
    size = puzzle.size
    Z_full = float(np.exp(log_Z))
    marginals = []

    for i in range(size * size):
        y, x = i // size, i % size
        n_border = y == 0
        e_border = x == size - 1
        s_border = y == size - 1
        w_border = x == 0
        Zi = Z_open.get(i)
        if Zi is None: continue

        for pid in range(puzzle.n_pieces):
            for rot in range(4):
                sig = puzzle.piece_edges(pid, rot)
                cN, cE, cS, cW = sig
                if n_border and cN != BORDER: continue
                if e_border and cE != BORDER: continue
                if s_border and cS != BORDER: continue
                if w_border and cW != BORDER: continue
                if not n_border and cN == BORDER: continue
                if not e_border and cE == BORDER: continue
                if not s_border and cS == BORDER: continue
                if not w_border and cW == BORDER: continue
                idx = []
                if not n_border: idx.append(cN)
                if not e_border: idx.append(cE)
                if not s_border: idx.append(cS)
                if not w_border: idx.append(cW)
                if len(idx) == 0:
                    Z_open_val = float(Zi)
                else:
                    Z_open_val = float(Zi[tuple(idx)])
                prob = np.exp(-mu[pid]) * Z_open_val / Z_full
                if prob > 1e-9:
                    marginals.append({
                        'cell': i,
                        'y': y,
                        'x': x,
                        'piece_id': pid,
                        'rotation': rot,
                        'prob': prob,
                    })

    # Sort by (cell, prob desc) for readability
    marginals.sort(key=lambda m: (m['cell'], -m['prob']))

    output = {
        'puzzle_size': size,
        'puzzle_n_pieces': puzzle.n_pieces,
        'chi': chi,
        'log_Z': log_Z,
        'mu': mu.tolist(),
        'marginals': marginals,
    }
    out_path.write_text(json.dumps(output, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle")
    ap.add_argument("--chi", type=int, default=64)
    ap.add_argument("--eta", type=float, default=0.3)
    ap.add_argument("--max-iter", type=int, default=100)
    ap.add_argument("--tol", type=float, default=0.05)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--momentum", type=float, default=0.0)
    args = ap.parse_args()

    p = load_puzzle(args.puzzle)
    print(f"Puzzle: size={p.size} pieces={p.n_pieces} K={p.n_colors}")

    t0 = time.time()
    print(f"Running Lagrangian dual (chi={args.chi}, eta={args.eta}, max_iter={args.max_iter})...")
    mu, q, Z_open, log_Z = lagrangian_loop(
        p, chi=args.chi, eta_init=args.eta, max_iter=args.max_iter,
        tol=args.tol, momentum=args.momentum, eta_decay=0.0,
    )
    print(f"Dual converged in {time.time()-t0:.1f}s; final |q-1|∞={abs(q-1).max():.5f}")

    print(f"Exporting marginals to {args.out}...")
    export_marginals(p, mu, args.chi, log_Z, Z_open, args.out)
    print(f"Wrote {args.out}")
    print(f"Total time: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
