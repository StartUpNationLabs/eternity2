#!/usr/bin/env python3
"""Decode a bucas-URL JSON into a placement JSON compatible with rescore_board.

Input: JSON with `url` field containing bucas URL with `board_edges=` (color
quad per cell) AND `board_pieces=` (3-digit piece IDs per cell).
Output: JSON {placement: [{pos, piece_id, rotation}, ...], matched, bucas_url}.

We compute (piece_id, rotation) per cell by:
1. Decode board_pieces (256 × 3-digit = 768 chars) → piece_id at each cell.
2. Decode board_edges (256 × 4-char quads) → edge colors at each cell.
3. For each cell, find rotation k ∈ {0..3} such that the canonical piece's
   edges rotated by k match the cell's edges.

Bucas uses 1-indexed piece IDs (1..256). Our internal puzzle uses 0-indexed.
"""

import argparse
import csv
import json
import sys
import urllib.parse
from pathlib import Path

PUZZLE_CSV = "../data/puzzles/size_16_official_eternity.csv"


def load_canonical_pieces():
    """Return list of (id, (N, E, S, W color)) tuples (0-indexed)."""
    BORDER_RAW = 65535
    pieces = []
    with open(PUZZLE_CSV) as f:
        size = int(f.readline().strip())
        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            def col(s):
                v = int(s.strip(), 2)
                return 0 if v == BORDER_RAW else v
            top = col(parts[0])
            right = col(parts[1])
            bottom = col(parts[2])
            left = col(parts[3])
            pieces.append((top, right, bottom, left))
    return pieces


def bucas_char_to_color(c):
    """Bucas encodes colors as letters a-w. 'a' = 0 (border), 'b'=1, ..."""
    return ord(c) - ord('a')


def rotate(edges, k):
    """Cyclic rotation of (N, E, S, W) by k*90° clockwise.

    After rotating piece by 90° CW, the new N (top) shows what was previously
    West. So new = (W, N, E, S) when k=1.
    """
    n, e, s, w = edges
    if k == 0: return (n, e, s, w)
    if k == 1: return (w, n, e, s)
    if k == 2: return (s, w, n, e)
    if k == 3: return (e, s, w, n)
    raise ValueError(k)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_json")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    with open(args.input_json) as f:
        d = json.load(f)
    url = d.get("url", "")
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).fragment)
    if "board_pieces" not in qs or "board_edges" not in qs:
        sys.exit("missing board_pieces or board_edges in URL")
    piece_str = qs["board_pieces"][0]
    edges_str = qs["board_edges"][0]
    assert len(piece_str) == 256 * 3, f"piece_str length {len(piece_str)} != 768"
    assert len(edges_str) == 256 * 4, f"edges_str length {len(edges_str)} != 1024"

    pieces = load_canonical_pieces()  # 0-indexed

    placement = [None] * 256
    matched = 0
    unmatched = 0
    failures = []
    for cell in range(256):
        # board_pieces uses 1-indexed
        piece_id_bucas = int(piece_str[cell * 3:(cell + 1) * 3])
        piece_id = piece_id_bucas - 1  # 0-indexed for our system
        if piece_id < 0 or piece_id >= 256:
            sys.exit(f"piece_id {piece_id_bucas} at cell {cell} out of range")
        # Cell edges from board_edges
        quad = edges_str[cell * 4:(cell + 1) * 4]
        cell_edges = tuple(bucas_char_to_color(c) for c in quad)  # (N, E, S, W)

        # Find rotation: pieces[piece_id] rotated by k should equal cell_edges
        canon_edges = pieces[piece_id]
        found_k = None
        for k in range(4):
            if rotate(canon_edges, k) == cell_edges:
                found_k = k
                break
        if found_k is None:
            failures.append((cell, piece_id_bucas, canon_edges, cell_edges))
            continue
        placement[cell] = {"pos": cell, "piece_id": piece_id, "rotation": found_k}

    if failures:
        print(f"WARNING: {len(failures)} cells failed rotation lookup")
        for cell, pb, canon, cell_e in failures[:5]:
            print(f"  cell {cell} piece_bucas={pb} canonical={canon} cell={cell_e}")

    # Count matched edges from cell_edges grid
    grid = [[None] * 16 for _ in range(16)]
    for cell in range(256):
        r, c = divmod(cell, 16)
        quad = edges_str[cell * 4:(cell + 1) * 4]
        grid[r][c] = tuple(bucas_char_to_color(ch) for ch in quad)
    for r in range(16):
        for c in range(15):
            if grid[r][c][1] == grid[r][c + 1][3]:
                matched += 1
    for r in range(15):
        for c in range(16):
            if grid[r][c][2] == grid[r + 1][c][0]:
                matched += 1
    print(f"Matched edges: {matched}/480")

    out = {
        "matched": matched,
        "bucas_url": url,
        "source": args.input_json,
        "placement": placement,
        "decode_failures": len(failures),
    }
    Path(Path(args.output).parent).mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
