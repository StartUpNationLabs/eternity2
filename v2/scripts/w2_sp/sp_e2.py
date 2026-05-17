"""W2 — Survey Propagation for Eternity II.

Implementation following Braunstein-Mézard-Zecchina 2002 (arXiv:cs/0212002).

The factor graph for E2:
  Variables (binary):
    x_{c, p, r} = 1 iff piece p is placed at cell c with rotation r.
    Total: n_cells × n_pieces × 4 variables.

  Factors:
    F_cell(c): exactly-one over { x_{c, p, r} : valid (p,r) for cell c }
    F_piece(p): exactly-one over { x_{c, p, r} : valid (c,r) for piece p }
    F_match(e): for interior edge e = (c_a, side_a, c_b, side_b),
      forbid configurations where the projected colors don't match.

This is NOT random k-SAT — it's a STRUCTURED factor graph. SP may or may not
converge. The bet is that SP's "cluster-aware" message-passing can succeed
where BP failed (vol-11/12 found BP gives 18.8% interior reduction; SP should
give MORE because it tracks the joint solution structure).

References:
  - Braunstein, Mézard, Zecchina. Survey propagation: An algorithm for
    satisfiability. Random Structures & Algorithms 27(2):201-226 (2005).
  - Marino, Parisi, Ricci-Tersenghi. Backtracking SP. Nature Comms 7:12996 (2016).
  - thibsej/SurveyPropagation (Python reference for random k-SAT).

For E2, we need to ADAPT SP for non-binary message passing because the
exactly-one factors are over many variables. The approach:
  - Use the "warning propagation" simplification (Braunstein 2002 sec 3).
  - Each cell has ONE active variable; treat the cell as a multi-class
    variable, and SP runs over MESSAGES from match-factors to cell-variables.

This is a substantial implementation. Start with the message-passing core,
then test on a small E2 instance.

Usage:
  python3 sp_e2.py <puzzle.csv> [--max-iter 100]
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


class SPFactorGraph:
    """Factor graph for E2 with multi-class cell variables.

    Variables: per-cell, takes values in {0..n_choices-1} where each choice is a
               valid (piece_id, rotation) for that cell.

    Factors: per interior edge, color-match constraint between two cells.

    The factor graph is BIPARTITE: variables on one side, factors on the other.
    Each edge in the factor graph carries a MESSAGE (variable → factor or
    factor → variable).
    """

    def __init__(self, puzzle: Puzzle):
        self.puzzle = puzzle
        self.size = puzzle.size
        self.n_cells = self.size * self.size

        # For each cell, compute the list of (pid, rot) compatible with border.
        # This is the "domain" of the cell variable.
        self.cell_choices: list[list[tuple[int, int]]] = []
        for pos in range(self.n_cells):
            y, x = pos // self.size, pos % self.size
            n_border = y == 0
            e_border = x == self.size - 1
            s_border = y == self.size - 1
            w_border = x == 0
            choices = []
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
                    choices.append((pid, rot))
            self.cell_choices.append(choices)

        # Per-cell: precompute, for each of cell's 4 sides, the color emitted by each choice.
        # cell_emit[pos][side][choice_idx] = color of that side for that choice.
        self.cell_emit: list[list[list[int]]] = []
        for pos in range(self.n_cells):
            emits = [[], [], [], []]  # N, E, S, W
            for pid, rot in self.cell_choices[pos]:
                sig = puzzle.piece_edges(pid, rot)
                for s in range(4):
                    emits[s].append(int(sig[s]))
            self.cell_emit.append(emits)

        # Edges: list of (cell_a, side_a, cell_b, side_b) for each interior edge.
        # Cell sides: 0=N, 1=E, 2=S, 3=W. side_a's color must equal side_b's color.
        # Adjacency: (a) right-of-a == b means side_a=E, side_b=W.
        #            (b) below-of-a == b means side_a=S, side_b=N.
        self.edges: list[tuple[int, int, int, int]] = []
        for y in range(self.size):
            for x in range(self.size):
                pos = y * self.size + x
                if x + 1 < self.size:
                    self.edges.append((pos, 1, pos + 1, 3))
                if y + 1 < self.size:
                    self.edges.append((pos, 2, pos + self.size, 0))

        # Filter to interior edges only (both sides non-border-emit color).
        # Actually: for the E2 problem, even border-adjacent edges have constraints,
        # since the BORDER side is automatically forced. Keep all edges.

    def print_stats(self):
        print(f"n_cells = {self.n_cells}")
        print(f"n_edges = {len(self.edges)}")
        sizes = [len(c) for c in self.cell_choices]
        print(f"cell domains: min={min(sizes)} mean={sum(sizes)/len(sizes):.1f} max={max(sizes)}")
        print(f"total var-domain-size product: ~10^{sum(np.log10(max(1, s)) for s in sizes):.1f}")
        # Per piece, count cell-rotation choices
        piece_cells = defaultdict(int)
        for pos, choices in enumerate(self.cell_choices):
            for pid, rot in choices:
                piece_cells[pid] += 1
        psize = list(piece_cells.values())
        print(f"piece-rotation slots per piece: min={min(psize)} mean={sum(psize)/len(psize):.1f} max={max(psize)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle")
    args = ap.parse_args()

    p = load_puzzle(args.puzzle)
    print(f"Puzzle: size={p.size} pieces={p.n_pieces} K={p.n_colors}")

    fg = SPFactorGraph(p)
    fg.print_stats()


if __name__ == "__main__":
    main()
