"""W2 analysis: run BP on the standing 459 board to identify "weak" cells.

For each cell in the 459 board, BP computes marginal probabilities.
If the board's current piece at that cell has LOW marginal probability,
that cell is a candidate for "wrong placement". Targeting ALNS on those
cells might escape the 459 plateau.

Approach:
  1. Load the 459 board.
  2. Run BP on the puzzle (no piece pinning).
  3. For each cell, check the probability that BP assigns to the current
     (pid, rot) at that cell.
  4. Rank cells by (low_prob = potentially wrong).
  5. Output: list of N "weakest" cells.

This is a novel use of BP marginals.
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
    ap.add_argument("board_json")
    ap.add_argument("--n-weakest", type=int, default=20)
    ap.add_argument("--damping", type=float, default=0.5)
    ap.add_argument("--max-iter", type=int, default=100)
    args = ap.parse_args()

    p = load_puzzle(args.puzzle)
    board_data = json.load(open(args.board_json))
    placement = {pp['pos']: (pp['piece_id'], pp['rotation']) for pp in board_data['placement']}
    print(f"Loaded {len(placement)} cells from board")

    # Pin the 5 canonical hints
    pinned = {h.position: (h.piece_id, h.rotation) for h in p.hints}
    print(f"Pinning {len(pinned)} canonical hints")

    # Run BP on the puzzle (with only hints pinned)
    solver = SPSolver(p, pinned=pinned)
    solver.initialize_messages()
    print("Running BP...")
    t0 = time.time()
    for it in range(args.max_iter):
        change = solver.iterate(np.zeros(p.n_pieces), damping=args.damping)
        if change < 1e-4: break
    beliefs = solver.compute_beliefs(np.zeros(p.n_pieces))
    print(f"BP done in {time.time()-t0:.1f}s, iter {it}")

    # For each non-pinned cell, find the BP probability of the current placement
    cell_data = []
    for pos in range(p.size * p.size):
        if pos in pinned: continue
        if pos not in placement:
            continue
        current = placement[pos]
        # Find this (pid, rot) in solver.cell_choices[pos]
        choices = solver.cell_choices[pos]
        if current not in choices:
            # Wait, the choices were determined post-pinning; current piece might
            # be excluded because its pid is pinned elsewhere.
            cell_data.append({
                'pos': pos, 'y': pos // p.size, 'x': pos % p.size,
                'current': current, 'bp_prob_current': 0.0,
                'bp_max_prob': float(beliefs[pos].max()) if len(beliefs[pos]) > 0 else 0.0,
                'note': 'current not in BP choices',
            })
            continue
        i = choices.index(current)
        prob_current = float(beliefs[pos][i])
        max_prob = float(beliefs[pos].max())
        max_i = int(np.argmax(beliefs[pos]))
        top_choice = choices[max_i]
        cell_data.append({
            'pos': pos, 'y': pos // p.size, 'x': pos % p.size,
            'current': current, 'bp_prob_current': prob_current,
            'bp_max_prob': max_prob, 'bp_top_choice': top_choice,
            'rank_of_current': int((np.argsort(-beliefs[pos]) == i).nonzero()[0][0]) + 1,
        })

    # Sort by lowest bp_prob_current (likely wrong)
    cell_data.sort(key=lambda d: d['bp_prob_current'])

    print(f"\nTop {args.n_weakest} WEAKEST cells (lowest BP confidence in current placement):")
    print(f"{'pos':>4} ({'y':>2},{'x':>2}) current_(pid,rot) prob_curr rank_curr bp_top         max_prob")
    for d in cell_data[:args.n_weakest]:
        if 'bp_top_choice' in d:
            print(f"{d['pos']:>4} ({d['y']:>2},{d['x']:>2}) {str(d['current']):>10} {d['bp_prob_current']:.4f}    {d['rank_of_current']:>5}    {str(d['bp_top_choice']):>10}    {d['bp_max_prob']:.4f}")
        else:
            print(f"{d['pos']:>4} ({d['y']:>2},{d['x']:>2}) {str(d['current']):>10} {d['bp_prob_current']:.4f}    -        -        {d['bp_max_prob']:.4f} ({d['note']})")

    # Save full analysis
    out_path = Path('output/vol-123/w2/459_weakest_cells.json')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w') as f:
        # Convert tuples to lists for JSON
        for d in cell_data:
            d['current'] = list(d['current'])
            if 'bp_top_choice' in d:
                d['bp_top_choice'] = list(d['bp_top_choice'])
        json.dump({'cells': cell_data}, f, indent=2)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
