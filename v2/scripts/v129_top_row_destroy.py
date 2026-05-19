#!/usr/bin/env python3
"""V129-T4 — PALIMPSEST top-rows-targeted destroy.

Heatmap finding: trap density is concentrated in rows 0-3.
Strategy: take the 461 base, BREAK the top 3 rows by piece-permutation,
then run ALNS basic. ALNS will repair from the broken top, hopefully
exploring a new basin.

Three variants:
  A) Cycle-permute 6 positions in rows 1-2 (light break)
  B) Cycle-permute 12 positions in rows 0-3 (medium break)
  C) FULL SCRAMBLE of all 48 positions in rows 0-2 (heavy break)

For variant C, this is effectively re-DFS-ing the top 3 rows; ALNS
basic might find a different bottom-up assembly.

Hint preservation: hint positions 34 and 45 are in rows 2-2,
respectively. We avoid moving them in variants A and B.
For variant C, we ALSO avoid the hint positions.
"""

from __future__ import annotations
import json
import subprocess
import sys
import time
import random
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
W = 16
N_CELLS = 256
HINTS = {34, 45, 135, 210, 221}


def load_record(path):
    d = json.load(open(path))
    pl = {}
    for i, p in enumerate(d.get("placement", [])):
        if isinstance(p, dict):
            pos = p.get("pos", i)
            pl[int(pos)] = (int(p["piece_id"]), int(p["rotation"]))
    return pl, d


def main():
    BASE = REPO / "output/vol-125/records/RECORD_461_bf_bw_off110_seed42.json"
    base_pl, _ = load_record(BASE)

    OUT_DIR = REPO / "output/vol-129" / f"top_row_destroy_{time.strftime('%Y%m%dT%H%M%S')}"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"OUT_DIR={OUT_DIR}", flush=True)

    # Row groupings.
    rows_1_2 = [r * W + c for r in [1, 2] for c in range(W) if (r*W+c) not in HINTS]
    rows_0_3 = [r * W + c for r in [0, 1, 2, 3] for c in range(W) if (r*W+c) not in HINTS]
    rows_0_2 = [r * W + c for r in [0, 1, 2] for c in range(W) if (r*W+c) not in HINTS]

    SEEDS = [42, 1, 7]

    procs = []
    variants = [
        ("A", 6, rows_1_2),
        ("B", 12, rows_0_3),
        ("C", 48, rows_0_2),  # essentially all of rows 0-2
    ]

    for variant_name, swap_n, positions in variants:
        for seed in SEEDS:
            # Cycle-permute swap_n positions.
            rng = random.Random(seed * 100 + swap_n)
            chosen = rng.sample(positions, min(swap_n, len(positions)))
            new_pl = dict(base_pl)
            cyc = list(chosen)
            rng.shuffle(cyc)
            pieces = [new_pl[p] for p in cyc]
            shifted = pieces[1:] + [pieces[0]]
            for pos, pr in zip(cyc, shifted):
                new_pl[pos] = pr

            start_path = OUT_DIR / f"start_{variant_name}_s{seed}.json"
            with open(start_path, "w") as f:
                json.dump({"matched": -1,
                           "placement": [
                               {"pos": p, "piece_id": pr[0], "rotation": pr[1]}
                               for p, pr in sorted(new_pl.items())
                           ],
                           "variant": variant_name,
                           "swap_n": swap_n}, f, indent=2)

            r = subprocess.run(
                [str(REPO / "target/bench-fast/rescore_board"), str(start_path)],
                capture_output=True, text=True)
            print(f"  {variant_name} seed={seed}: {r.stdout.strip().split(chr(10))[-1]}", flush=True)

            log = OUT_DIR / f"alns_{variant_name}_s{seed}.log"
            cmd = [str(REPO / "target/bench-fast/alns_only"),
                   "--cp-board", str(start_path),
                   "--ops", "basic",
                   "--alns-budget-ms", "1800000",
                   "--seed", str(seed)]
            f = open(log, "w")
            p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=str(REPO))
            procs.append((variant_name, seed, p, f, log))

    print(f"\nLaunched {len(procs)} ALNS jobs. Waiting...", flush=True)
    for variant_name, seed, p, f, log in procs:
        p.wait()
        f.close()
        with open(log) as fh:
            content = fh.read()
        scores = []
        for line in content.split("\n"):
            if "matched=" in line:
                try:
                    scores.append(int(line.split("matched=")[1].split()[0].strip(",")))
                except: pass
        best = max(scores) if scores else None
        print(f"  {variant_name} seed={seed}: best={best}", flush=True)

    # Summary.
    print(f"\n--- Summary ---", flush=True)
    summary = {}
    for variant_name, seed, p, f, log in procs:
        with open(log) as fh:
            content = fh.read()
        scores = []
        for line in content.split("\n"):
            if "matched=" in line:
                try: scores.append(int(line.split("matched=")[1].split()[0].strip(",")))
                except: pass
        best = max(scores) if scores else None
        summary[f"{variant_name}_s{seed}"] = best
    with open(OUT_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
