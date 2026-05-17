"""W2 — BP + decimation: iteratively run BP, fix most-biased cell, repeat.

This is the canonical "BP-guided search" pattern that has been shown to work
for k-SAT, graph coloring, and other CSP problems.

For E2:
  1. Run BP on the factor graph.
  2. Find the cell with highest max_prob (most decisive belief).
  3. Pin that cell to its top candidate.
  4. Repeat with the remaining unpinned cells.

At each step, the puzzle becomes more constrained, BP gives stronger signals,
and we should fix cells one by one until all are pinned. If BP ever gets
stuck (impossible configuration), we backtrack.

Compare to ALNS or random search: this is a GREEDY algorithm guided by BP.
The bet is that BP's marginals identify the "easiest" cells to fix first,
unlocking the rest progressively.

Usage:
  python3 bp_decimation.py <puzzle.csv> [--max-fixes N] [--out partial.json]
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

from puzzle_loader import Puzzle, load_puzzle, BORDER
from sp_e2 import SPSolver


def bp_decimation(
    puzzle: Puzzle,
    initial_pinned: dict | None = None,
    max_fixes: int | None = None,
    bp_max_iter: int = 100,
    bp_tol: float = 1e-4,
    damping: float = 0.5,
    verbose: bool = True,
) -> dict:
    """Run BP+decimation until max_fixes cells pinned (or all)."""
    pinned = dict(initial_pinned or {})
    n_cells = puzzle.size * puzzle.size
    target_fixes = max_fixes if max_fixes is not None else n_cells

    t0 = time.time()
    while len(pinned) < target_fixes and len(pinned) < n_cells:
        # Build solver with current pinned
        solver = SPSolver(puzzle, pinned=pinned)
        if verbose:
            sizes = [len(c) for c in solver.cell_choices]
            unpinned = [pos for pos in range(n_cells) if pos not in pinned]
            print(f"  [{len(pinned):3d} pinned] unpinned={len(unpinned)} mean_dom={np.mean(sizes):.1f} max_dom={max(sizes)}", flush=True)

        solver.initialize_messages()
        for it in range(bp_max_iter):
            change = solver.iterate(np.zeros(puzzle.n_pieces), damping=damping)
            if change < bp_tol:
                break

        beliefs = solver.compute_beliefs(np.zeros(puzzle.n_pieces))

        # Find the unpinned cell with the highest max_prob
        best = (-1.0, None, None)  # (max_prob, pos, (pid, rot))
        for pos in range(n_cells):
            if pos in pinned:
                continue
            b = beliefs[pos]
            if len(b) == 0:
                # No valid choices — dead-end. Could backtrack.
                if verbose: print(f"  DEAD-END: cell {pos} has no valid choices", flush=True)
                return {'pinned': pinned, 'dead_end': True, 'time_s': time.time() - t0}
            i = int(np.argmax(b))
            prob = float(b[i])
            if prob > best[0]:
                best = (prob, pos, solver.cell_choices[pos][i])

        max_prob, pos, choice = best
        if pos is None:
            if verbose: print(f"  no candidate, stopping", flush=True)
            break
        if verbose:
            y, x = pos // puzzle.size, pos % puzzle.size
            elapsed = time.time() - t0
            print(f"    fix cell ({y},{x}) = piece {choice[0]} rot {choice[1]} (prob {max_prob:.4f})  t={elapsed:.1f}s", flush=True)
        pinned[pos] = choice

    return {
        'pinned': pinned,
        'dead_end': False,
        'time_s': time.time() - t0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle")
    ap.add_argument("--max-fixes", type=int, default=None)
    ap.add_argument("--bp-iter", type=int, default=100)
    ap.add_argument("--damping", type=float, default=0.5)
    ap.add_argument("--use-hints", action='store_true')
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    p = load_puzzle(args.puzzle)
    print(f"Puzzle: size={p.size} pieces={p.n_pieces}")

    initial_pinned = {}
    if args.use_hints:
        for h in p.hints:
            initial_pinned[h.position] = (h.piece_id, h.rotation)
        print(f"Initial pinned (hints): {len(initial_pinned)}")

    result = bp_decimation(
        p, initial_pinned=initial_pinned,
        max_fixes=args.max_fixes,
        bp_max_iter=args.bp_iter,
        damping=args.damping,
    )

    pinned = result['pinned']
    print(f"\nFinal: {len(pinned)} pinned (dead_end={result['dead_end']}, time={result['time_s']:.1f}s)")

    if args.out:
        placement = [
            {'pos': pos, 'piece_id': pid, 'rotation': rot}
            for pos, (pid, rot) in sorted(pinned.items())
        ]
        out = {
            'source': 'vol123_w2_bp_decimation',
            'puzzle_size': p.size,
            'n_placed': len(placement),
            'placement': placement,
        }
        args.out.write_text(json.dumps(out, indent=2))
        print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
