"""W1 — Python CSP backtracker that uses PEPS marginals as value-order.

Goal: validate that PEPS marginals as value-order make CSP faster than
without. Compare on small generated puzzles.

This is a pedagogical implementation; the production version would be in
solver-engine (Rust). We mainly want to verify:
  1. Loading PEPS marginals from JSON works.
  2. Using them as value-order in a vanilla backtracking CSP works.
  3. CSP solves puzzles where PEPS alone didn't fully solve.

The CSP follows the same scan order as solver-engine (border-first MRV),
but at each cell uses the PEPS marginal ranking instead of bucket-listed
piece order.
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from puzzle_loader import Puzzle, load_puzzle, BORDER


def build_legal_options(puzzle: Puzzle) -> dict[int, list[tuple[int, int]]]:
    """For each cell, list of (piece_id, rotation) options consistent with border."""
    size = puzzle.size
    K = puzzle.n_colors
    out: dict[int, list[tuple[int, int]]] = {}
    for pos in range(size * size):
        y, x = pos // size, pos % size
        n_border = y == 0
        e_border = x == size - 1
        s_border = y == size - 1
        w_border = x == 0
        opts = []
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
                opts.append((pid, rot))
        out[pos] = opts
    return out


def order_cells_border_first(size: int) -> list[int]:
    """Border-first scan order: borders first, then interior rows."""
    cells = []
    # Top row
    for x in range(size):
        cells.append(0 * size + x)
    # Bottom row
    for x in range(size):
        cells.append((size - 1) * size + x)
    # Left column (excluding corners)
    for y in range(1, size - 1):
        cells.append(y * size + 0)
    # Right column (excluding corners)
    for y in range(1, size - 1):
        cells.append(y * size + (size - 1))
    # Interior
    for y in range(1, size - 1):
        for x in range(1, size - 1):
            cells.append(y * size + x)
    return cells


def csp_solve(
    puzzle: Puzzle,
    cell_order: list[int],
    options_per_cell: dict[int, list[tuple[int, int]]],
    value_order: dict[int, list[tuple[int, int]]] | None,
    deadline_s: float = 60.0,
) -> tuple[dict[int, tuple[int, int]] | None, dict]:
    """Backtracking CSP.

    cell_order: cells in fill order.
    value_order: per-cell priority list of (pid, rot) (high to low priority).
                 If None, uses options_per_cell directly.

    Returns (solution_or_none, stats).
    """
    size = puzzle.size
    n_cells = size * size
    placement: dict[int, tuple[int, int]] = {}
    used_pieces = [False] * puzzle.n_pieces
    nodes = [0]
    t_start = time.time()
    timeout = [False]

    def neighbors_edges_match(pos: int, pid: int, rot: int) -> bool:
        edges = puzzle.piece_edges(pid, rot)
        y, x = pos // size, pos % size
        # Check against already-placed neighbors
        if y > 0:
            up_pos = (y - 1) * size + x
            if up_pos in placement:
                up_pid, up_rot = placement[up_pos]
                up_edges = puzzle.piece_edges(up_pid, up_rot)
                if up_edges[2] != edges[0]:
                    return False
        if x > 0:
            left_pos = y * size + (x - 1)
            if left_pos in placement:
                lp, lr = placement[left_pos]
                le = puzzle.piece_edges(lp, lr)
                if le[1] != edges[3]:
                    return False
        return True

    def recurse(idx: int) -> bool:
        if timeout[0]: return False
        if idx == len(cell_order):
            return True
        if time.time() - t_start > deadline_s:
            timeout[0] = True
            return False

        pos = cell_order[idx]
        opts = (value_order.get(pos, options_per_cell[pos])
                if value_order is not None else options_per_cell[pos])

        for (pid, rot) in opts:
            if used_pieces[pid]: continue
            if not neighbors_edges_match(pos, pid, rot): continue
            placement[pos] = (pid, rot)
            used_pieces[pid] = True
            nodes[0] += 1
            if recurse(idx + 1):
                return True
            del placement[pos]
            used_pieces[pid] = False
            if timeout[0]: return False
        return False

    found = recurse(0)
    stats = {
        'nodes': nodes[0],
        'time_s': time.time() - t_start,
        'timeout': timeout[0],
        'found': found,
        'placed': len(placement),
    }
    if found:
        return dict(placement), stats
    return None, stats


def load_value_order(marginals_path: Path) -> dict[int, list[tuple[int, int]]]:
    """Build value-order: per cell, sort (pid, rot) by descending marginal probability."""
    data = json.loads(marginals_path.read_text())
    by_cell: dict[int, list[tuple[float, int, int]]] = defaultdict(list)
    for m in data['marginals']:
        by_cell[m['cell']].append((m['prob'], m['piece_id'], m['rotation']))
    out: dict[int, list[tuple[int, int]]] = {}
    for cell, lst in by_cell.items():
        lst.sort(key=lambda t: -t[0])  # descending prob
        out[cell] = [(pid, rot) for _, pid, rot in lst]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle")
    ap.add_argument("--marginals", type=Path, help="PEPS marginals JSON (skip if not given = vanilla)")
    ap.add_argument("--deadline", type=float, default=60.0)
    args = ap.parse_args()

    p = load_puzzle(args.puzzle)
    print(f"Puzzle: size={p.size} pieces={p.n_pieces}")

    cell_order = order_cells_border_first(p.size)
    opts = build_legal_options(p)
    print(f"Options per cell: min={min(len(v) for v in opts.values())}, "
          f"max={max(len(v) for v in opts.values())}")

    if args.marginals:
        print(f"Loading PEPS marginals from {args.marginals}")
        value_order = load_value_order(args.marginals)
    else:
        value_order = None

    print(f"\nRunning CSP {'with PEPS value-order' if value_order else 'vanilla'} "
          f"(deadline {args.deadline}s)...")
    sol, stats = csp_solve(p, cell_order, opts, value_order, deadline_s=args.deadline)
    print(f"Result: {stats}")
    if sol:
        print(f"FOUND solution with {len(sol)} cells")
    else:
        print(f"NO solution within deadline")


if __name__ == "__main__":
    main()
