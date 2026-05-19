#!/usr/bin/env python3
"""V138-T2 — INTAGLIO 2x2 patch feasibility (random sample)."""
from __future__ import annotations
import argparse, json, random, sys, time
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

def check_2x2_feasible(pr_color, p_tl, p_tr, p_bl, p_br):
    for r_tl in range(4):
        tl = pr_color[p_tl, r_tl]
        if tl[1] == 0 or tl[2] == 0: continue
        for r_tr in range(4):
            tr = pr_color[p_tr, r_tr]
            if tl[1] != tr[3]: continue
            if tr[2] == 0: continue
            for r_bl in range(4):
                bl = pr_color[p_bl, r_bl]
                if tl[2] != bl[0]: continue
                if bl[1] == 0: continue
                for r_br in range(4):
                    br = pr_color[p_br, r_br]
                    if tr[2] != br[0]: continue
                    if bl[1] != br[3]: continue
                    return True
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", required=True)
    ap.add_argument("--n-samples", type=int, default=10000)
    args = ap.parse_args()
    size, pieces = load_csv(args.puzzle)
    P = len(pieces)
    print(f"Puzzle: {size}×{size}, {P} pieces, sampling N={args.n_samples}", flush=True)
    pr_color = np.zeros((P, 4, 4), dtype=np.int16)
    for p in range(P):
        for r in range(4):
            pr_color[p, r] = rotate(pieces[p], r)
    interior_pids = [p for p in range(P) if 0 not in pieces[p]]
    print(f"Interior pieces: {len(interior_pids)}", flush=True)
    rng = random.Random(42)
    n_feasible = 0
    t0 = time.time()
    for _ in range(args.n_samples):
        p4 = rng.sample(interior_pids, 4)
        if check_2x2_feasible(pr_color, *p4):
            n_feasible += 1
    elapsed = time.time() - t0
    print(f"\nResults after {args.n_samples} samples ({elapsed:.1f}s):", flush=True)
    print(f"  feasible: {n_feasible}/{args.n_samples} ({n_feasible/args.n_samples*100:.3f}%)", flush=True)
    print(f"  FORBIDDEN: {args.n_samples-n_feasible}/{args.n_samples} ({(args.n_samples-n_feasible)/args.n_samples*100:.3f}%)", flush=True)

if __name__ == "__main__":
    main()
