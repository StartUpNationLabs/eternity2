#!/usr/bin/env python3
"""V129-T12 — Attack all 15 non-McGavin basin families.

For each of the 14 non-McGavin corner-perm basins with max score
458-461 (plus the 2 distinct McGavin-family records, totaling 15-16
distinct basins), run ALNS basic 30min × 1 seed.

This is the discriminative test: can any non-McGavin basin reach 462+?
If yes, it's a completely new finding.

Total compute: 15 × 30min = 7.5 CPU-hours. At 7 cores parallel,
~1.5 hours wallclock.

Run when CPU is free (after K-sweep finishes).
"""

from __future__ import annotations
import json
import subprocess
import sys
import time
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parents[1]
DB = REPO / "database-400-480"
W = 16
N_CELLS = 256


def load_record(p):
    try: d = json.load(open(p))
    except: return None
    m = d.get("matched")
    pl = d.get("placement", [])
    if not isinstance(m, int): return None
    placement = {int(pp.get("pos", i)): (int(pp["piece_id"]), int(pp["rotation"]))
                 for i, pp in enumerate(pl) if isinstance(pp, dict)}
    if len(placement) != N_CELLS: return None
    return m, placement


def main():
    # Get highest-score per corner perm.
    by_corner_best = {}
    by_corner_path = {}
    for path in sorted(DB.glob("*.json")):
        r = load_record(path)
        if r is None: continue
        m, pl = r
        if m < 458: continue
        cp = tuple(pl[c][0] for c in (0, 15, 240, 255))
        if cp not in by_corner_best or m > by_corner_best[cp][0]:
            by_corner_best[cp] = (m, pl, path.name)
            by_corner_path[cp] = path

    # Skip the 2 closely related to McGavin: keep them anyway as
    # different starting points.
    OUT_DIR = REPO / "output/vol-129" / f"15_basin_attack_{time.strftime('%Y%m%dT%H%M%S')}"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"OUT_DIR={OUT_DIR}", flush=True)

    SEED = 42
    procs = []
    MAX_PARALLEL = 7

    targets = sorted(by_corner_best.items(), key=lambda x: -x[1][0])
    for cp, (score, _, name) in targets:
        path = by_corner_path[cp]
        log = OUT_DIR / f"alns_{'_'.join(str(c) for c in cp)}_score{score}.log"
        cmd = [str(REPO / "target/bench-fast/alns_only"),
               "--cp-board", str(path),
               "--ops", "basic",
               "--alns-budget-ms", "1800000",
               "--seed", str(SEED)]
        f = open(log, "w")
        p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=str(REPO))
        procs.append((cp, score, p, f, log))
        print(f"  launched cp={cp} base={score} pid={p.pid}", flush=True)

        # Throttle to MAX_PARALLEL.
        while True:
            running = [(c, s, pp, ff, ll) for c, s, pp, ff, ll in procs if pp.poll() is None]
            if len(running) < MAX_PARALLEL: break
            time.sleep(5)

    # Wait all.
    print(f"\nWaiting for {len(procs)} jobs...", flush=True)
    for cp, score, p, f, log in procs:
        p.wait()
        f.close()

    # Collect.
    summary = {}
    for cp, score, p, f, log in procs:
        content = open(log).read()
        scores = []
        for line in content.split("\n"):
            if "matched=" in line:
                try: scores.append(int(line.split("matched=")[1].split()[0].strip(",")))
                except: pass
        best = max(scores) if scores else None
        summary[str(cp)] = {"base_score": score, "best": best}
        delta = best - score if best else None
        marker = "★" if best and best >= 462 else ""
        print(f"  cp={cp}: base={score} → best={best} (Δ{delta}) {marker}", flush=True)

    with open(OUT_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
