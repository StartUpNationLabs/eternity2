"""W2 stochastic BP-decimation: introduce randomness in cell-fix selection.

Variants:
  --select greedy: pick the cell with max marginal (deterministic).
  --select top-k-random: pick uniformly from top-K cells by max_prob.
  --select sample: sample a cell with prob ∝ max_prob.
  --select temperature: pick proportional to max_prob^(1/T).

For each chosen cell, also pick the piece-rotation:
  --fix-mode top: always pick the top-marginal piece (greedy).
  --fix-mode sample: sample piece-rotation proportional to its belief.

Goal: explore the variance of BP-decim outputs across seeds.
If different seeds find DIFFERENT 435-class boards, multi-start could win.

Usage:
  python3 bp_decim_stochastic.py <puzzle.csv> --seed N [--select greedy|sample|top-k-random]
"""
from __future__ import annotations
import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'w1_peps'))

from puzzle_loader import Puzzle, load_puzzle
from sp_e2 import SPSolver


def bp_decim_stochastic(
    puzzle: Puzzle,
    initial_pinned: dict | None,
    seed: int,
    select_mode: str = 'top-k-random',
    top_k: int = 3,
    fix_mode: str = 'top',
    bp_max_iter: int = 100,
    bp_tol: float = 1e-4,
    damping: float = 0.5,
    verbose: bool = True,
) -> dict:
    """Stochastic BP-decimation."""
    rng = random.Random(seed)
    np_rng = np.random.RandomState(seed)

    pinned = dict(initial_pinned or {})
    n_cells = puzzle.size * puzzle.size

    t0 = time.time()
    while len(pinned) < n_cells:
        solver = SPSolver(puzzle, pinned=pinned)
        solver.initialize_messages()
        for it in range(bp_max_iter):
            change = solver.iterate(np.zeros(puzzle.n_pieces), damping=damping)
            if change < bp_tol:
                break
        beliefs = solver.compute_beliefs(np.zeros(puzzle.n_pieces))

        # Collect candidate cells with their max_prob
        candidates = []
        for pos in range(n_cells):
            if pos in pinned: continue
            b = beliefs[pos]
            if len(b) == 0:
                if verbose: print(f"  DEAD-END: cell {pos} no choices", flush=True)
                return {'pinned': pinned, 'dead_end': True, 'time_s': time.time() - t0, 'seed': seed}
            candidates.append((pos, b))

        if not candidates:
            break

        # Pick cell based on select_mode
        if select_mode == 'greedy':
            best_idx = max(range(len(candidates)), key=lambda i: candidates[i][1].max())
            pos, b = candidates[best_idx]
        elif select_mode == 'top-k-random':
            sorted_cands = sorted(candidates, key=lambda c: -c[1].max())
            top = sorted_cands[:top_k]
            pos, b = rng.choice(top)
        elif select_mode == 'sample':
            probs = np.array([c[1].max() for c in candidates])
            probs = probs / probs.sum()
            idx = np_rng.choice(len(candidates), p=probs)
            pos, b = candidates[idx]
        elif select_mode == 'temperature':
            T = 0.5
            log_p = np.log(np.array([c[1].max() for c in candidates]) + 1e-12) / T
            log_p -= log_p.max()
            p = np.exp(log_p); p /= p.sum()
            idx = np_rng.choice(len(candidates), p=p)
            pos, b = candidates[idx]
        else:
            raise ValueError(f"unknown select_mode {select_mode}")

        # Pick (pid, rot)
        if fix_mode == 'top':
            i = int(np.argmax(b))
        elif fix_mode == 'sample':
            p = b / b.sum()
            i = int(np_rng.choice(len(b), p=p))
        else:
            raise ValueError
        choice = solver.cell_choices[pos][i]

        if verbose:
            elapsed = time.time() - t0
            y, x = pos // puzzle.size, pos % puzzle.size
            if (len(pinned) + 1) % 25 == 0:
                print(f"    [{len(pinned)+1:3d}] fix ({y},{x}) = piece {choice[0]} rot {choice[1]} prob {float(b[i]):.3f} t={elapsed:.0f}s", flush=True)
        pinned[pos] = choice

    return {'pinned': pinned, 'dead_end': False, 'time_s': time.time() - t0, 'seed': seed}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--select", choices=['greedy', 'top-k-random', 'sample', 'temperature'], default='top-k-random')
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--fix-mode", choices=['top', 'sample'], default='top')
    ap.add_argument("--use-hints", action='store_true')
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    p = load_puzzle(args.puzzle)
    print(f"Puzzle: size={p.size} K={p.n_colors}")

    initial = {}
    if args.use_hints:
        for h in p.hints:
            initial[h.position] = (h.piece_id, h.rotation)

    result = bp_decim_stochastic(
        p, initial_pinned=initial,
        seed=args.seed,
        select_mode=args.select,
        top_k=args.top_k,
        fix_mode=args.fix_mode,
    )

    pinned = result['pinned']
    print(f"\nFinal: {len(pinned)} pinned (seed={args.seed} select={args.select} fix={args.fix_mode} time={result['time_s']:.1f}s)")

    placement = [{'pos': pos, 'piece_id': pid, 'rotation': rot}
                 for pos, (pid, rot) in sorted(pinned.items())]
    out = {
        'source': f'vol123_w2_stochastic_bp_decim_seed{args.seed}_{args.select}_{args.fix_mode}',
        'seed': args.seed, 'select': args.select, 'fix_mode': args.fix_mode,
        'puzzle_size': p.size, 'n_placed': len(placement),
        'placement': placement,
    }
    args.out.write_text(json.dumps(out, indent=2))
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
