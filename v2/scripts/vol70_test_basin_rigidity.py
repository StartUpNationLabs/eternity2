#!/usr/bin/env python3
"""Vol-70 day 1 — Test rigidity of our basin-component reps.

For each rep, pin top-14 rows + run ALNS with N seeds. If all
seeds converge to the same score (within ±1), basin is RIGID.
Otherwise LOOSE.

Hypothesis: McGavin's basin is rigid. Our basins are loose.
Test: how many rigid basins exist in our 47 saved reps?
"""

import json
import subprocess
import sys
import time
from pathlib import Path


def main():
    n_seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    budget_ms = int(sys.argv[2]) if len(sys.argv) > 2 else 30000

    # Load 47 component reps
    with open("output/vol-67/components_db.json") as f:
        db = json.load(f)
    reps = db["components"]
    print(f"Testing rigidity of {len(reps)} basin-component reps")
    print(f"({n_seeds} seeds × {budget_ms/1000}s per rep)")
    print()

    SEEDS = [1, 17, 42, 100]
    if n_seeds > 4:
        SEEDS = list(range(1, n_seeds + 1))
    SEEDS = SEEDS[:n_seeds]

    results = []
    for r in reps:
        cid = r["component_id"]
        target = r["max_score"]
        if target < 458:
            continue  # focus on high-score basins
        # Build top-14 partial from rep
        rep_placement = r["rep_placement"]  # [[pid, pos], ...]
        # Position constraint: only keep cells in top 14 rows (pos < 224)
        pins = []
        for pid_pos in rep_placement:
            pid, pos = pid_pos
            if pos < 14 * 16:
                # Need rotation, but we only saved (pid, pos). Get full from source.
                pass
        # Actually let me re-load from rep_file to get rotations
        with open(r["rep_file"]) as f: full = json.load(f)
        partial_pins = []
        for idx, item in enumerate(full.get("placement", [])):
            if item is None: continue
            pos = item.get("pos", idx)
            if pos < 14 * 16:
                partial_pins.append({"pos": pos, "piece_id": item["piece_id"],
                                     "rotation": item["rotation"]})
        partial = {"matched": 0, "placement": partial_pins}
        Path("output/vol-70/rigidity_test").mkdir(parents=True, exist_ok=True)
        inp = f"output/vol-70/rigidity_test/comp{cid}_top14.json"
        with open(inp, "w") as f:
            json.dump(partial, f)

        scores = []
        for seed in SEEDS:
            proc = subprocess.run(
                ["target/release/alns_only", "--cp-board", inp,
                 "--alns-budget-ms", str(budget_ms), "--seed", str(seed),
                 "--ops", "winning5", "--t", "1.0"],
                capture_output=True, text=True, timeout=budget_ms / 1000 + 30,
            )
            saved = None
            for line in proc.stderr.split("\n") + proc.stdout.split("\n"):
                if line.startswith("saved:"):
                    saved = line.split(":", 1)[1].strip(); break
            if saved and Path(saved).exists():
                with open(saved) as f: result = json.load(f)
                scores.append(result.get("matched", 0))
            else:
                scores.append(None)

        ok_scores = [s for s in scores if s is not None]
        if not ok_scores:
            print(f"comp {cid} (target {target}): all seeds failed")
            continue
        max_s = max(ok_scores); min_s = min(ok_scores)
        spread = max_s - min_s
        rigid = "RIGID" if spread <= 1 else "loose"
        results.append((cid, target, ok_scores, spread, rigid))
        print(f"comp {cid:>3} (target {target}): scores={ok_scores}, "
              f"spread={spread}, {rigid}")

    print()
    print(f"SUMMARY:")
    n_rigid = sum(1 for r in results if r[4] == "RIGID")
    print(f"  RIGID basins: {n_rigid} / {len(results)}")
    print(f"  Spread distribution: {sorted([r[3] for r in results])}")


if __name__ == "__main__":
    main()
