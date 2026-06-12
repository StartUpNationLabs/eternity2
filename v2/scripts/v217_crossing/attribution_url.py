#!/usr/bin/env python3
"""Break attribution by region, straight from a Bucas board_edges
encoding (corpus JSONs). Same regions as attribution.py.

Usage: attribution_url.py CORPUS.json...
"""
import json
import re
import sys


def classify(grid):
    crossing, band, early, allb = [], [], [], []
    for r in range(16):
        for c in range(16):
            e = grid.get((r, c))
            if e is None:
                continue
            if c + 1 < 16 and (r, c + 1) in grid:
                if e[1] != grid[(r, c + 1)][3]:
                    t = ("H", r, c)
                    allb.append(t)
                    ix, ib = r in (11, 12, 13), r in (13, 14)
                    (crossing.append(t) if ix else None)
                    (band.append(t) if ib else None)
                    (early.append(t) if not ix and not ib else None)
            if r + 1 < 16 and (r + 1, c) in grid:
                if e[2] != grid[(r + 1, c)][0]:
                    t = ("V", r, c)
                    allb.append(t)
                    ix = r in (10, 11, 12) and 1 <= c <= 14
                    ib = r in (13, 14) and 1 <= c <= 14
                    (crossing.append(t) if ix else None)
                    (band.append(t) if ib else None)
                    (early.append(t) if not ix and not ib else None)
    return crossing, band, early, allb


def main():
    print("board\ttotal\tcrossing(87e)\tband(58e)\tearly\tbreak_cells")
    for path in sys.argv[1:]:
        d = json.load(open(path))
        m = re.search(r"board_edges=([a-w]+)", d["url"])
        enc = m.group(1)
        grid = {}
        for p in range(256):
            q = enc[p * 4:p * 4 + 4]
            if q and q != "aaaa":
                grid[(p // 16, p % 16)] = [ord(ch) - 97 for ch in q]
        x, b, ea, allb = classify(grid)
        tag = path.rsplit("/", 1)[-1][:-5]
        cells = ",".join(f"{t}{r}:{c}" for t, r, c in allb)
        print(f"{tag}\t{len(allb)}\t{len(x)}\t{len(b)}\t{len(ea)}\t{cells}")


if __name__ == "__main__":
    main()
