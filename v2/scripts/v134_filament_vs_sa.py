#!/usr/bin/env python3
"""V134-T1 — FILAMENT-repair vs SA-repair head-to-head on V131 suite.

For each puzzle in V131 scaling suite, run alns_e2 with:
  --repair sa
  --repair filament
60s budget, 3 seeds each. Compare distributions.

Hypothesis (from vol-130 single-test on 254 board):
  SA wins on equal time budget because FILAMENT is more
  expensive per repair call.

This is a PROPER controlled comparison: same operator portfolio,
same puzzle, same budget, only repair changes.
"""

from __future__ import annotations
import json
import re
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "output/vol-134" / f"filament_vs_sa_{time.strftime('%Y%m%dT%H%M%S')}"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Use V131 suite puzzles
V131 = REPO / "output/vol-131/scaling_bench_20260519T123004"
PUZZLES = []
for size, n_colors in [(6,4),(7,5),(8,6),(10,8),(12,10),(14,12)]:
    p = V131 / f"puzzle_s{size}_c{n_colors}_seed42.csv"
    if p.exists():
        PUZZLES.append((f"{size}x{size}_c{n_colors}", p))

SEEDS = [42, 1, 7]
BUDGET_S = 60
REPAIRS = ["sa", "filament"]


def run(puzzle, repair, seed):
    log = OUT_DIR / f"{Path(puzzle).stem}_{repair}_seed{seed}.log"
    proc = subprocess.run(
        [str(REPO/"target/bench-fast/alns_e2"),
         "--puzzle", str(puzzle), "--seconds", str(BUDGET_S),
         "--seed", str(seed), "--repair", repair, "--skip-warmup"],
        capture_output=True, text=True, cwd=str(REPO),
    )
    out = proc.stdout + proc.stderr
    with open(log, "w") as f: f.write(out)
    scores = re.findall(r"matched=(\d+)|score=(\d+)|matches: (\d+)", out)
    best = 0
    for tup in scores:
        for s in tup:
            if s: best = max(best, int(s))
    best_marks = re.findall(r"best.*?(\d+)", out)
    for s in best_marks:
        try:
            v = int(s)
            if 0 < v < 1000: best = max(best, v)
        except: pass
    return best


def main():
    print(f"OUT_DIR={OUT_DIR}", flush=True)
    rows = []
    for label, puzzle in PUZZLES:
        size = int(label.split("x")[0])
        target = (size - 1) * size + size * (size - 1)
        print(f"\n=== {label}  (target={target}) ===", flush=True)
        for repair in REPAIRS:
            scores = []
            for seed in SEEDS:
                best = run(puzzle, repair, seed)
                scores.append(best)
                rows.append({"puzzle": label, "repair": repair, "seed": seed,
                            "target": target, "best": best,
                            "pct": best/target*100})
            med = sorted(scores)[len(scores)//2]
            print(f"  {repair:>9}: scores={scores}  median={med}  ({med/target*100:.1f}%)", flush=True)

    with open(OUT_DIR / "results.json", "w") as f:
        json.dump(rows, f, indent=2)
    # Summary table.
    print(f"\n=== HEAD-TO-HEAD TABLE ===", flush=True)
    print(f"{'puzzle':>10} {'target':>7} {'sa_med':>7} {'fil_med':>8} {'sa%':>6} {'fil%':>6} {'Δ':>5}", flush=True)
    for label, _ in PUZZLES:
        sa_scores = [r['best'] for r in rows if r['puzzle']==label and r['repair']=='sa']
        fil_scores = [r['best'] for r in rows if r['puzzle']==label and r['repair']=='filament']
        if not sa_scores or not fil_scores: continue
        sa_med = sorted(sa_scores)[len(sa_scores)//2]
        fil_med = sorted(fil_scores)[len(fil_scores)//2]
        target = rows[next(i for i,r in enumerate(rows) if r['puzzle']==label)]['target']
        sa_pct = sa_med/target*100
        fil_pct = fil_med/target*100
        delta = fil_pct - sa_pct
        print(f"{label:>10} {target:>7} {sa_med:>7} {fil_med:>8} "
              f"{sa_pct:>5.1f}% {fil_pct:>5.1f}% {delta:>+5.1f}", flush=True)


if __name__ == "__main__":
    main()
