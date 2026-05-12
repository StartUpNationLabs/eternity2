#!/usr/bin/env python3
"""Analyze structural similarity across multiple saved E2 boards.

Useful diagnostics:
- backbone cells (all boards agree on piece+rotation)
- piece-set per row-region (does CP determine region assignment?)
- per-cell uniqueness (how flexible is each position?)

Usage: python3 scripts/board_diff_analysis.py BOARD1.json BOARD2.json [...]
"""
import json
import sys
from pathlib import Path

W = H = 16

def load_board(path):
    data = json.load(open(path))
    if 'placement' not in data:
        return None
    cell = [None]*(W*H)
    for x in data['placement']:
        if x is not None:
            cell[x['pos']] = (x['piece_id'], x['rotation'])
    return cell

def region_pieces(board, y_lo, y_hi):
    return {board[y*W + x][0]
            for y in range(y_lo, y_hi+1) for x in range(W)
            if board[y*W + x] is not None}

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    boards = []
    for p in sys.argv[1:]:
        b = load_board(p)
        if b is not None:
            boards.append((p, b))
    print(f"Loaded {len(boards)} boards")
    for p, _ in boards:
        print(f"  {p}")
    if len(boards) < 2:
        return

    # Backbone analysis.
    backbone = 0
    for i in range(W*H):
        placements = set(b[1][i] for b in boards if b[1][i] is not None)
        if len(placements) == 1:
            backbone += 1
    print(f"\nbackbone cells (all boards agree): {backbone}/256")

    # Per-region piece-set comparison.
    regions = [(0, 4, "rows 0-4"), (5, 8, "rows 5-8"),
               (9, 12, "rows 9-12"), (13, 15, "rows 13-15")]
    print("\nPiece-set intersection across boards:")
    for y_lo, y_hi, name in regions:
        sets = [region_pieces(b[1], y_lo, y_hi) for b in boards]
        intersection = set.intersection(*sets) if sets else set()
        print(f"  {name}: |intersection| = {len(intersection)}/{len(sets[0])}")
        for i, s in enumerate(sets):
            if s != sets[0]:
                print(f"    board {i} ({Path(boards[i][0]).name}) differs: {len(s)} pieces, overlap with board 0 = {len(s & sets[0])}")

if __name__ == '__main__':
    main()
