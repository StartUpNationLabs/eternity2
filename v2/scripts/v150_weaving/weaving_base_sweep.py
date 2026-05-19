#!/usr/bin/env python3
"""V150 — sweep row-greedy and col-greedy with many seeds.

WEAVING's consensus step degraded scores (refuted at eps=5). The
remaining value is the BASE GREEDY which reaches 388/480 in 0.3s.

Question: does broad seed sweep reveal high outliers?
"""

from __future__ import annotations
import argparse
import random
import time
from pathlib import Path

import sys
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts/v150_weaving"))

from weaving_poc import (
    load_csv, build_greedy, score, row_major_scan, col_major_scan,
    total_interior_edges,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", required=True)
    ap.add_argument("--n-seeds", type=int, default=200)
    ap.add_argument("--budget-s", type=float, default=120.0)
    args = ap.parse_args()

    size, pieces = load_csv(args.puzzle)
    target = total_interior_edges(size)
    print(f"[v150-sweep] {size}×{size} target={target}", flush=True)

    row_scan = row_major_scan(size)
    col_scan = col_major_scan(size)

    all_scores = []
    n_done = 0
    t0 = time.time()
    seed = 0
    while n_done < args.n_seeds and time.time() - t0 < args.budget_s:
        # Try both axes for each seed.
        random.seed(seed)
        B_R, _ = build_greedy(pieces, size, seed, row_scan)
        B_C, _ = build_greedy(pieces, size, seed, col_scan)
        s_R = score(B_R, size)
        s_C = score(B_C, size)
        best = max(s_R, s_C)
        all_scores.append((seed, s_R, s_C))
        if best >= 400:
            print(f"  seed={seed}: HIGH score_R={s_R} score_C={s_C}", flush=True)
        n_done += 1
        seed += 1

    elapsed = time.time() - t0
    print()
    print(f"[v150-sweep] {n_done} seeds in {elapsed:.1f}s ({elapsed/n_done:.3f}s/seed)")
    all_r = sorted([s[1] for s in all_scores])
    all_c = sorted([s[2] for s in all_scores])
    all_best = sorted([max(s[1], s[2]) for s in all_scores])
    print(f"[v150-sweep] row-greedy:  min={all_r[0]} p10={all_r[len(all_r)//10]} med={all_r[len(all_r)//2]} p90={all_r[9*len(all_r)//10]} max={all_r[-1]}")
    print(f"[v150-sweep] col-greedy:  min={all_c[0]} p10={all_c[len(all_c)//10]} med={all_c[len(all_c)//2]} p90={all_c[9*len(all_c)//10]} max={all_c[-1]}")
    print(f"[v150-sweep] best(R,C):   min={all_best[0]} p10={all_best[len(all_best)//10]} med={all_best[len(all_best)//2]} p90={all_best[9*len(all_best)//10]} max={all_best[-1]}")
    # How many ≥ 400?
    n_400 = sum(1 for s in all_best if s >= 400)
    n_420 = sum(1 for s in all_best if s >= 420)
    n_440 = sum(1 for s in all_best if s >= 440)
    print(f"[v150-sweep] ≥400: {n_400}/{n_done} ({n_400/n_done*100:.1f}%)")
    print(f"[v150-sweep] ≥420: {n_420}/{n_done}")
    print(f"[v150-sweep] ≥440: {n_440}/{n_done}")


if __name__ == "__main__":
    main()
