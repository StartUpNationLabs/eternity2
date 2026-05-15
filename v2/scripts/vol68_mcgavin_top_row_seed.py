#!/usr/bin/env python3
"""Vol-68 — Seed ALNS with McGavin's exact top row, run pipeline.

Extract McGavin 469's top row (16 piece-placements at positions 0-15)
and use as --extra-hint for alns_only. Random interior, McGavin frame.
If our pipeline lands near McGavin (Hamming << 247), we've bridged.

Builds extra_hint args for alns_only: pos:pid:rot per pin.
Then runs ALNS-from-empty or ALNS-from-partial.

Note: alns_only's --extra-hint adds pins on top of canonical hints.
For now: just pin McGavin's top row and run.
"""

import json
import subprocess
import sys
from pathlib import Path

MCG_PATH = "output/vol-65/mcgavin_469.json"


def main():
    with open(MCG_PATH) as f:
        d = json.load(f)

    # Extract top-row placements (pos 0..15)
    top_row_pins = []
    for idx, item in enumerate(d["placement"]):
        if item is None: continue
        pos = item.get("pos", idx)
        if 0 <= pos < 16:
            top_row_pins.append((pos, item["piece_id"], item["rotation"]))

    print(f"McGavin top-row pins: {len(top_row_pins)}")
    for pos, pid, rot in sorted(top_row_pins):
        print(f"  pos {pos}: piece {pid} rot {rot}")

    # We need to seed alns_only with a starting board that has these pins.
    # Easiest: create a partial JSON that has only these 16 cells filled.
    partial = {
        "matched": 0,
        "placement": [
            {"pos": pos, "piece_id": pid, "rotation": rot}
            for pos, pid, rot in top_row_pins
        ],
    }
    Path("output/vol-68").mkdir(parents=True, exist_ok=True)
    out_path = "output/vol-68/mcgavin_top_row_partial.json"
    with open(out_path, "w") as f:
        json.dump(partial, f)
    print(f"\nSaved partial to {out_path}")
    print(f"This is 16 placed pieces (top row only). ALNS will fill the rest.")

    # Note: alns_only expects a complete board to start from. Top-row-only
    # may not be directly accepted. Let's check the binary's behavior:
    # Run it once with this partial and see what happens.
    result = subprocess.run(
        ["target/release/alns_only", "--cp-board", out_path,
         "--alns-budget-ms", "5000", "--seed", "1", "--ops", "minimal",
         "--t", "1.0"],
        capture_output=True, text=True, timeout=30,
    )
    print(f"\nALNS test run (5s):")
    print(f"  stdout (first 500 chars): {result.stdout[:500]}")
    print(f"  stderr (first 500 chars): {result.stderr[:500]}")


if __name__ == "__main__":
    main()
