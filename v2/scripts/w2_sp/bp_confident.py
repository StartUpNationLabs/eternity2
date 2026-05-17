"""W2 — BP-confident decimation: only commit to high-confidence cells.

Variant of bp_decimation.py:
  - Run BP.
  - Fix ALL cells whose top-candidate has prob ≥ threshold (default 0.9).
  - Re-run BP.
  - Stop when no more cells exceed threshold.

The resulting partial board has HIGH-CONFIDENCE assignments only. Then
hand off to CSP backtracker (solver-engine) for the remaining cells.

Usage:
  python3 bp_confident.py <puzzle.csv> [--threshold 0.9] [--out partial.json]
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


def bp_confident_decimation(
    puzzle: Puzzle,
    initial_pinned: dict | None = None,
    threshold: float = 0.9,
    bp_max_iter: int = 100,
    bp_tol: float = 1e-4,
    damping: float = 0.5,
    max_rounds: int = 100,
    verbose: bool = True,
) -> dict:
    pinned = dict(initial_pinned or {})
    n_cells = puzzle.size * puzzle.size

    t0 = time.time()
    for round_num in range(max_rounds):
        solver = SPSolver(puzzle, pinned=pinned)
        if verbose:
            print(f"  round {round_num}: {len(pinned)} pinned", flush=True)

        solver.initialize_messages()
        for it in range(bp_max_iter):
            change = solver.iterate(np.zeros(puzzle.n_pieces), damping=damping)
            if change < bp_tol:
                break

        beliefs = solver.compute_beliefs(np.zeros(puzzle.n_pieces))

        # Find all cells with prob >= threshold
        new_fixes = []
        for pos in range(n_cells):
            if pos in pinned: continue
            b = beliefs[pos]
            if len(b) == 0:
                if verbose: print(f"  DEAD-END at cell {pos}", flush=True)
                return {'pinned': pinned, 'dead_end': True, 'time_s': time.time() - t0}
            i = int(np.argmax(b))
            prob = float(b[i])
            if prob >= threshold:
                new_fixes.append((pos, solver.cell_choices[pos][i], prob))

        if not new_fixes:
            if verbose:
                # Find the highest-confidence unfixed cell for info
                max_b = 0.0
                for pos in range(n_cells):
                    if pos in pinned: continue
                    b = beliefs[pos]
                    if len(b) > 0:
                        max_b = max(max_b, float(np.max(b)))
                print(f"  no new high-conf cells; max remaining = {max_b:.4f}", flush=True)
            break

        for pos, choice, prob in new_fixes:
            pinned[pos] = choice
        if verbose:
            avg_prob = np.mean([p for _, _, p in new_fixes])
            print(f"    fixed {len(new_fixes)} cells (avg_prob={avg_prob:.4f})", flush=True)

    elapsed = time.time() - t0
    return {'pinned': pinned, 'dead_end': False, 'time_s': elapsed}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle")
    ap.add_argument("--threshold", type=float, default=0.9)
    ap.add_argument("--bp-iter", type=int, default=100)
    ap.add_argument("--damping", type=float, default=0.5)
    ap.add_argument("--use-hints", action='store_true')
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    p = load_puzzle(args.puzzle)
    print(f"Puzzle: size={p.size} pieces={p.n_pieces} threshold={args.threshold}")

    initial = {}
    if args.use_hints:
        for h in p.hints:
            initial[h.position] = (h.piece_id, h.rotation)
        print(f"Initial pinned: {len(initial)}")

    result = bp_confident_decimation(
        p, initial_pinned=initial,
        threshold=args.threshold,
        bp_max_iter=args.bp_iter,
        damping=args.damping,
    )

    pinned = result['pinned']
    print(f"\nFinal: {len(pinned)}/{p.size*p.size} pinned (dead_end={result['dead_end']}, time={result['time_s']:.1f}s)")

    if args.out:
        placement = [
            {'pos': pos, 'piece_id': pid, 'rotation': rot}
            for pos, (pid, rot) in sorted(pinned.items())
        ]
        out = {
            'source': 'vol123_w2_bp_confident',
            'threshold': args.threshold,
            'puzzle_size': p.size,
            'n_placed': len(placement),
            'placement': placement,
        }
        args.out.write_text(json.dumps(out, indent=2))
        print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
