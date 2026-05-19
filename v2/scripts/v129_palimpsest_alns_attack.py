#!/usr/bin/env python3
"""V129-T3 — PALIMPSEST attack: deliberate-trap-destroy ALNS.

Take a 461 record (which is IN the consensus-trap basin), force-destroy
the trap-positions, run ALNS basic.

Setup:
  1. Load top 50 consensus-trap pairs from V129-T1.
  2. Build a starting board from our 461 (off=110 seed=42).
  3. Identify the 50 specific trap pairs IN this board.
  4. Find a "wedge": pick the position that, if destroyed, breaks
     the MOST trap pairs while preserving high-cat-A pairs.
  5. Run ALNS basic 30min × 6 seeds, with these positions
     marked as PRIORITY destroy targets via extra random
     restart hints.

Implementation reality: alns_only doesn't have "destroy-here-first"
option; closest is to RANDOMIZE the destroy by setting a particular
seed. So instead: take the 461 record, manually SWAP some pieces at
trap positions to non-trap pieces (introducing 4-8 mismatches), then
re-feed to ALNS. ALNS basic will preferentially destroy those
intentionally-broken regions via worst-band.
"""

from __future__ import annotations
import json
import subprocess
import sys
import time
from pathlib import Path
from collections import defaultdict
import random

REPO = Path(__file__).resolve().parents[1]
W = 16
N_CELLS = 256


def load_record(path):
    d = json.load(open(path))
    pl = {}
    for i, p in enumerate(d.get("placement", [])):
        if isinstance(p, dict):
            pos = p.get("pos", i)
            pl[int(pos)] = (int(p["piece_id"]), int(p["rotation"]))
    return pl, d


def main():
    # Load latest PALIMPSEST consensus.
    cons_dirs = sorted((REPO / "output/vol-129").glob("palimpsest_*"))
    if not cons_dirs:
        print("ERROR: run v129_palimpsest_consensus.py first.")
        sys.exit(1)
    cons_path = cons_dirs[-1] / "consensus.json"
    cons = json.load(open(cons_path))
    print(f"Consensus from {cons_path}", flush=True)
    print(f"  cat_A: {len(cons['cat_A_likely_correct'])}  cat_B (traps): {len(cons['cat_B_consensus_traps'])}", flush=True)

    # Load base 461.
    BASE = REPO / "output/vol-125/records/RECORD_461_bf_bw_off110_seed42.json"
    base_pl, base_d = load_record(BASE)
    print(f"Base 461: matched={base_d.get('matched')}", flush=True)

    # Find which top-50 traps are present in our base.
    base_traps_present = []
    top_traps = cons["cat_B_consensus_traps"][:200]
    for t in top_traps:
        i, j, d, pi, ri, pj, rj = t["key"]
        if base_pl.get(i) == (pi, ri) and base_pl.get(j) == (pj, rj):
            base_traps_present.append(t)
    print(f"Top-200 traps PRESENT in our base 461: {len(base_traps_present)}", flush=True)

    # Print the present traps.
    print(f"\nFirst 20:", flush=True)
    for t in base_traps_present[:20]:
        i, j, d, pi, ri, pj, rj = t["key"]
        print(f"  i={i:>4} j={j:>4} d={d} pi={pi:>3} ri={ri} pj={pj:>3} rj={rj} cnt={t['count']:>3} max={t['max_score']}", flush=True)

    # For each present trap, mark BOTH positions as "to destroy".
    destroy_positions = set()
    for t in base_traps_present:
        destroy_positions.add(t["key"][0])
        destroy_positions.add(t["key"][1])
    print(f"\nUnique positions to destroy: {len(destroy_positions)}", flush=True)

    # Strategy: SWAP a small number of pieces at trap positions with random pieces from
    # OUTSIDE the trap-set. This artificially breaks ~K trap pairs, forcing ALNS
    # to repair around them instead of into them.
    # We KEEP the canonical 5 hints intact.
    HINTS = {34, 45, 135, 210, 221}
    swappable = [p for p in destroy_positions if p not in HINTS]
    print(f"Trap positions excluding canonical hints: {len(swappable)}", flush=True)

    # OUT_DIR.
    OUT_DIR = REPO / "output/vol-129" / f"palimpsest_attack_{time.strftime('%Y%m%dT%H%M%S')}"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"OUT_DIR={OUT_DIR}", flush=True)

    # For each of several swap-counts, prepare a starting board.
    SWAP_COUNTS = [4, 8, 12]
    SEEDS = [42, 1, 7]
    rng = random.Random(2026)
    procs = []

    for swap_n in SWAP_COUNTS:
        for seed in SEEDS:
            # Permute swap_n piece positions.
            rng_local = random.Random(seed * 100 + swap_n)
            chosen = rng_local.sample(swappable, min(swap_n, len(swappable)))
            # Cycle-permute the pieces at chosen positions.
            new_pl = dict(base_pl)
            cyc = list(chosen)
            rng_local.shuffle(cyc)
            old_pieces = [new_pl[p] for p in cyc]
            shifted = old_pieces[1:] + [old_pieces[0]]
            for pos, pr in zip(cyc, shifted):
                new_pl[pos] = pr

            # Save.
            start_path = OUT_DIR / f"start_n{swap_n}_s{seed}.json"
            placement_list = [
                {"pos": p, "piece_id": pr[0], "rotation": pr[1]}
                for p, pr in sorted(new_pl.items())
            ]
            with open(start_path, "w") as f:
                json.dump({"matched": -1, "placement": placement_list,
                           "source": str(BASE.name),
                           "swap_n": swap_n, "swap_seed": seed,
                           "swapped_positions": cyc}, f, indent=2)

            # Rescore.
            r = subprocess.run([str(REPO/"target/bench-fast/rescore_board"), str(start_path)],
                              capture_output=True, text=True)
            score_line = r.stdout.strip().split("\n")[-1]
            print(f"  swap_n={swap_n} seed={seed}: {score_line}", flush=True)

            # Launch ALNS basic 30min.
            log = OUT_DIR / f"alns_n{swap_n}_s{seed}.log"
            cmd = [str(REPO / "target/bench-fast/alns_only"),
                   "--cp-board", str(start_path),
                   "--ops", "basic",
                   "--alns-budget-ms", "1800000",
                   "--seed", str(seed)]
            f = open(log, "w")
            p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=str(REPO))
            procs.append((swap_n, seed, p, f, log))

            # Throttle: max 6 jobs in parallel
            running = [(sn, sd, pp, ff, ll) for sn, sd, pp, ff, ll in procs if pp.poll() is None]
            while len(running) >= 6:
                time.sleep(2)
                running = [(sn, sd, pp, ff, ll) for sn, sd, pp, ff, ll in procs if pp.poll() is None]

    # Wait for all.
    print(f"\nWaiting for {len(procs)} jobs...", flush=True)
    for swap_n, seed, p, f, log in procs:
        p.wait()
        f.close()
        with open(log) as fh:
            content = fh.read()
        scores = []
        for line in content.split("\n"):
            if "matched=" in line:
                tok = line.split("matched=")[1].split()[0].strip(",")
                try: scores.append(int(tok))
                except: pass
        best = max(scores) if scores else None
        print(f"  swap_n={swap_n} seed={seed}: best={best}", flush=True)


if __name__ == "__main__":
    main()
