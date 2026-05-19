#!/usr/bin/env python3
"""V138-T1 — INTAGLIO 2-cell forbidden patterns."""
from __future__ import annotations
import argparse, json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np

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

def rotate(p, r):
    n, e, s, w = p
    return [(n,e,s,w),(e,s,w,n),(s,w,n,e),(w,n,e,s)][r]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", required=True)
    args = ap.parse_args()
    size, pieces = load_csv(args.puzzle)
    P = len(pieces)
    print(f"Puzzle: {size}×{size}, {P} pieces", flush=True)

    pr_color = np.zeros((P, 4, 4), dtype=np.int16)
    for p in range(P):
        for r in range(4):
            pr_color[p, r] = rotate(pieces[p], r)

    horiz_feasible = np.zeros((P, P), dtype=bool)
    vert_feasible = np.zeros((P, P), dtype=bool)

    for i in range(P):
        for j in range(P):
            if i == j: continue
            for r_i in range(4):
                ec = pr_color[i, r_i, 1]
                if ec == 0: continue
                for r_j in range(4):
                    if pr_color[j, r_j, 3] == ec:
                        horiz_feasible[i, j] = True
                        break
                if horiz_feasible[i, j]: break
            for r_i in range(4):
                sc = pr_color[i, r_i, 2]
                if sc == 0: continue
                for r_j in range(4):
                    if pr_color[j, r_j, 0] == sc:
                        vert_feasible[i, j] = True
                        break
                if vert_feasible[i, j]: break

    n_pairs = P * (P - 1)
    n_h_f = int(horiz_feasible.sum())
    n_v_f = int(vert_feasible.sum())
    print(f"\nHorizontal: feasible={n_h_f}/{n_pairs} ({n_h_f/n_pairs*100:.2f}%)  forbidden={n_pairs-n_h_f}", flush=True)
    print(f"Vertical:   feasible={n_v_f}/{n_pairs} ({n_v_f/n_pairs*100:.2f}%)  forbidden={n_pairs-n_v_f}", flush=True)

    h_out = horiz_feasible.sum(axis=1)
    h_in = horiz_feasible.sum(axis=0)
    v_out = vert_feasible.sum(axis=1)
    v_in = vert_feasible.sum(axis=0)
    print(f"\nHoriz out-deg: min={h_out.min()} max={h_out.max()} mean={h_out.mean():.1f}", flush=True)
    print(f"Vert out-deg:  min={v_out.min()} max={v_out.max()} mean={v_out.mean():.1f}", flush=True)

if __name__ == "__main__":
    main()
