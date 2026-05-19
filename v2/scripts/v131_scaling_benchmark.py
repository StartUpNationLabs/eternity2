#!/usr/bin/env python3
"""V131-T2 — Scaling-curve benchmark.

Generate puzzle suite at sizes {6, 7, 8, 10, 12, 14} × 3 seeds each.
For each: run alns_e2 for 60s, record best score, time-to-solve.

Output: scaling table + JSON for later plotting.
"""

from __future__ import annotations
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "output/vol-131" / f"scaling_bench_{time.strftime('%Y%m%dT%H%M%S')}"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SIZES_COLORS = [
    (6, 4),
    (7, 5),
    (8, 6),
    (10, 8),
    (12, 10),
    (14, 12),
]
SEEDS = [42, 1, 7]
BUDGET_S = 60


def gen_puzzle(size, n_colors, seed, out_csv):
    subprocess.run(
        [str(REPO / "target/bench-fast/gen_small_csv"),
         str(size), str(n_colors), str(seed), str(out_csv)],
        check=True, capture_output=True,
    )


def total_edges(size):
    return (size - 1) * size + size * (size - 1)


def run_alns(puzzle_path, seed, budget_s):
    """Run alns_e2 on the puzzle. Returns (best_score, total_edges, elapsed_s)."""
    log_path = OUT_DIR / (puzzle_path.stem + f"_seed{seed}.log")
    t0 = time.time()
    proc = subprocess.run(
        [str(REPO / "target/bench-fast/alns_e2"),
         "--puzzle", str(puzzle_path),
         "--seconds", str(budget_s),
         "--seed", str(seed),
         "--skip-warmup"],
        capture_output=True, text=True, cwd=str(REPO),
    )
    elapsed = time.time() - t0
    with open(log_path, "w") as f:
        f.write(proc.stdout + "\n---STDERR---\n" + proc.stderr)

    # Parse best score from stderr/stdout
    output = proc.stdout + proc.stderr
    scores = re.findall(r"matched=(\d+)|score=(\d+)|matches: (\d+)", output)
    best = 0
    for tup in scores:
        for s in tup:
            if s:
                best = max(best, int(s))
    # Also look for "best=N" patterns
    best_marks = re.findall(r"best.*?(\d+)", output)
    for s in best_marks:
        try:
            v = int(s)
            if 0 < v < 1000:
                best = max(best, v)
        except: pass
    return best, elapsed, log_path


def main():
    print(f"OUT_DIR={OUT_DIR}", flush=True)

    results = []
    for size, n_colors in SIZES_COLORS:
        size_results = []
        for seed in SEEDS:
            puzzle_path = OUT_DIR / f"puzzle_s{size}_c{n_colors}_seed{seed}.csv"
            gen_puzzle(size, n_colors, seed, puzzle_path)
            t_edges = total_edges(size)
            print(f"\nsize={size}×{size}/c{n_colors}  seed={seed}  target={t_edges}", flush=True)

            best, elapsed, log = run_alns(puzzle_path, seed, BUDGET_S)
            pct = best / t_edges * 100 if t_edges > 0 else 0
            solved = (best == t_edges)
            print(f"  best={best}/{t_edges} ({pct:.1f}%)  elapsed={elapsed:.1f}s  solved={solved}", flush=True)
            size_results.append({
                "size": size, "n_colors": n_colors, "seed": seed,
                "target_edges": t_edges,
                "best": best, "pct": pct, "elapsed_s": elapsed,
                "solved": solved, "log": str(log),
            })
        # Stats per size.
        scores = [r["best"] for r in size_results]
        pcts = [r["pct"] for r in size_results]
        print(f"  size={size}: scores={scores}  median pct={sorted(pcts)[len(pcts)//2]:.1f}%", flush=True)
        results.extend(size_results)

    with open(OUT_DIR / "results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n=== SCALING TABLE ===", flush=True)
    print(f"{'size':>5} {'cols':>5} {'seed':>5} {'target':>7} {'best':>6} {'pct':>6} {'solved':>7}", flush=True)
    for r in results:
        print(f"{r['size']:>5} {r['n_colors']:>5} {r['seed']:>5} "
              f"{r['target_edges']:>7} {r['best']:>6} {r['pct']:>5.1f}% "
              f"{'YES' if r['solved'] else 'no':>7}", flush=True)


if __name__ == "__main__":
    main()
