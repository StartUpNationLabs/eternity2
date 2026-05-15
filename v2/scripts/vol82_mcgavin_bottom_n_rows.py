#!/usr/bin/env python3
"""Vol-82 — Pin McGavin's BOTTOM N rows, let ALNS reconstruct TOP.

Vol-68 tested top-N pinning: N=14 (rows 0..13, 224 pieces) is the
sharp threshold for reconstructing McGavin's 469. N=13 gave only 455.

This script tests the REVERSE: pin bottom N rows, see if ALNS can
reconstruct the top.

If bottom-N has a similar sharp threshold (e.g., N=14 → 469), then
McGavin's basin has TWO independent rigid sub-structures (top and
bottom).

If bottom-N gives a different threshold or no reconstruction at any
N, then the basin's rigidity is asymmetric — top is the determining
half, bottom is interchangeable. This is structural information
unique to McGavin's basin.

Output: output/vol-82-bottom-N-{TS}/
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

MCG_PATH = "output/vol-65/mcgavin_469.json"


def load_mcgavin():
    with open(MCG_PATH) as f:
        d = json.load(f)
    placements = []
    for idx, item in enumerate(d["placement"]):
        if item is None: continue
        pos = item.get("pos", idx)
        placements.append((pos, item["piece_id"], item["rotation"]))
    return placements


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget-ms", type=int, default=60000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--n-rows", type=str, default="11,12,13,14",
                    help="comma-separated list of N (rows to pin from bottom)")
    args = ap.parse_args()

    ns = [int(x) for x in args.n_rows.split(",")]
    mcg = load_mcgavin()

    ts = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    out_dir = Path(f"output/vol-82-bottom-N-{ts}")
    out_dir.mkdir(parents=True, exist_ok=True)

    readme = out_dir / "README.txt"
    with open(readme, "w") as rf:
        rf.write(f"Vol-82 — McGavin bottom-N row pinning experiment\n")
        rf.write(f"Started: {datetime.datetime.now()}\n")
        rf.write(f"Source: {MCG_PATH}\n")
        rf.write(f"N values: {ns}\n")
        rf.write(f"Budget per N: {args.budget_ms}ms\n")
        rf.write(f"Seed: {args.seed}\n")
        rf.write(f"---\n")

    results = []
    for N in ns:
        # Bottom N rows = positions where row >= 16 - N, i.e., pos // 16 >= 16 - N
        lo_row = 16 - N
        pins = [(pos, pid, rot) for (pos, pid, rot) in mcg if (pos // 16) >= lo_row]
        n_pins = len(pins)
        print(f"\nN={N}: pinning rows {lo_row}..15 = {n_pins} pieces")

        partial = {
            "matched": 0,
            "placement": [
                {"pos": p, "piece_id": pid, "rotation": rot}
                for p, pid, rot in pins
            ],
        }
        partial_path = out_dir / f"bottom_N{N}_partial.json"
        with open(partial_path, "w") as f:
            json.dump(partial, f)

        # Run ALNS from this partial. Use winning5 ops; same as vol-68 used.
        log_path = out_dir / f"bottom_N{N}_seed{args.seed}.log"
        result_path = out_dir / f"bottom_N{N}_seed{args.seed}_result.json"
        with open(readme, "a") as rf:
            rf.write(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] N={N} pins={n_pins} budget={args.budget_ms}ms\n")

        proc = subprocess.run(
            ["target/release/alns_only",
             "--cp-board", str(partial_path),
             "--alns-budget-ms", str(args.budget_ms),
             "--seed", str(args.seed),
             "--ops", "winning5",
             "--t", "1.0"],
            capture_output=True, text=True, timeout=args.budget_ms / 1000 + 30,
        )
        with open(log_path, "w") as lf:
            lf.write(proc.stdout)
            lf.write("\n--- STDERR ---\n")
            lf.write(proc.stderr)

        # Find saved board path
        saved = None
        for line in (proc.stdout + proc.stderr).split("\n"):
            if line.startswith("saved:"):
                saved = line.split(":", 1)[1].strip()
                break

        if saved and Path(saved).exists():
            with open(saved) as f:
                board = json.load(f)
            score = board.get("matched", 0)
            print(f"  -> score = {score}/480 (saved: {saved})")
            results.append((N, n_pins, score, saved))
            # Copy result for archive
            import shutil
            shutil.copy(saved, result_path)
        else:
            print(f"  -> FAILED (no saved board)")
            results.append((N, n_pins, None, None))

        with open(readme, "a") as rf:
            rf.write(f"  score: {results[-1][2]}\n")

    print(f"\n=== FINAL ===")
    print(f"{'N':>3} | {'pins':>5} | {'score':>5}")
    for N, pins, score, _ in results:
        print(f"{N:>3} | {pins:>5} | {score!s:>5}")
    with open(readme, "a") as rf:
        rf.write(f"\n=== FINAL ===\n")
        rf.write(f"{'N':>3} | {'pins':>5} | {'score':>5}\n")
        for N, pins, score, _ in results:
            rf.write(f"{N:>3} | {pins:>5} | {score!s:>5}\n")

    return out_dir


if __name__ == "__main__":
    main()
