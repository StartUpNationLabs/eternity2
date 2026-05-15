#!/usr/bin/env python3
"""Vol-68 — Find minimal McGavin pin-set that ALNS extends to 469.

Strategy: start with top-13 rows (208 pieces, N=13 gives 455 base).
Add cells one at a time from rows 13-15, see which addition lifts
score to 469.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

MCG = "output/vol-65/mcgavin_469.json"


def main():
    with open(MCG) as f:
        d = json.load(f)
    placements_by_pos = {item.get("pos", i): item
                         for i, item in enumerate(d["placement"]) if item}

    # Base: top 13 rows (positions 0..207)
    base_positions = set(range(13 * 16))

    # Candidate additions: all cells in rows 13-15 (positions 208-255)
    candidates = list(range(13 * 16, 256))

    # Greedy: add one candidate, run ALNS 30s, see if score reaches 469.
    # If yes, that single cell is the key. If no, try the next.
    print(f"Testing each single-cell addition to top-13 base...")
    print(f"{'added_pos':<10} | {'(r,c)':<8} | piece_McGavin | score")
    for pos in candidates:
        item = placements_by_pos[pos]
        r, c = divmod(pos, 16)
        # Build partial
        pins = []
        for p in base_positions:
            pins.append(placements_by_pos[p])
        pins.append(item)
        partial = {"matched": 0, "placement": pins}
        Path("output/vol-68/minimal_pin").mkdir(parents=True, exist_ok=True)
        inp = f"output/vol-68/minimal_pin/base13_plus_{pos}.json"
        with open(inp, "w") as f:
            json.dump(partial, f)
        proc = subprocess.run(
            ["target/release/alns_only", "--cp-board", inp,
             "--alns-budget-ms", "30000", "--seed", "1",
             "--ops", "winning5", "--t", "1.0"],
            capture_output=True, text=True, timeout=60,
        )
        saved = None
        for line in proc.stderr.split("\n") + proc.stdout.split("\n"):
            if line.startswith("saved:"):
                saved = line.split(":", 1)[1].strip()
                break
        if saved and Path(saved).exists():
            with open(saved) as f: result = json.load(f)
            score = result.get("matched", 0)
            marker = " ★" if score >= 469 else ""
            print(f"{pos:<10} | ({r},{c}) | {item['piece_id']:>4}{marker} | {score}")
        else:
            print(f"{pos:<10} | ({r},{c}) | ERROR")


if __name__ == "__main__":
    main()
