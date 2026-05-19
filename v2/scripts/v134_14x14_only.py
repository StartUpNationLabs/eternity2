#!/usr/bin/env python3
"""V134 14x14 ONLY — complete the missing datapoint."""
import json, re, subprocess, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "output/vol-134" / f"14x14_only_{time.strftime('%Y%m%dT%H%M%S')}"
OUT.mkdir(parents=True, exist_ok=True)
print(f"OUT={OUT}", flush=True)

PUZZLE = REPO / "output/vol-131/scaling_bench_20260519T123004/puzzle_s14_c12_seed42.csv"
SEEDS = [42, 1, 7]
TARGET = 364

def run(repair, seed):
    log = OUT / f"{repair}_seed{seed}.log"
    proc = subprocess.run(
        [str(REPO/"target/bench-fast/alns_e2"),
         "--puzzle", str(PUZZLE), "--seconds", "60",
         "--seed", str(seed), "--repair", repair, "--skip-warmup"],
        capture_output=True, text=True, cwd=str(REPO),
    )
    out = proc.stdout + proc.stderr
    with open(log, "w") as f: f.write(out)
    m = re.search(r"best:\s*(\d+)/(\d+)", out)
    return int(m.group(1)) if m else 0

def main():
    rows = []
    for repair in ["sa", "filament"]:
        scores = []
        for seed in SEEDS:
            best = run(repair, seed)
            scores.append(best)
            print(f"  {repair} seed={seed}: {best}/{TARGET}", flush=True)
            rows.append({"repair": repair, "seed": seed, "best": best, "target": TARGET})
        med = sorted(scores)[len(scores)//2]
        print(f"  {repair} median: {med}/{TARGET} ({med/TARGET*100:.1f}%)", flush=True)
    with open(OUT / "results.json", "w") as f:
        json.dump(rows, f, indent=2)

if __name__ == "__main__":
    main()
