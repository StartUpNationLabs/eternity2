#!/usr/bin/env python3
"""Build the E2 factor graph and compute initial per-cell domains.

Variables: one per cell (256 total for 16x16).
Domain[pos]: list of (piece_id, rotation) tuples = "states" that satisfy
            border-class restriction + hint pin + rotation validity.

A state s = (pid, rot) at position `pos` is *valid* iff:
- The piece's class matches the cell's class:
    * corner cells (4 of them): only corner pieces (2 BORDER edges),
      and rotation orients both BORDER edges toward the frame.
    * edge cells (56 of them): only edge pieces (1 BORDER edge), and
      rotation orients that BORDER edge toward the frame.
    * interior cells (196 of them): only interior pieces (0 BORDER edges),
      and any of 4 rotations is allowed.
- If `pos` is a hint cell, the state must match the hinted (pid, rot).

This script just enumerates domains and reports their sizes — no BP yet.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from v11_load_e2 import load, rotate_edges, BORDER

SIZE = 16
N = SIZE * SIZE  # 256


def cell_class(pos: int) -> str:
    x, y = pos % SIZE, pos // SIZE
    on_top = (y == 0); on_bot = (y == SIZE - 1)
    on_left = (x == 0); on_right = (x == SIZE - 1)
    n_borders = int(on_top) + int(on_bot) + int(on_left) + int(on_right)
    if n_borders == 2:
        return "corner"
    if n_borders == 1:
        return "edge"
    return "interior"


def cell_border_mask(pos: int) -> tuple[bool, bool, bool, bool]:
    """Return (top, right, bottom, left) booleans: which sides face the frame."""
    x, y = pos % SIZE, pos // SIZE
    return (y == 0, x == SIZE - 1, y == SIZE - 1, x == 0)


def state_edges(pieces: np.ndarray, pid: int, rot: int) -> np.ndarray:
    """Return edges (top, right, bottom, left) after rotation."""
    return rotate_edges(pieces[pid], rot)


def state_valid_at(pos: int, pid: int, rot: int, pieces: np.ndarray) -> bool:
    """Is placing piece `pid` at rotation `rot` at `pos` compatible with the
    cell's border mask (BORDER edges face the frame, non-BORDER edges face
    interior)?"""
    edges = state_edges(pieces, pid, rot)
    mask = cell_border_mask(pos)
    for side in range(4):
        is_border_edge = edges[side] == BORDER
        faces_frame = mask[side]
        if is_border_edge != faces_frame:
            return False
    return True


def build_domains(puzzle: dict) -> list[list[tuple[int, int]]]:
    """Return domains: domains[pos] = list of (pid, rot) tuples."""
    pieces = puzzle["pieces"]
    hints = {pos: (pid, rot) for pos, pid, rot in puzzle["hints"]}

    domains: list[list[tuple[int, int]]] = []
    for pos in range(N):
        if pos in hints:
            pid, rot = hints[pos]
            assert state_valid_at(pos, pid, rot, pieces), \
                f"hint at pos={pos} not class-compatible"
            domains.append([(pid, rot)])
            continue
        cls = cell_class(pos)
        states: list[tuple[int, int]] = []
        for pid in range(256):
            # Filter by piece class
            piece_border_count = int((pieces[pid] == BORDER).sum())
            if cls == "corner" and piece_border_count != 2:
                continue
            if cls == "edge" and piece_border_count != 1:
                continue
            if cls == "interior" and piece_border_count != 0:
                continue
            for rot in range(4):
                if state_valid_at(pos, pid, rot, pieces):
                    states.append((pid, rot))
        domains.append(states)
    return domains


def adjacency_pairs() -> list[tuple[int, int, int]]:
    """List of (pos_a, pos_b, side) for every internal grid join.

    `side` is the side of `pos_a` that touches `pos_b`:
      0 = top    (pos_b is above pos_a)
      1 = right  (pos_b is to the right)
      2 = bottom (pos_b is below)
      3 = left   (pos_b is to the left)
    We only emit each pair once (right + bottom from each cell), yielding
    480 pairs for 16x16.
    """
    pairs = []
    for pos in range(N):
        x, y = pos % SIZE, pos // SIZE
        if x + 1 < SIZE:
            pairs.append((pos, pos + 1, 1))  # right neighbor
        if y + 1 < SIZE:
            pairs.append((pos, pos + SIZE, 2))  # bottom neighbor
    return pairs


OPPOSITE = {0: 2, 1: 3, 2: 0, 3: 1}


def summarize(puzzle: dict, domains: list[list[tuple[int, int]]]) -> None:
    sizes = [len(d) for d in domains]
    by_class = {"corner": [], "edge": [], "interior": []}
    for pos, s in enumerate(sizes):
        by_class[cell_class(pos)].append(s)
    print(f"total states across all cells: {sum(sizes)}")
    for cls, vals in by_class.items():
        if not vals:
            continue
        print(f"  {cls}: n_cells={len(vals)} min={min(vals)} max={max(vals)} mean={sum(vals)/len(vals):.1f}")
    pairs = adjacency_pairs()
    print(f"adjacency pairs (factors): {len(pairs)}")


def main():
    puzzle = load()
    domains = build_domains(puzzle)
    summarize(puzzle, domains)


if __name__ == "__main__":
    main()
