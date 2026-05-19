#!/usr/bin/env python3
"""V133-T1 — Density saturation test.

Generate puzzles spanning extreme densities and measure ALNS gap.

Configurations:
  - HIGH density (small puzzle, few colors): 4×4/2, 5×5/3, 6×6/3
    expect p_match > 0.20, ALNS should hit 100% easily, gap small
  - MEDIUM density: 8×8/4, 10×10/5, 12×12/6
    p_match should sit between high/low
  - LOW density: 8×8/16, 10×10/20, 12×12/24
    p_match should be very low (lots of colors), ALNS may struggle

For each, generate 3 seeds + measure density + run 60s ALNS.
"""

from __future__ import annotations
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from collections import Counter

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "output/vol-133" / f"saturation_{time.strftime('%Y%m%dT%H%M%S')}"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CONFIGS = [
    # (size, n_colors, label)
    (4, 2, "high_4x4_c2"),
    (5, 3, "high_5x5_c3"),
    (6, 3, "high_6x6_c3"),
    (8, 4, "med_8x8_c4"),
    (10, 5, "med_10x10_c5"),
    (12, 6, "med_12x12_c6"),
    (8, 16, "low_8x8_c16"),
    (10, 20, "low_10x10_c20"),
    (12, 24, "low_12x12_c24"),
]
SEEDS = [42, 1, 7]
BUDGET_S = 60


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


def measure_density(size, pieces):
    P, R = len(pieces), 4
    n_int = (size - 1) * size + size * (size - 1)
    cf = Counter()
    for p in pieces:
        for r in range(R):
            n, e, s, w = p
            rot = [(n,e,s,w),(e,s,w,n),(s,w,n,e),(w,n,e,s)][r]
            for c in rot:
                cf[c] += 1
    total = P * R * 4
    p_match = sum((v/total)**2 for c, v in cf.items() if c != 0)
    return p_match, n_int


def gen_puzzle(size, n_colors, seed, out_csv):
    subprocess.run(
        [str(REPO/"target/bench-fast/gen_small_csv"),
         str(size), str(n_colors), str(seed), str(out_csv)],
        check=True, capture_output=True,
    )


def run_alns(puzzle, seed, budget_s):
    log = OUT_DIR / (Path(puzzle).stem + f"_seed{seed}.log")
    proc = subprocess.run(
        [str(REPO/"target/bench-fast/alns_e2"),
         "--puzzle", str(puzzle), "--seconds", str(budget_s),
         "--seed", str(seed), "--skip-warmup"],
        capture_output=True, text=True, cwd=str(REPO),
    )
    output = proc.stdout + proc.stderr
    with open(log, "w") as f: f.write(output)
    scores = re.findall(r"matched=(\d+)|score=(\d+)|matches: (\d+)", output)
    best = 0
    for tup in scores:
        for s in tup:
            if s:
                best = max(best, int(s))
    best_marks = re.findall(r"best.*?(\d+)", output)
    for s in best_marks:
        try:
            v = int(s)
            if 0 < v < 1000: best = max(best, v)
        except: pass
    return best


def main():
    print(f"OUT_DIR={OUT_DIR}", flush=True)
    rows = []
    for size, n_colors, label in CONFIGS:
        bests = []
        for seed in SEEDS:
            puzzle = OUT_DIR / f"{label}_seed{seed}.csv"
            try:
                gen_puzzle(size, n_colors, seed, puzzle)
            except subprocess.CalledProcessError as e:
                print(f"  GEN FAILED {label} seed={seed}: {e}", flush=True)
                continue
            size_check, pieces = load_csv(puzzle)
            pm, n_int = measure_density(size_check, pieces)
            best = run_alns(puzzle, seed, BUDGET_S)
            pct = best / n_int * 100
            exp_random = pm * 100
            gap = pct - exp_random
            print(f"  {label} seed={seed}: pm={pm:.4f} exp_random={exp_random:.1f}% "
                  f"best={best}/{n_int} ({pct:.1f}%) gap={gap:+.1f}", flush=True)
            bests.append({
                "size": size, "n_colors": n_colors, "seed": seed,
                "label": label, "p_match": pm,
                "exp_random_pct": exp_random,
                "best": best, "n_interior_edges": n_int,
                "pct": pct, "gap": gap,
            })
        rows.extend(bests)
        if bests:
            med_pct = sorted([b["pct"] for b in bests])[len(bests)//2]
            med_gap = sorted([b["gap"] for b in bests])[len(bests)//2]
            print(f"  {label}: median pct={med_pct:.1f}% median gap={med_gap:+.1f}", flush=True)
    with open(OUT_DIR / "results.json", "w") as f:
        json.dump(rows, f, indent=2)


if __name__ == "__main__":
    main()
