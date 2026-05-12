#!/usr/bin/env python3
"""Convert a vol-6 border JSONL entry into a pt_e2-compatible
start-from JSON: full 256-cell placement array with the 60 perimeter
cells from the border + 5 hints + 191 unfilled interior cells as
null. pt_e2 with --start-from will greedy-fill the empty interior;
--pin-perimeter will hold the border during PT.

Usage:
  python3 scripts/synth_border_seed.py \\
      output/borders/top_1000_by_corner_tightness.jsonl \\
      <line_index> <out.json>

Border format (vol-6): {"border": [[pid, rot], [pid, rot], ...]} 60 entries,
in clockwise order starting from top-left.
"""

import json
import sys
from pathlib import Path

W = 16

# Mapping: 60 border entries in clockwise order:
#   indices 0..15  = top row (x=0..15, y=0)
#   indices 16..28 = right col (x=15, y=1..13)
#   indices 29..44 = bottom row, RIGHT-TO-LEFT (x=15..0, y=15)
#   indices 45..58 = left col, BOTTOM-TO-TOP (x=0, y=14..1)
# That's 16 + 13 + 16 + 14 = 59, but it should be 60. Let me check:
# corners are at (0,0), (15,0), (15,15), (0,15). Top row has 16 cells.
# Right col has 16 cells but corners (15,0) and (15,15) are already in top/bot.
# So right col (excluding corners) is y=1..14, 14 cells.
# Bottom row has 16 cells, but (15,15) and (0,15) are corners (already counted
# if we did rightward then bottom, but here it's separate).
# Let me re-derive: top + right (excl top corner) + bottom (excl right corner)
# + left (excl bottom and top corners) = 16 + 14 + 15 + 14 = 59. Still off.
#
# Actually convention: 4 corners + 56 edges = 60 perimeter pieces.
# Cleanly: top row 16, right col 14 (no corners), bottom row 16, left col 14 = 60. Yes.
# But the CLOCKWISE listing convention is:
#   top row (16 cells, x = 0..15 at y = 0),
#   right column (14 cells, y = 1..14 at x = 15),
#   bottom row (16 cells, x = 15..0 at y = 15),  REVERSED
#   left column (14 cells, y = 14..1 at x = 0). REVERSED


def border_idx_to_xy(i, w=W):
    """Map clockwise border index [0..59] to (x, y) cell coordinate."""
    if i < 16:
        return (i, 0)
    if i < 30:
        return (w - 1, i - 15)  # i=16 → y=1, i=29 → y=14
    if i < 46:
        return (w - 1 - (i - 30), w - 1)  # i=30 → (15,15), i=45 → (0,15)
    return (0, w - 1 - (i - 46))  # i=46 → (0,14), i=59 → (0,1)


# Hint positions (x, y), piece_id, rotation
HINTS = [
    ((7, 8), 138, 0),
    ((2, 13), 180, 1),
    ((2, 2), 207, 1),
    ((13, 13), 248, 2),
    ((13, 2), 254, 1),
]


def main():
    if len(sys.argv) < 4:
        print("Usage: synth_border_seed.py <borders.jsonl> <line_idx> <out.json>", file=sys.stderr)
        sys.exit(1)
    borders_path = Path(sys.argv[1])
    idx = int(sys.argv[2])
    out_path = Path(sys.argv[3])

    with borders_path.open() as f:
        for i, ln in enumerate(f):
            if i == idx:
                entry = json.loads(ln)
                break
        else:
            print(f"line {idx} not in {borders_path}", file=sys.stderr)
            sys.exit(1)

    border = entry["border"]
    if len(border) != 60:
        print(f"unexpected border length: {len(border)}", file=sys.stderr)
        sys.exit(1)

    placement = [None] * (W * W)
    used = set()

    # Place border pieces
    for i, (pid, rot) in enumerate(border):
        x, y = border_idx_to_xy(i)
        cell_idx = y * W + x
        placement[cell_idx] = {"piece_id": pid, "rotation": rot}
        used.add(pid)

    # Place hints
    for (x, y), pid, rot in HINTS:
        cell_idx = y * W + x
        placement[cell_idx] = {"piece_id": pid, "rotation": rot}
        used.add(pid)

    # Fill remaining interior with placeholder pieces.
    # pt_e2 expects all 256 cells placed in the start-from board? Let me
    # check by inspection of read_board_from_json: it allows null cells.
    # So leave the 191 interior cells null.

    out = {
        "puzzle": {"width": W, "height": W, "color_count": 23,
                   "piece_count": 256, "name": "size_16_official_eternity"},
        "score": {"matched_edges": 0, "total_edges": 480, "placed_cells": len(used),
                  "total_cells": W * W, "percent": 0.0},
        "details": {"cp": {}, "pt": {}, "seed": entry.get("seed", 0)},
        "placement": placement,
        "run_name": f"synth_border_idx_{idx}",
        "timestamp_unix": 0,
    }
    with out_path.open("w") as f:
        json.dump(out, f)
    print(f"wrote {out_path} (border idx {idx}, {len(used)} pieces placed)", file=sys.stderr)


if __name__ == "__main__":
    main()
