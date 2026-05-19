#!/usr/bin/env python3
"""V154 — verify E2 encoding via xcover library.

Uses the proven xcover library (Knuth Algorithm C). If xcover finds
a solution, the encoding is correct and Rust DLX has a bug.
"""
from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path

from xcover import covers

REPO = Path(__file__).resolve().parents[2]


def load_csv(p):
    BORDER_RAW = 65535
    pieces = []
    with open(p) as f:
        size = int(f.readline().strip())
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split(",")
            sides = [int(s.strip(), 2) for s in parts[:4]]
            sides = [0 if v == BORDER_RAW else v for v in sides]
            pieces.append(tuple(sides))
    return size, pieces


def rotate(piece, r):
    base = list(piece)
    return tuple(base[(i + 4 - r) % 4] for i in range(4))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", required=True)
    args = ap.parse_args()
    size, pieces = load_csv(args.puzzle)
    print(f"[xcover] puzzle: {size}×{size}, {len(pieces)} pieces")

    # Build options for xcover.
    # Items: "cell_N" for each cell N, "piece_P" for each P (primary),
    #        "adj_H_R_C" / "adj_V_R_C" with colors (secondary).
    N = size
    n_h_adj = N * (N - 1)
    n_v_adj = (N - 1) * N

    primary = []
    for cell in range(N * N):
        primary.append(f"cell_{cell}")
    for pid in range(len(pieces)):
        primary.append(f"piece_{pid}")

    secondary = []
    for r in range(N):
        for c in range(N - 1):
            secondary.append(f"hadj_{r}_{c}")
    for r in range(N - 1):
        for c in range(N):
            secondary.append(f"vadj_{r}_{c}")

    options = []
    option_meta = []  # (cell, pid, rot)
    for cell in range(N * N):
        r = cell // N
        c = cell % N
        for pid in range(len(pieces)):
            for rot in range(4):
                sides = rotate(pieces[pid], rot)
                top, right, bottom, left = sides
                if r == 0 and top != 0: continue
                if r != 0 and top == 0: continue
                if r == N - 1 and bottom != 0: continue
                if r != N - 1 and bottom == 0: continue
                if c == 0 and left != 0: continue
                if c != 0 and left == 0: continue
                if c == N - 1 and right != 0: continue
                if c != N - 1 and right == 0: continue

                opt = [f"cell_{cell}", f"piece_{pid}"]
                if r > 0:
                    opt.append(f"vadj_{r-1}_{c}:{top}")
                if r < N - 1:
                    opt.append(f"vadj_{r}_{c}:{bottom}")
                if c > 0:
                    opt.append(f"hadj_{r}_{c-1}:{left}")
                if c < N - 1:
                    opt.append(f"hadj_{r}_{c}:{right}")
                options.append(opt)
                option_meta.append((cell, pid, rot))

    print(f"[xcover] options: {len(options)} | primary: {len(primary)} | secondary: {len(secondary)}")

    t0 = time.time()
    gen = covers(options, primary=primary, secondary=secondary, colored=True)
    sols = []
    for sol in gen:
        sols.append(sol)
        if len(sols) >= 5: break
    elapsed = time.time() - t0
    print(f"[xcover] solutions: {len(sols)} in {elapsed:.2f}s")
    if sols:
        print(f"[xcover] first solution = {len(sols[0])} options selected")
        for opt_idx in sorted(sols[0]):
            print(f"  {option_meta[opt_idx]}")


if __name__ == "__main__":
    main()
