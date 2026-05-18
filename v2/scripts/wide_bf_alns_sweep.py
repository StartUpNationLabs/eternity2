#!/usr/bin/env python3
"""Wide bf_bw + ALNS sweep: 7 parallel workers, each cycling through:
- bf_bw with random seed-offset
- alns_only basic with random ALNS seed
Save any board scoring >= 462 (a new record).

This is the proven record-producer (offset=110 seed=42 found 461).
Wider sweep = more chances of finding 462+."""

import json
import random
import subprocess
import time
from datetime import datetime
from pathlib import Path
import multiprocessing as mp


REPO = Path("/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2")
BF_BW = REPO / "target" / "bench-fast" / "bf_bw"
ALNS = REPO / "target" / "bench-fast" / "alns_only"
PUZZLE = REPO.parent / "data" / "puzzles" / "size_16_official_eternity.csv"

OUT_DIR = REPO / "output" / "vol-125" / f"wide_sweep_{datetime.now():%Y%m%dT%H%M%S}"
OUT_DIR.mkdir(parents=True, exist_ok=True)

WORKERS = 7
TOTAL_BUDGET_SEC = 60 * 60 * 6  # 6 hours
BF_BW_BUDGET_MS = 60000  # 1 min bf_bw
ALNS_BUDGET_MS = 1800000  # 30 min ALNS
TARGET = 462  # record


def run_one_pipeline(worker_id: int, offset: int, alns_seed: int) -> dict | None:
    """One full bf_bw -> ALNS pipeline. Returns dict if found final result."""
    partial = OUT_DIR / f"w{worker_id}_off{offset}_s{alns_seed}_partial.json"
    try:
        subprocess.run(
            [str(BF_BW),
             "--threads", "1",
             "--seed-offset", str(offset),
             "--budget-ms", str(BF_BW_BUDGET_MS),
             "--dump-partial", str(partial)],
            cwd=REPO, timeout=BF_BW_BUDGET_MS//1000 + 10,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False)
    except Exception:
        return None
    if not partial.exists(): return None

    final_log = OUT_DIR / f"w{worker_id}_off{offset}_s{alns_seed}_alns.log"
    try:
        # alns_only doesn't have --out-board; it prints to stdout / dumps internally.
        # We monitor by parsing the log.
        subprocess.run(
            [str(ALNS),
             "--cp-board", str(partial),
             "--ops", "basic",
             "--alns-budget-ms", str(ALNS_BUDGET_MS),
             "--seed", str(alns_seed)],
            cwd=REPO, timeout=ALNS_BUDGET_MS//1000 + 120,
            stdout=open(final_log, "w"), stderr=subprocess.STDOUT,
            check=False)
    except Exception:
        return None
    if not final_log.exists(): return None

    # Parse final log for best score.
    text = final_log.read_text()
    best = 0
    for line in text.splitlines():
        # Format: "ALNS: elapsed=Xs iters=Y placed=Z/256 matched=W/480 ..."
        if "matched=" in line:
            try:
                m = line.split("matched=")[1].split("/")[0]
                best = max(best, int(m))
            except Exception:
                pass
        if "new_best=" in line:
            try:
                m = line.split("new_best=")[1].split()[0]
                best = max(best, int(m))
            except Exception:
                pass
    partial.unlink(missing_ok=True)
    return {"worker_id": worker_id, "offset": offset, "alns_seed": alns_seed, "best": best, "log": str(final_log)}


def worker(worker_id: int, end_time: float, results_q):
    rng = random.Random(worker_id * 12345 + int(time.time()))
    runs = 0
    best_seen = 0
    while time.time() < end_time:
        offset = rng.randint(0, 9999)
        alns_seed = rng.randint(1, 10000)
        result = run_one_pipeline(worker_id, offset, alns_seed)
        if result is None: continue
        runs += 1
        best_seen = max(best_seen, result["best"])
        results_q.put(result)
        if result["best"] >= TARGET:
            print(f"🎯🎯 [w{worker_id}] OFFSET={offset} SEED={alns_seed} BEST={result['best']} >= TARGET={TARGET}!", flush=True)
    print(f"[w{worker_id}] done: {runs} runs, best={best_seen}", flush=True)


def main():
    print(f"OUT_DIR={OUT_DIR}", flush=True)
    print(f"Workers={WORKERS}, budget={TOTAL_BUDGET_SEC}s = {TOTAL_BUDGET_SEC/3600:.1f}h", flush=True)
    end_time = time.time() + TOTAL_BUDGET_SEC
    mgr = mp.Manager()
    q = mgr.Queue()
    procs = []
    for i in range(WORKERS):
        p = mp.Process(target=worker, args=(i, end_time, q))
        p.start()
        procs.append(p)

    # Drain queue periodically to print + save results.
    summary = []
    bests_by_band = {}
    last_print = time.time()
    while any(p.is_alive() for p in procs):
        try:
            while True:
                r = q.get(timeout=1)
                summary.append(r)
                bests_by_band[r["best"]] = bests_by_band.get(r["best"], 0) + 1
                if r["best"] >= 460:
                    print(f"  [w{r['worker_id']}] off={r['offset']} s={r['alns_seed']} → best={r['best']}", flush=True)
        except Exception:
            pass
        # Print summary every 5 min.
        if time.time() - last_print > 300:
            last_print = time.time()
            print(f"\n=== mid-sweep snapshot (total runs: {len(summary)}) ===", flush=True)
            for sc in sorted(bests_by_band.keys(), reverse=True):
                print(f"  best={sc}: {bests_by_band[sc]} runs", flush=True)
            print(flush=True)

    for p in procs:
        p.join()

    print(f"\n=== FINAL ===")
    print(f"Total runs: {len(summary)}")
    print(f"Distribution:")
    for sc in sorted(bests_by_band.keys(), reverse=True):
        print(f"  {sc}: {bests_by_band[sc]}")

    # Save the summary.
    summary_path = OUT_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"\nSaved summary to {summary_path}")


if __name__ == "__main__":
    main()
