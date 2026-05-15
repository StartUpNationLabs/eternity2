#!/usr/bin/env python3
"""Vol-77 — ALNS from each enumerated frame.

Different angle from vol-76 CAS-from-frames:
For each frame, pin shell-0 (60 cells) and run ALNS on the
remaining 196 interior cells.

Hypothesis: some frames extend to higher ALNS scores than others.
Best score across frames = the BEST our pipeline can do from that
frame's specific outer color profile.
"""

import glob
import json
import subprocess
import sys
import time
from pathlib import Path


def main():
    n_frames = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    budget_ms = int(sys.argv[2]) if len(sys.argv) > 2 else 60000
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1

    frame_files = sorted(glob.glob("output/vol-76/frame_solution_*.json"))[:n_frames]
    print(f"Testing ALNS-from-frame on {len(frame_files)} frames, seed={seed}, budget={budget_ms}ms")
    print(f"{'frame':<35} | {'score':>5}")

    best = (0, None)
    for fp in frame_files:
        proc = subprocess.run(
            ["target/release/alns_only", "--cp-board", fp,
             "--alns-budget-ms", str(budget_ms), "--seed", str(seed),
             "--ops", "winning5", "--t", "1.0"],
            capture_output=True, text=True, timeout=budget_ms / 1000 + 60,
        )
        saved = None
        for line in (proc.stderr + proc.stdout).split("\n"):
            if line.startswith("saved:"):
                saved = line.split(":", 1)[1].strip(); break
        if saved and Path(saved).exists():
            with open(saved) as f: data = json.load(f)
            sc = data.get("matched", 0)
            print(f"{Path(fp).stem:<35} | {sc:>5}")
            if sc > best[0]:
                best = (sc, fp)
        else:
            print(f"{Path(fp).stem:<35} | FAILED")

    print(f"\nBest score: {best[0]} from {best[1]}")


if __name__ == "__main__":
    main()
