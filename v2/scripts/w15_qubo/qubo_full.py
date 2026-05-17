"""W15 — Full-board QUBO encoder for ANY edge-matching puzzle (works on
canonical E2 and on generated NxN test puzzles).

This is the FULL-puzzle formulation (not border-only). Variables:
  x[piece_idx, rot, cell] = 1 if piece at (rot, cell)

Constraints (as penalties):
  C1. Each cell has exactly one piece: sum_{p,r} x[p,r,c] = 1
  C2. Each piece appears at exactly one cell: sum_{c,r} x[p,r,c] = 1
  C3. Hints forced as unit clauses (if applicable).

Objective: maximize number of matched interior edges.
"""

from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "w1_peps"))
from puzzle_loader import Puzzle, load_puzzle, BORDER


def valid_rotations_for_cell(puzzle: Puzzle, pid: int, pos: int) -> list[int]:
    """All rotations r such that placing piece pid at pos with rotation r
    has BORDER on the right sides (if on perimeter) and not BORDER on internal
    sides."""
    W = puzzle.size
    row, col = pos // W, pos % W
    out = []
    for r in range(4):
        n, e, s, w = puzzle.piece_edges(pid, r)
        if row == 0 and n != BORDER: continue
        if row == W-1 and s != BORDER: continue
        if col == 0 and w != BORDER: continue
        if col == W-1 and e != BORDER: continue
        if row != 0 and n == BORDER: continue
        if row != W-1 and s == BORDER: continue
        if col != 0 and w == BORDER: continue
        if col != W-1 and e == BORDER: continue
        out.append(r)
    return out


def build_var_index(puzzle: Puzzle):
    """Map (pid, rot, pos) → variable index for the full puzzle.
    Only valid (piece, rot, cell) combos get vars."""
    W = puzzle.size
    n_cells = W * W
    var_idx = {}
    pos_to_vars = {pos: [] for pos in range(n_cells)}
    piece_to_vars = {pid: [] for pid in range(puzzle.n_pieces)}

    for pid in range(puzzle.n_pieces):
        for pos in range(n_cells):
            for rot in valid_rotations_for_cell(puzzle, pid, pos):
                idx = len(var_idx)
                var_idx[(pid, rot, pos)] = idx
                pos_to_vars[pos].append(idx)
                piece_to_vars[pid].append(idx)

    return var_idx, pos_to_vars, piece_to_vars


def adjacent_pairs(W: int):
    """All adjacent cell pairs in WxW grid. Each pair: (a, side_a, b, side_b)
    side codes: 0=N, 1=E, 2=S, 3=W. Returns each pair ONCE."""
    pairs = []
    for r in range(W):
        for c in range(W):
            pos = r*W + c
            if c < W-1:
                pairs.append((pos, 1, pos+1, 3))  # E↔W
            if r < W-1:
                pairs.append((pos, 2, pos+W, 0))  # S↔N
    return pairs


def edge_color(puzzle: Puzzle, pid: int, rot: int, side: int) -> int:
    return puzzle.piece_edges(pid, rot)[side]


