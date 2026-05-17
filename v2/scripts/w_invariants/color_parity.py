"""W-INVARIANTS: Color parity / invariant analysis for E2.

Inspired by polyomino-tiling impossibility proofs (Barequet, Ben-Shachar 2024).

For each color c, define indicator variables for cells emitting c on each side.
Sum these over the board → invariant that must hold for ANY full placement.
Mismatches at edges contribute differently from matches.

For E2: there are 22 interior colors. We can check parities like:
  - For each color c, the # of NORTH-emitting cells should equal the
    # of SOUTH-emitting cells across all interior edges (mass conservation).
  - For each color c, sum of (col-index × color-c-N-emission) should equal
    sum of (col-index × color-c-S-emission).

If a board violates any such invariant, it CAN'T be a 480 solution.

Goal: find invariants that 469 boards violate, providing a structural
diagnostic.

Usage:
  python3 color_parity.py <puzzle.csv> [board1.json board2.json ...]
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'w1_peps'))
from puzzle_loader import Puzzle, load_puzzle, BORDER


def compute_color_emissions(puzzle: Puzzle, placement: dict[int, tuple[int, int]]) -> dict:
    """For each color c and each side {N, E, S, W}, count emissions."""
    # Per-side per-color count
    side_color_count = {s: Counter() for s in ['N', 'E', 'S', 'W']}
    # Per-color total emissions
    color_total = Counter()

    for pos, (pid, rot) in placement.items():
        edges = puzzle.piece_edges(pid, rot)  # (N, E, S, W)
        for i, side in enumerate(['N', 'E', 'S', 'W']):
            c = edges[i]
            side_color_count[side][c] += 1
            color_total[c] += 1

    return {'side_color_count': side_color_count, 'color_total': color_total}


def check_mass_conservation(puzzle: Puzzle, placement: dict[int, tuple[int, int]]) -> dict:
    """For ANY full placement, each color c on N-sides must equal c on S-sides
    (interior horizontal mass conservation), and same for E vs W.

    INVARIANT: For any valid placement of ALL 256 pieces:
      sum_cells (1 if color c on N) - sum_cells (1 if color c on S) = ???

    Actually this depends on the puzzle pieces. Let me just compute the
    per-side per-color counts and check what equality holds.
    """
    em = compute_color_emissions(puzzle, placement)
    side_color = em['side_color_count']

    # Mass conservation: per interior edge, N-emission of bottom cell = S-emission of top cell.
    # Total N-emissions across all cells (except top row) should equal total S-emissions
    # across all cells (except bottom row) of the matching color.
    # Each cell contributes to N (if not in top row) and S (if not in bottom row).

    # For each color c, count N-emissions and S-emissions.
    # The DIFFERENCE (N-count - S-count) should equal the # of border-side emissions of c.
    # Wait, hmm — actually each piece has 4 sides; the assignment of sides to N/E/S/W
    # depends on rotation. So the per-color N/S counts depend on the placement.

    # Better invariant: # cells where color c appears on N - # where color c appears on S.
    # For the perfect placement, every interior edge color appears once on N-side of bottom
    # cell and once on S-side of top cell. So total color-c N-emissions = total color-c
    # S-emissions across interior edges. Border N-emissions are at top row only; border
    # S-emissions are at bottom row only.

    # Simpler check: per-color, what's the imbalance N-S? It should depend on row geometry.
    # In a fully-matched board:
    #   - Top row N-sides are BORDER (=0). Other rows N-sides are interior colors.
    #   - Bottom row S-sides are BORDER. Other rows S-sides are interior colors.
    #   - Interior edges: bottom cell's N = top cell's S. So same color on both sides.

    return {
        'n_per_color': dict(side_color['N']),
        's_per_color': dict(side_color['S']),
        'e_per_color': dict(side_color['E']),
        'w_per_color': dict(side_color['W']),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle")
    ap.add_argument("boards", nargs='+')
    args = ap.parse_args()

    p = load_puzzle(args.puzzle)
    print(f"Puzzle: size={p.size} colors={p.n_colors}")
    print()

    for board_path in args.boards:
        data = json.load(open(board_path))
        placement = {pp['pos']: (pp['piece_id'], pp['rotation']) for pp in data['placement']}
        em = check_mass_conservation(p, placement)
        score = data.get('score', '?')
        print(f"Board: {board_path}")
        print(f"  Cells: {len(placement)}")

        # Per-color N vs S balance
        print(f"  color  N    S    E    W    N-S  E-W")
        print(f"  -----  ---  ---  ---  ---  ---  ---")
        for c in range(p.n_colors):
            n = em['n_per_color'].get(c, 0)
            s = em['s_per_color'].get(c, 0)
            e = em['e_per_color'].get(c, 0)
            w = em['w_per_color'].get(c, 0)
            n_s_diff = n - s
            e_w_diff = e - w
            print(f"  {c:5d}  {n:3d}  {s:3d}  {e:3d}  {w:3d}  {n_s_diff:+4d}  {e_w_diff:+4d}")
        print()


if __name__ == "__main__":
    main()
