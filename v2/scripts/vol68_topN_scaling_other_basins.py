#!/usr/bin/env python3
"""Vol-68 — Test N-row scaling on local-459 and vol-32-458.

If McGavin's N=14 threshold is universal across basins, then for
ANY high-score basin, pinning top-14 rows + running our ALNS
reconstructs the original.

If NOT, then only McGavin's basin has this property — interesting
structural fact.
"""

import json
import subprocess
import sys
import time
from pathlib import Path


def main():
    sources = [
        ("local-459-p06", "output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json"),
        ("vol-32-458", "output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json"),
        ("vol-61-s17-458", "output/vol-61/faithful_sota_20260515T174124/stage3_seed17.json"),
    ]

    for name, path in sources:
        with open(path) as f:
            d = json.load(f)
        target_score = d.get("matched", 0)
        placements_by_pos = {item.get("pos", i): item
                              for i, item in enumerate(d["placement"]) if item}
        print(f"\n=== {name} (target {target_score}) ===")
        print(f"{'N rows':>6} | {'pins':>4} | {'score':>5} | {'gap':>5}")

        for n in [12, 13, 14, 15]:
            pins = [placements_by_pos[p] for p in range(16 * n) if p in placements_by_pos]
            partial = {"matched": 0, "placement": pins}
            Path("output/vol-68/topN_other_basins").mkdir(parents=True, exist_ok=True)
            inp = f"output/vol-68/topN_other_basins/{name}_top{n}.json"
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
                    saved = line.split(":", 1)[1].strip(); break
            if saved and Path(saved).exists():
                with open(saved) as f: result = json.load(f)
                score = result.get("matched", 0)
                gap = score - target_score
                sign = "+" if gap >= 0 else ""
                print(f"{n:>6} | {len(pins):>4} | {score:>5} | {sign}{gap}")
            else:
                print(f"{n:>6} | {len(pins):>4} | ERROR")


if __name__ == "__main__":
    main()
