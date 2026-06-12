#!/usr/bin/env python3
"""Vol-217 setup: attribute realized breaks of full boards to edge
regions, in particular the CROSSING-counted edge set (the exact 87
edges the crossing oracle will score):

  - V edges between full rows 10-11 (= N of interior row 10), cols 1-14
  - H edges within full rows 11, 12, 13 (cols 0-14: 13 interior + 2 rim)
  - V edges between full rows 11-12 and 12-13, cols 1-14

and the BAND-counted edge set (vol-216 band oracle, 58 edges):
  - H edges within full rows 13, 14
  - V edges between full rows 13-14 and 14-15 (S rim), cols 1-14

(The two sets overlap on the 15 H edges of full row 13 = interior
row 12.)  Everything else is "early" (rows 0-10 H, V above 9-10, rim).

Usage: attribution.py BOARD.json...
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "v216_lp"))
import lp_prefix_score as L


def board_edges(path, pieces):
    pl = json.load(open(path))["placement"]
    grid = {}
    for ent in pl:
        pos = ent["pos"]
        grid[(pos // 16, pos % 16)] = L.oriented(pieces[ent["piece_id"]],
                                                 ent["rotation"])
    return grid


def classify(grid):
    crossing, band, early, all_breaks = [], [], [], []
    for r in range(16):
        for c in range(16):
            if (r, c) not in grid:
                continue
            e = grid[(r, c)]
            # H edge to (r, c+1)
            if c + 1 < 16 and (r, c + 1) in grid:
                if e[1] != grid[(r, c + 1)][3]:
                    tag = ("H", r, c)
                    all_breaks.append(tag)
                    inx = r in (11, 12, 13)
                    inb = r in (13, 14)
                    if inx:
                        crossing.append(tag)
                    if inb:
                        band.append(tag)
                    if not inx and not inb:
                        early.append(tag)
            # V edge to (r+1, c)
            if r + 1 < 16 and (r + 1, c) in grid:
                if e[2] != grid[(r + 1, c)][0]:
                    tag = ("V", r, c)
                    all_breaks.append(tag)
                    inx = r in (10, 11, 12) and 1 <= c <= 14
                    inb = r in (13, 14) and 1 <= c <= 14
                    if inx:
                        crossing.append(tag)
                    if inb:
                        band.append(tag)
                    if not inx and not inb:
                        early.append(tag)
    return crossing, band, early, all_breaks


def main():
    pieces, _hints = L.load_puzzle(
        os.path.join(os.path.dirname(__file__), "..", "..", "..",
                     "data/puzzles/size_16_official_eternity.csv"))
    print("board\ttotal\tcrossing(87e)\tband(58e)\toverlap_r13H\tearly\tcrossing_edges")
    for path in sys.argv[1:]:
        grid = board_edges(path, pieces)
        x, b, ea, allb = classify(grid)
        ov = [t for t in x if t in b]
        tag = os.path.basename(path)[:-5]
        xs = ",".join(f"{t}{r}:{c}" for t, r, c in x)
        print(f"{tag}\t{len(allb)}\t{len(x)}\t{len(b)}\t{len(ov)}"
              f"\t{len(ea)}\t{xs}")


if __name__ == "__main__":
    main()
