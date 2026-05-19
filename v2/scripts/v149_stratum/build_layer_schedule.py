#!/usr/bin/env python3
"""V149-T2 — Build the STRATUM v2 layer schedule.

Per piece, assign a layer index:
  0 = corner (2 border sides)
  1 = border-edge (1 border side)
  2a = interior with ≥ 1 rare color (1-5)
  2b = interior with ≥ 1 medium color (6-10) and no rare
  2c = interior with only common colors (11-22)

Output: scripts/v149_stratum/layer_schedule.json
  {
    "pieces_by_layer": {"0": [...], "1": [...], "2a": [...], ...},
    "scan_order_positions": [pos_0, pos_1, ..., pos_255]
       in order of placement.
  }

Scan order convention for canonical 16×16:
  - Layer 0 placements: 4 corner positions (0, 15, 240, 255).
  - Layer 1 placements: 56 border positions (around the ring, clockwise
    starting from pos 1).
  - Layer 2: interior 14×14 positions, BUT in a sequence designed so
    rare-color pieces find spots adjacent to placed cells (board-
    interior expansion in concentric rings).

For now we use a simpler scan: corners → border CW → interior
spiral-in. The PIECE order is what enforces stratum; the POS order
is row-major within each layer.
"""

from __future__ import annotations
import argparse
import json
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load_canonical_pieces(path):
    with open(path) as f:
        lines = [l.strip() for l in f if l.strip()]
    size = int(lines[0])
    pieces = []
    for line in lines[1:]:
        parts = line.split(",")

        def cw(s):
            v = int(s.strip(), 2)
            return 0 if v == 65535 else v

        t, r, b, l = cw(parts[0]), cw(parts[1]), cw(parts[2]), cw(parts[3])
        pieces.append((t, r, b, l))
    assert len(pieces) == size * size
    return size, pieces


def piece_class(piece):
    """Classify per layer schedule."""
    border_count = sum(1 for c in piece if c == 0)
    if border_count == 2:
        return "0"  # corner
    elif border_count == 1:
        return "1"  # border-edge
    elif border_count == 0:
        colors = set(c for c in piece if c != 0)
        if any(1 <= c <= 5 for c in colors):
            return "2a"
        elif any(6 <= c <= 10 for c in colors):
            return "2b"
        else:
            return "2c"
    else:
        return "0"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", type=str,
                    default=str(REPO.parent / "data/puzzles/size_16_official_eternity.csv"))
    args = ap.parse_args()

    size, pieces = load_canonical_pieces(args.puzzle)
    pieces_by_layer = defaultdict(list)
    for pid, p in enumerate(pieces):
        pieces_by_layer[piece_class(p)].append(pid)

    print(f"[v149-t2] Layer distribution:")
    for layer in ["0", "1", "2a", "2b", "2c"]:
        print(f"  layer {layer}: {len(pieces_by_layer[layer])} pieces")
    print()

    # Verify counts match expectation.
    expected = {"0": 4, "1": 56, "interior": 196}
    int_total = sum(len(pieces_by_layer[l]) for l in ["2a", "2b", "2c"])
    print(f"[v149-t2] corners {len(pieces_by_layer['0'])} (expect 4)")
    print(f"[v149-t2] border-edges {len(pieces_by_layer['1'])} (expect 56)")
    print(f"[v149-t2] interior {int_total} (expect 196)")

    # Scan order: corners → border CW → interior spiral inward (concentric rings).
    N = size

    def position_layer(pos):
        x, y = pos % N, pos // N
        if (x in (0, N-1)) and (y in (0, N-1)):
            return "0"
        if x == 0 or x == N-1 or y == 0 or y == N-1:
            return "1"
        return "interior"

    corners = [0, N-1, N*(N-1), N*N-1]  # TL, TR, BL, BR
    # Border ring positions, CW starting from (0,1).
    border = []
    # Top row (y=0): x = 1..N-2
    for x in range(1, N-1):
        border.append(x)
    # Right col (x=N-1): y = 1..N-2
    for y in range(1, N-1):
        border.append(y * N + (N-1))
    # Bottom row (y=N-1): x = N-2..1
    for x in range(N-2, 0, -1):
        border.append((N-1) * N + x)
    # Left col (x=0): y = N-2..1
    for y in range(N-2, 0, -1):
        border.append(y * N)
    assert len(border) == 56, f"got {len(border)} border positions"

    # Interior: spiral inward starting from (1,1), going CW.
    interior = []
    def add_ring(top, left, size_):
        if size_ <= 0:
            return
        if size_ == 1:
            interior.append((top + 0) * N + (left + 0))
            return
        # top row
        for x in range(left, left + size_):
            interior.append(top * N + x)
        # right col
        for y in range(top + 1, top + size_):
            interior.append(y * N + (left + size_ - 1))
        # bottom row reversed
        for x in range(left + size_ - 2, left - 1, -1):
            interior.append((top + size_ - 1) * N + x)
        # left col reversed
        for y in range(top + size_ - 2, top, -1):
            interior.append(y * N + left)

    # interior is 14x14, position (1,1) to (14,14)
    for d in range(7):
        add_ring(1 + d, 1 + d, 14 - 2 * d)
    assert len(interior) == 196, f"got {len(interior)} interior positions"

    scan_order = corners + border + interior
    assert len(scan_order) == N * N

    out = {
        "size": size,
        "pieces_by_layer": dict(pieces_by_layer),
        "scan_order_positions": scan_order,
        "n_corners": 4,
        "n_border": 56,
        "n_interior": 196,
    }
    path = REPO / "scripts/v149_stratum/layer_schedule.json"
    json.dump(out, open(path, "w"), indent=2)
    print(f"[v149-t2] saved to {path}")
    print(f"[v149-t2] scan order: corners(4) + border-CW(56) + interior-spiral-in(196)")


if __name__ == "__main__":
    main()
