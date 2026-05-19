#!/usr/bin/env python3
"""V142-T1 — INTAGLIO larger patches.

Test forbidden-rate at:
- 2x1 horizontal (= V138 baseline ~54% forbidden)
- 2x2 square (= V138 measurement: 99.72% forbidden)
- 3x1 horizontal strip
- L-shape (3 cells: TL + TR + BL)
- 2x3 rectangle

Sample N random piece-tuples. Compute forbidden fraction.

Hypothesis: larger patches have even higher forbidden rate.
"""
from __future__ import annotations
import argparse, random, sys, time
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[1]


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


def is_feasible_horizontal_2(pr, p1, p2):
    """p1-p2 with p1.E == p2.W under some rotation pair, no border colors."""
    for r1 in range(4):
        e1 = pr[p1, r1, 1]
        if e1 == 0: continue
        for r2 in range(4):
            if pr[p2, r2, 3] == e1: return True
    return False


def is_feasible_horizontal_3(pr, p1, p2, p3):
    """3-cell horizontal strip with chained matches."""
    for r1 in range(4):
        e1 = pr[p1, r1, 1]
        if e1 == 0: continue
        for r2 in range(4):
            if pr[p2, r2, 3] != e1: continue
            e2 = pr[p2, r2, 1]
            if e2 == 0: continue
            for r3 in range(4):
                if pr[p3, r3, 3] == e2: return True
    return False


def is_feasible_2x2(pr, p_tl, p_tr, p_bl, p_br):
    for r_tl in range(4):
        tl = pr[p_tl, r_tl]
        if tl[1] == 0 or tl[2] == 0: continue
        for r_tr in range(4):
            tr = pr[p_tr, r_tr]
            if tl[1] != tr[3]: continue
            if tr[2] == 0: continue
            for r_bl in range(4):
                bl = pr[p_bl, r_bl]
                if tl[2] != bl[0]: continue
                if bl[1] == 0: continue
                for r_br in range(4):
                    br = pr[p_br, r_br]
                    if tr[2] != br[0]: continue
                    if bl[1] != br[3]: continue
                    return True
    return False


def is_feasible_Lshape(pr, p_tl, p_tr, p_bl):
    """L: TL-TR horizontally + TL-BL vertically."""
    for r_tl in range(4):
        tl = pr[p_tl, r_tl]
        if tl[1] == 0 or tl[2] == 0: continue
        for r_tr in range(4):
            tr = pr[p_tr, r_tr]
            if tl[1] != tr[3]: continue
            for r_bl in range(4):
                bl = pr[p_bl, r_bl]
                if tl[2] == bl[0]: return True
    return False


def is_feasible_2x3(pr, p_tl, p_tm, p_tr, p_bl, p_bm, p_br):
    """2x3 rectangle: 2 rows of 3 cells each."""
    for r_tl in range(4):
        tl = pr[p_tl, r_tl]
        if tl[1] == 0 or tl[2] == 0: continue
        for r_tm in range(4):
            tm = pr[p_tm, r_tm]
            if tl[1] != tm[3]: continue
            if tm[1] == 0 or tm[2] == 0: continue
            for r_tr in range(4):
                tr = pr[p_tr, r_tr]
                if tm[1] != tr[3]: continue
                if tr[2] == 0: continue
                for r_bl in range(4):
                    bl = pr[p_bl, r_bl]
                    if tl[2] != bl[0]: continue
                    if bl[1] == 0: continue
                    for r_bm in range(4):
                        bm = pr[p_bm, r_bm]
                        if tm[2] != bm[0]: continue
                        if bl[1] != bm[3]: continue
                        if bm[1] == 0: continue
                        for r_br in range(4):
                            br = pr[p_br, r_br]
                            if tr[2] != br[0]: continue
                            if bm[1] != br[3]: continue
                            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", required=True)
    ap.add_argument("--n-samples", type=int, default=5000)
    args = ap.parse_args()
    size, pieces = load_csv(args.puzzle)
    P = len(pieces)
    pr = np.zeros((P, 4, 4), dtype=np.int16)
    for p in range(P):
        for r in range(4):
            pr[p, r] = rotate(pieces[p], r)
    interior_pids = [p for p in range(P) if 0 not in pieces[p]]
    print(f"Puzzle: {size}×{size}  pieces={P}  interior={len(interior_pids)}", flush=True)

    rng = random.Random(42)
    N = args.n_samples

    for name, n_cells, fn in [
        ("2-horiz", 2, lambda ps: is_feasible_horizontal_2(pr, *ps)),
        ("3-horiz", 3, lambda ps: is_feasible_horizontal_3(pr, *ps)),
        ("L-shape", 3, lambda ps: is_feasible_Lshape(pr, *ps)),
        ("2x2",     4, lambda ps: is_feasible_2x2(pr, *ps)),
        ("2x3",     6, lambda ps: is_feasible_2x3(pr, *ps)),
    ]:
        t0 = time.time()
        n_feas = 0
        for _ in range(N):
            ps = rng.sample(interior_pids, n_cells)
            if fn(ps): n_feas += 1
        elapsed = time.time() - t0
        print(f"  {name}: n_cells={n_cells} samples={N} feasible={n_feas}/{N} "
              f"({n_feas/N*100:.3f}%)  forbidden={100-n_feas/N*100:.3f}%  "
              f"t={elapsed:.1f}s", flush=True)


if __name__ == "__main__":
    main()
