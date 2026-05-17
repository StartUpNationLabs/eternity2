"""W2 — Export BP marginals as CSP value-order JSON.

Plain BP on E2 factor graph (no Lagrangian) at canonical scale in ~3s.
Output JSON has per-cell (pid, rot) probabilities.

Usage:
  python3 export_marginals.py <puzzle.csv> [--use-hints] [--out out.json]
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'w1_peps'))

from puzzle_loader import Puzzle, load_puzzle
from sp_e2 import SPSolver


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle")
    ap.add_argument("--max-iter", type=int, default=100)
    ap.add_argument("--tol", type=float, default=1e-4)
    ap.add_argument("--damping", type=float, default=0.5)
    ap.add_argument("--use-hints", action='store_true')
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    p = load_puzzle(args.puzzle)
    print(f"Puzzle: size={p.size} pieces={p.n_pieces}")

    pinned = {}
    if args.use_hints:
        for h in p.hints:
            pinned[h.position] = (h.piece_id, h.rotation)
        print(f"Pinning {len(pinned)} hints")

    solver = SPSolver(p, pinned=pinned)
    solver.initialize_messages()

    t0 = time.time()
    for it in range(args.max_iter):
        change = solver.iterate(np.zeros(p.n_pieces), damping=args.damping)
        if it < 5 or it % 10 == 0:
            print(f"  iter {it}: change={change:.6e}")
        if change < args.tol:
            print(f"  converged at iter {it}")
            break

    beliefs = solver.compute_beliefs(np.zeros(p.n_pieces))
    print(f"Total: {time.time()-t0:.1f}s")

    # Build marginals JSON
    marginals = []
    for pos, choices in enumerate(solver.cell_choices):
        b = beliefs[pos]
        for i, (pid, rot) in enumerate(choices):
            prob = float(b[i])
            if prob > 1e-9:
                y, x = pos // p.size, pos % p.size
                marginals.append({
                    'cell': pos, 'y': y, 'x': x,
                    'piece_id': pid, 'rotation': rot,
                    'prob': prob,
                })

    marginals.sort(key=lambda m: (m['cell'], -m['prob']))

    output = {
        'puzzle_size': p.size,
        'puzzle_n_pieces': p.n_pieces,
        'method': 'plain BP (multi-class messages)',
        'damping': args.damping,
        'pinned_cells': len(pinned),
        'mean_max_prob': float(np.mean([b.max() for b in beliefs])),
        'min_max_prob': float(np.min([b.max() for b in beliefs])),
        'cells_max_prob_ge_0.5': sum(1 for b in beliefs if b.max() >= 0.5),
        'marginals': marginals,
    }
    args.out.write_text(json.dumps(output, indent=2))
    print(f"Wrote {len(marginals)} marginals to {args.out}")
    print(f"mean_max_prob = {output['mean_max_prob']:.4f}")
    print(f"min_max_prob = {output['min_max_prob']:.4f}")
    print(f"cells max_prob >= 0.5: {output['cells_max_prob_ge_0.5']}")


if __name__ == "__main__":
    main()
