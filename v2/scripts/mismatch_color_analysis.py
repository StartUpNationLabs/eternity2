#!/usr/bin/env python3
"""For each mismatched edge on a board, identify the color pair and
how many pieces in the puzzle could supply that pair if it were
matched (vs how many pieces actually present the current colors).

Diagnostic of "combinatorial freedom" on each defect: an edge
mismatch where the sides are colors (a, b) is "easy to fix" if
many pieces have edges of color a or color b in the right
configuration; "hard to fix" if very few do.
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


W = 16
H = 16
BORDER = 0


def parse_csv_piece_word(s):
    v = int(s.strip(), 2)
    if v == 65535:
        return 0
    return v


def load_pieces(path):
    pieces = []
    with open(path) as f:
        size = int(f.readline().strip())
        for pid, line in enumerate(f):
            cols = line.strip().split(',')
            if len(cols) < 4:
                continue
            quad = tuple(parse_csv_piece_word(cols[i]) for i in range(4))
            pieces.append(quad)
    return pieces


def main():
    if len(sys.argv) < 2:
        print("usage: mismatch_color_analysis.py BOARD_JSON", file=sys.stderr)
        sys.exit(1)

    pieces = load_pieces("../data/puzzles/size_16_official_eternity.csv")

    # Build color-pair availability table: (a, b) -> # pieces that have
    # color a on at least one side AND color b on another side. Order
    # matters? For matching, no — they need to be on FACING sides of
    # adjacent pieces. So both pieces need: piece1 has a on the facing
    # side, piece2 has a on the facing side too (matching colors a==b).
    # So really we count pieces with at least 1 edge of color c.
    color_present_in_piece = defaultdict(set)  # color -> set of pieces
    for pid, q in enumerate(pieces):
        for c in q:
            color_present_in_piece[c].add(pid)

    # Color frequency.
    color_count = Counter()
    for q in pieces:
        for c in q:
            color_count[c] += 1

    # Load the board.
    board_json = json.load(open(sys.argv[1]))
    url = board_json['bucas_url']
    blob = re.search(r'board_edges=([a-z]+)', url).group(1)
    quads = [
        tuple(ord(blob[pos*4+i])-ord('a') for i in range(4))
        for pos in range(W * H)
    ]

    # Find mismatches.
    mismatches = []
    for y in range(H):
        for x in range(W):
            pos = y*W+x
            if x+1<W:
                a, b = quads[pos][1], quads[pos+1][3]
                if a!=BORDER and b!=BORDER and a!=b:
                    mismatches.append(('h', pos, x, y, a, b))
            if y+1<H:
                a, b = quads[pos][2], quads[pos+W][0]
                if a!=BORDER and b!=BORDER and a!=b:
                    mismatches.append(('v', pos, x, y, a, b))

    print(f"=== mismatches on board (total {len(mismatches)}) ===")
    print(f"{'edge':>10}  {'cell':>9}  {'colors':>10}  {'count_a':>8}  {'count_b':>8}  {'pieces_a':>9}  {'pieces_b':>9}")
    for typ, pos, x, y, a, b in mismatches:
        # # pieces that have color a (could supply that side).
        pa = len(color_present_in_piece[a])
        pb = len(color_present_in_piece[b])
        # Note the SIDE of the offender: a is offered by current piece's right/bottom side;
        # b is offered by neighbor's left/top.
        rare_a = '*' if a <= 5 else ' '
        rare_b = '*' if b <= 5 else ' '
        print(f"  {typ:>1} {pos:>3d}  ({x:>2},{y:>2})  ({a:>2}{rare_a},{b:>2}{rare_b})  "
              f"{color_count[a]:>5}    {color_count[b]:>5}    "
              f"{pa:>5}     {pb:>5}")

    # Color-pair statistics.
    color_pair_counter = Counter()
    for typ, pos, x, y, a, b in mismatches:
        pair = tuple(sorted([a, b]))
        color_pair_counter[pair] += 1
    print(f"\n=== color-pair frequencies in mismatches ===")
    for pair, n in color_pair_counter.most_common(10):
        a, b = pair
        # # pieces with color a AND color b (any sides).
        both = len(color_present_in_piece[a] & color_present_in_piece[b])
        print(f"  pair {pair}: {n} mismatches  (#pieces with both colors = {both})")

    # Per-color mismatch-cell COUNT (each mismatch contributes to BOTH side colors).
    color_in_mismatch = Counter()
    for typ, pos, x, y, a, b in mismatches:
        color_in_mismatch[a] += 1
        color_in_mismatch[b] += 1
    print(f"\n=== color appearance in mismatches (each mismatch counts both sides) ===")
    for c in range(1, 23):
        n = color_in_mismatch[c]
        total_edges = color_count[c]
        rare = ' *' if c <= 5 else ''
        print(f"  color {c:>2}: {n:>3} mismatch-incidences / {total_edges} total edges  ({n/total_edges*100:.0f}%){rare}")


if __name__ == "__main__":
    main()
