#!/usr/bin/env python3
"""Vol-68 — Seed ALNS with McGavin's TOP N ROWS pinned.

For N in {1, 2, 4, 8}, extract McGavin's top N rows as partial board.
Run ALNS-only from each. See how score grows with N.

If score plateaus quickly (i.e., 2 rows already gives 460+), then
the row-2-onwards constraint is dominant. If only N=8 (half-board)
gives 460+, then McGavin's structure is HOLISTIC, not row-by-row.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

MCG = "output/vol-65/mcgavin_469.json"


def main():
    n_rows = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    budget_ms = int(sys.argv[2]) if len(sys.argv) > 2 else 300000
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    ops = sys.argv[4] if len(sys.argv) > 4 else "winning5"

    with open(MCG) as f:
        d = json.load(f)
    # Extract top N rows: positions 0..(16*n - 1)
    max_pos = 16 * n_rows
    pins = []
    for idx, item in enumerate(d["placement"]):
        if item is None: continue
        pos = item.get("pos", idx)
        if 0 <= pos < max_pos:
            pins.append({"pos": pos, "piece_id": item["piece_id"],
                          "rotation": item["rotation"]})

    partial = {"matched": 0, "placement": pins}
    Path("output/vol-68").mkdir(parents=True, exist_ok=True)
    out_path = f"output/vol-68/mcgavin_top{n_rows}_partial.json"
    with open(out_path, "w") as f:
        json.dump(partial, f)
    print(f"McGavin top-{n_rows}-rows pinned: {len(pins)} pieces")

    # Run alns_only
    print(f"Running alns_only (--ops {ops} seed={seed} budget={budget_ms}ms)...")
    t0 = time.time()
    proc = subprocess.run(
        ["target/release/alns_only", "--cp-board", out_path,
         "--alns-budget-ms", str(budget_ms), "--seed", str(seed),
         "--ops", ops, "--t", "1.0"],
        capture_output=True, text=True, timeout=budget_ms / 1000 + 60,
    )
    print(f"Time: {time.time() - t0:.1f}s")

    # Find saved output
    saved = None
    for line in proc.stderr.split("\n") + proc.stdout.split("\n"):
        if line.startswith("saved:"):
            saved = line.split(":", 1)[1].strip()
            break
    if saved and Path(saved).exists():
        with open(saved) as f: result = json.load(f)
        score = result.get("matched", 0)
        print(f"Final score: {score}/480")
        # Output also to a clearly-named result file
        result_path = f"output/vol-68/mcgavin_top{n_rows}_result_seed{seed}_ops{ops}.json"
        with open(result_path, "w") as f:
            json.dump(result, f)
        print(f"Saved to {result_path}")
    else:
        print(f"No saved output found. stderr tail: {proc.stderr[-500:]}")


if __name__ == "__main__":
    main()
