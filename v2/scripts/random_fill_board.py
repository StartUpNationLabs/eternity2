#!/usr/bin/env python3
"""Generate a random class-respecting filling of an Eternity II board,
honoring official hints. Output as a pt_e2-compatible JSON for use
with `pt_e2 --start-from`.

Class-respecting = corners-to-corners, edges-to-non-corner-borders,
interiors-to-interior-cells. Rotations chosen to satisfy border-edge
constraints when possible (corner cells get the unique rotation that
puts the 2 BORDER edges on the right sides; edge cells similar).

Diagnostic purpose: pt_e2's CP phase always biases the basin. A
random fill is structurally different — testing it tells us whether
PT's plateau at 449 is set by the CP basin or is intrinsic to the
local-search landscape.

Usage:
    python3 scripts/random_fill_board.py --out random_fill.json [--seed N]
"""

import argparse
import json
import random
import sys
from pathlib import Path


W = 16
H = 16
BORDER = 0


def parse_csv_piece_word(s):
    v = int(s.strip(), 2)
    if v == 65535:
        return 0
    return v


def load_puzzle(path):
    pieces = []
    hints = {}
    with open(path) as f:
        size = int(f.readline().strip())
        assert size == W
        for pid, line in enumerate(f):
            cols = line.strip().split(',')
            if len(cols) < 4:
                continue
            quad = tuple(parse_csv_piece_word(cols[i]) for i in range(4))
            pieces.append(quad)
            if len(cols) >= 7:
                x = int(cols[4]); y = int(cols[5]); rot = int(cols[6])
                if (x, y, rot) != (0, 0, 0):
                    pos = y * W + x
                    hints[pos] = (pid, rot)
    return pieces, hints


def piece_class(quad):
    """0=corner (2 BORDER), 1=edge (1 BORDER), 2=interior (0)."""
    n = sum(1 for c in quad if c == BORDER)
    if n >= 2:
        return 0
    if n == 1:
        return 1
    return 2


def cell_class(pos):
    x, y = pos % W, pos // W
    n = (x == 0) + (x == W-1) + (y == 0) + (y == H-1)
    if n >= 2:
        return 0
    if n == 1:
        return 1
    return 2


def cell_border_mask(pos):
    """Returns (top_b, right_b, bottom_b, left_b) — True if that side
    must be BORDER (= cell is at board edge on that side)."""
    x, y = pos % W, pos // W
    return (y == 0, x == W - 1, y == H - 1, x == 0)


def rotate_quad(q, rot):
    t, r, b, l = q
    if rot == 0: return (t, r, b, l)
    if rot == 1: return (l, t, r, b)
    if rot == 2: return (b, l, t, r)
    if rot == 3: return (r, b, l, t)


def find_valid_rotation(quad, mask):
    """Find a rotation r such that (quad rotated by r)[s] == BORDER iff mask[s].
    Returns the rotation index, or None if no valid rotation."""
    for r in range(4):
        rq = rotate_quad(quad, r)
        ok = all((rq[s] == BORDER) == mask[s] for s in range(4))
        if ok:
            return r
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", default="../data/puzzles/size_16_official_eternity.csv")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    pieces, hints = load_puzzle(args.puzzle)
    rng = random.Random(args.seed)

    # Bin pieces by class.
    pieces_by_class = [[], [], []]
    for pid, quad in enumerate(pieces):
        pieces_by_class[piece_class(quad)].append(pid)

    # Bin cells by class.
    cells_by_class = [[], [], []]
    for pos in range(W * H):
        cells_by_class[cell_class(pos)].append(pos)

    # Honor hints: pin those pieces.
    placement = [None] * (W * H)
    used_pids = set()
    for pos, (pid, rot) in hints.items():
        placement[pos] = {"piece_id": pid, "rotation": rot}
        used_pids.add(pid)

    # For each class, shuffle pieces and assign to remaining cells.
    for cls in range(3):
        free_pieces = [p for p in pieces_by_class[cls] if p not in used_pids]
        free_cells = [c for c in cells_by_class[cls] if placement[c] is None]
        rng.shuffle(free_pieces)
        rng.shuffle(free_cells)
        if len(free_pieces) != len(free_cells):
            print(f"WARNING class {cls}: {len(free_pieces)} pieces vs {len(free_cells)} cells",
                  file=sys.stderr)
        for cell, pid in zip(free_cells, free_pieces):
            mask = cell_border_mask(cell)
            quad = pieces[pid]
            r = find_valid_rotation(quad, mask)
            if r is None:
                print(f"WARN: pid={pid} can't rotate to fit cell {cell}",
                      file=sys.stderr)
                r = 0
            placement[cell] = {"piece_id": pid, "rotation": r}

    n_placed = sum(1 for p in placement if p is not None)
    print(f"# placed {n_placed}/{W*H} cells", file=sys.stderr)

    # Wrap in pt_e2-compatible JSON. The bare minimum is `placement`.
    out = {
        "run_name": "random_fill",
        "puzzle": {"name": "size_16_official_eternity", "width": W, "height": H},
        "placement": placement,
    }
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print(f"# wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
