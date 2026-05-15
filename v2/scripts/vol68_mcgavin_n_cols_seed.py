#!/usr/bin/env python3
"""Vol-68 — N-COLUMN scaling (mirror of N-row).

Pin McGavin's LEFTMOST N columns + run ALNS. See if threshold is
at N=14 (same as N-row) or different.

If same threshold: rigidity is symmetric across rows/cols.
If different: McGavin's basin has direction-specific structure.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

MCG = "output/vol-65/mcgavin_469.json"


def main():
    n_cols = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    budget_ms = int(sys.argv[2]) if len(sys.argv) > 2 else 60000
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1

    with open(MCG) as f:
        d = json.load(f)

    pins = []
    for idx, item in enumerate(d["placement"]):
        if item is None: continue
        pos = item.get("pos", idx)
        col = pos % 16
        if col < n_cols:
            pins.append({"pos": pos, "piece_id": item["piece_id"],
                          "rotation": item["rotation"]})

    partial = {"matched": 0, "placement": pins}
    Path("output/vol-68").mkdir(parents=True, exist_ok=True)
    out_path = f"output/vol-68/mcgavin_leftN{n_cols}_partial.json"
    with open(out_path, "w") as f:
        json.dump(partial, f)
    print(f"McGavin left-{n_cols}-cols pinned: {len(pins)} pieces")

    print(f"Running alns_only ({budget_ms}ms, seed={seed})...")
    proc = subprocess.run(
        ["target/release/alns_only", "--cp-board", out_path,
         "--alns-budget-ms", str(budget_ms), "--seed", str(seed),
         "--ops", "winning5", "--t", "1.0"],
        capture_output=True, text=True, timeout=budget_ms / 1000 + 60,
    )

    saved = None
    for line in proc.stderr.split("\n") + proc.stdout.split("\n"):
        if line.startswith("saved:"):
            saved = line.split(":", 1)[1].strip()
            break
    if saved and Path(saved).exists():
        with open(saved) as f: result = json.load(f)
        score = result.get("matched", 0)
        print(f"Final score: {score}/480")
    else:
        print("No saved output")


if __name__ == "__main__":
    main()
