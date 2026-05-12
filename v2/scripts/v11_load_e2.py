#!/usr/bin/env python3
"""Load canonical E2 puzzle + 5 official hints into a clean dict-of-arrays.

Format reference: crates/benchmark/src/loader.rs.

Each piece row in size_16_official_eternity.csv is:
    top,right,bottom,left, x, y, rotation

Colors are 16-bit binary strings. '1111111111111111' = 65535 = BORDER (color 0
in our convention); everything else is a small int color id (1, 2, ...).

Hint convention: (x, y, rotation) all-zero means "no hint". Hint pieces have
non-zero columns.

Output:
- pieces: numpy int8 [256, 4] with edge colors (top, right, bottom, left).
  Color 0 = BORDER; colors 1..22 = interior colors.
- hints: list of (position, piece_id, rotation) tuples, position = y*16 + x.
- color_count: number of distinct non-border colors actually present.

Validates that we have:
- 4 corners (2 border edges each)
- 56 edge pieces (1 border edge each)
- 196 interior pieces (0 border edges)
- 22 distinct interior colors
- 5 hints
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CSV = Path(__file__).resolve().parents[2] / "data" / "puzzles" / "size_16_official_eternity.csv"
BORDER = 0  # our convention; loader.rs maps 65535 -> 0


def parse_color(s: str) -> int:
    v = int(s.strip(), 2)
    if v == 65535:
        return BORDER
    if v > 255:
        raise ValueError(f"color {v} doesn't fit u8")
    return v


def load() -> dict:
    raw = CSV.read_text().splitlines()
    size = int(raw[0])
    if size != 16:
        raise ValueError(f"expected 16x16, got {size}")

    pieces = np.zeros((256, 4), dtype=np.int8)  # top, right, bottom, left
    hints: list[tuple[int, int, int]] = []
    n_pieces = 0
    for line in raw[1:]:
        line = line.strip()
        if not line:
            continue
        cols = line.split(",")
        if len(cols) < 4:
            continue
        t = parse_color(cols[0])
        r = parse_color(cols[1])
        b = parse_color(cols[2])
        l = parse_color(cols[3])
        pieces[n_pieces, :] = [t, r, b, l]
        if len(cols) >= 7:
            x = int(cols[4]); y = int(cols[5]); rot = int(cols[6])
            if not (x == 0 and y == 0 and rot == 0):
                if 0 <= x < size and 0 <= y < size and 0 <= rot <= 3:
                    pos = y * size + x
                    hints.append((pos, n_pieces, rot))
        n_pieces += 1
    assert n_pieces == 256, f"expected 256 pieces, got {n_pieces}"

    # Classify
    border_counts = (pieces == BORDER).sum(axis=1)
    n_corners = int((border_counts == 2).sum())
    n_edges = int((border_counts == 1).sum())
    n_interior = int((border_counts == 0).sum())
    assert n_corners == 4 and n_edges == 56 and n_interior == 196, \
        f"class counts wrong: {n_corners}/{n_edges}/{n_interior}"

    interior_colors = set()
    for p in pieces:
        for c in p:
            if c != BORDER:
                interior_colors.add(int(c))
    color_count = len(interior_colors)
    assert len(hints) == 5, f"expected 5 hints, got {len(hints)}"

    return {
        "size": size,
        "pieces": pieces,
        "hints": hints,
        "color_count": color_count,
        "interior_colors": sorted(interior_colors),
    }


def rotate_edges(edges: np.ndarray, rot: int) -> np.ndarray:
    """Rotate piece edges. rot=0 is identity; positive = CW.

    edges = [top, right, bottom, left].
    rot=1 (CW 90°): new_top = old_left, new_right = old_top, new_bot = old_right, new_left = old_bot.
    """
    if rot == 0:
        return edges
    return np.roll(edges, rot)


def main():
    p = load()
    print(f"size={p['size']} color_count={p['color_count']} "
          f"interior_colors={p['interior_colors']}")
    print(f"hints (pos, piece_id, rotation): {p['hints']}")
    # Show the 5 hint pieces' raw edges
    print()
    print("hint piece edges (top, right, bottom, left):")
    for pos, pid, rot in p["hints"]:
        e = p["pieces"][pid]
        x, y = pos % 16, pos // 16
        print(f"  pid={pid} at (x={x},y={y}) rot={rot} edges_raw={tuple(int(c) for c in e)} "
              f"edges_rotated={tuple(int(c) for c in rotate_edges(e, rot))}")


if __name__ == "__main__":
    main()