def build_qubo(
    puzzle: Puzzle,
    lambda_cell: float = 50.0,
    lambda_piece: float = 50.0,
    use_hints: bool = True,
    hints: dict | None = None,
):
    """Build QUBO. Returns (model, x, var_idx, idx_to_tuple)."""
    from amplify import VariableGenerator
    var_idx, pos_to_vars, piece_to_vars = build_var_index(puzzle)
    n_vars = len(var_idx)

    gen = VariableGenerator()
    x = gen.array("Binary", n_vars)
    idx_to_tuple = {v: k for k, v in var_idx.items()}

    # Objective: -reward (maximize matches → minimize negative)
    objective = 0
    n_terms = 0
    W = puzzle.size
    for (pos_a, side_a, pos_b, side_b) in adjacent_pairs(W):
        # Group vars at pos_a by edge color on side_a
        vars_a_by_color = {}
        for idx_a in pos_to_vars[pos_a]:
            (pid_a, rot_a, _) = idx_to_tuple[idx_a]
            c = edge_color(puzzle, pid_a, rot_a, side_a)
            if c == BORDER:
                continue
            vars_a_by_color.setdefault(c, []).append(idx_a)
        vars_b_by_color = {}
        for idx_b in pos_to_vars[pos_b]:
            (pid_b, rot_b, _) = idx_to_tuple[idx_b]
            c = edge_color(puzzle, pid_b, rot_b, side_b)
            if c == BORDER:
                continue
            vars_b_by_color.setdefault(c, []).append(idx_b)
        for color, idxs_a in vars_a_by_color.items():
            if color not in vars_b_by_color:
                continue
            for ia in idxs_a:
                for ib in vars_b_by_color[color]:
                    objective -= x[ia] * x[ib]
                    n_terms += 1

    # Penalty C1: each cell has exactly one piece
    cell_pen = 0
    for pos in range(W*W):
        vlist = pos_to_vars[pos]
        if not vlist:
            continue
        s = sum(x[i] for i in vlist)
        cell_pen += (s - 1) ** 2

    # Penalty C2: each piece appears exactly once
    piece_pen = 0
    for pid in range(puzzle.n_pieces):
        vlist = piece_to_vars[pid]
        if not vlist:
            continue
        s = sum(x[i] for i in vlist)
        piece_pen += (s - 1) ** 2

    # Hint penalty: pin given hints
    hint_pen = 0
    if use_hints and hints:
        for pos, (pid, rot) in hints.items():
            key = (pid, rot, pos)
            if key in var_idx:
                idx = var_idx[key]
                hint_pen += (1 - x[idx]) ** 2  # force it to 1

    total = objective + lambda_cell * cell_pen + lambda_piece * piece_pen + 100.0 * hint_pen

    print(f"[QUBO full] n_vars={n_vars} | objective_terms={n_terms} "
          f"| λ_cell={lambda_cell} λ_piece={lambda_piece}")

    return total, x, var_idx, idx_to_tuple


def decode(sol, idx_to_tuple, n_vars):
    placements = []
    for idx in range(n_vars):
        if sol[idx] > 0.5:
            pid, rot, pos = idx_to_tuple[idx]
            placements.append({"pos": pos, "piece_id": pid, "rotation": rot})
    return placements


def score(placements, puzzle: Puzzle):
    """Score placement: matched interior edges + violations."""
    W = puzzle.size
    cells = {}
    for p in placements:
        cells.setdefault(p["pos"], []).append(p)
    duplicate_cells = sum(1 for ps in cells.values() if len(ps) > 1)
    empty_cells = sum(1 for pos in range(W*W) if pos not in cells)
    pieces_used = {}
    for p in placements:
        pieces_used.setdefault(p["piece_id"], []).append(p)
    duplicate_pieces = sum(1 for ps in pieces_used.values() if len(ps) > 1)

    pos_to_piece = {p["pos"]: p for p in placements if p["pos"] in cells and len(cells[p["pos"]]) == 1}

    matched_interior = 0
    total_interior = 0
    matched_border = 0
    total_border = 0
    for (a, sa, b, sb) in adjacent_pairs(W):
        if a not in pos_to_piece or b not in pos_to_piece:
            continue
        pa = pos_to_piece[a]; pb = pos_to_piece[b]
        ca = edge_color(puzzle, pa["piece_id"], pa["rotation"], sa)
        cb = edge_color(puzzle, pb["piece_id"], pb["rotation"], sb)
        is_border_side = (ca == BORDER) or (cb == BORDER)
        if is_border_side:
            total_border += 1
            if ca == cb: matched_border += 1
        else:
            total_interior += 1
            if ca == cb: matched_interior += 1

    return {
        "n_placements": len(placements),
        "empty_cells": empty_cells,
        "duplicate_cells": duplicate_cells,
        "duplicate_pieces": duplicate_pieces,
        "matched_interior": matched_interior,
        "total_interior": total_interior,
        "matched_border": matched_border,
        "total_border": total_border,
        "is_perfect": (empty_cells == 0 and duplicate_cells == 0
                       and duplicate_pieces == 0 and matched_interior == total_interior),
    }
