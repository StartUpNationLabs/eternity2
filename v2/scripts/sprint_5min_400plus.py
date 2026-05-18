#!/usr/bin/env python3
"""5-minute sprint: generate boards >= 400 using bf_bw (our fastest record-producer).

7 parallel workers, each cycling 30-sec bf_bw runs with random seed-offset.
Saves any partial with score >= 400 to output/vol-125/sprint_5min_*/sprint_*.json.
"""

import json
import os
import random
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path


REPO = Path("/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2")
BF_BW = REPO / "target" / "bench-fast" / "bf_bw"
OUT_DIR = REPO / "output" / "vol-125" / f"sprint_5min_{datetime.now():%Y%m%dT%H%M%S}"
OUT_DIR.mkdir(parents=True, exist_ok=True)

WORKERS = 7
TOTAL_BUDGET_SEC = 300
PER_JOB_BF_MS = 30000  # 30 sec per bf_bw call
PER_JOB_TIMEOUT_SEC = 40  # SIGKILL after 40s as safety


def run_one(worker_id: int, offset: int) -> tuple[int, str | None]:
    """Run one bf_bw job. Returns (score, saved_path or None)."""
    partial_path = OUT_DIR / f"w{worker_id}_off{offset}_p.json"
    try:
        subprocess.run(
            [
                str(BF_BW),
                "--threads", "1",
                "--seed-offset", str(offset),
                "--budget-ms", str(PER_JOB_BF_MS),
                "--dump-partial", str(partial_path),
            ],
            cwd=REPO,
            timeout=PER_JOB_TIMEOUT_SEC,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return 0, None
    except Exception:
        return 0, None

    if not partial_path.exists():
        return 0, None

    try:
        with open(partial_path) as f:
            data = json.load(f)
    except Exception:
        partial_path.unlink(missing_ok=True)
        return 0, None

    score = data.get("score", data.get("matched", 0))
    if not isinstance(score, int):
        partial_path.unlink(missing_ok=True)
        return 0, None

    if score >= 400:
        final_path = OUT_DIR / f"sprint_w{worker_id}_off{offset}_score{score}.json"
        partial_path.rename(final_path)
        return score, str(final_path)
    else:
        partial_path.unlink(missing_ok=True)
        return score, None


def worker_loop(worker_id: int, end_time: float, results_queue: list):
    """Each worker keeps running bf_bw with random offsets until budget exhausted."""
    runs = 0
    saves = 0
    while time.time() < end_time:
        offset = random.randint(0, 9999)
        score, path = run_one(worker_id, offset)
        runs += 1
        if path:
            saves += 1
            results_queue.append((score, path))
            print(f"[worker {worker_id}] off={offset} score={score} → saved ({saves} saves)", flush=True)
    print(f"[worker {worker_id}] done, runs={runs} saves={saves}", flush=True)
    return runs, saves


def main():
    print(f"OUT_DIR={OUT_DIR}", flush=True)
    print(f"Workers={WORKERS}, total budget={TOTAL_BUDGET_SEC}s, per-bf-job={PER_JOB_BF_MS}ms", flush=True)

    end_time = time.time() + TOTAL_BUDGET_SEC
    # Use simple multiprocessing — each worker is a process running a loop.
    import multiprocessing as mp
    manager = mp.Manager()
    shared = manager.list()
    procs = []
    for i in range(WORKERS):
        p = mp.Process(target=worker_loop, args=(i, end_time, shared))
        p.start()
        procs.append(p)
    for p in procs:
        p.join(timeout=TOTAL_BUDGET_SEC + 60)
        if p.is_alive():
            p.terminate()

    # Tally.
    saved_files = sorted(OUT_DIR.glob("sprint_w*_off*_score*.json"))
    print()
    print(f"=== SPRINT COMPLETE ===")
    print(f"Saved boards >= 400: {len(saved_files)}")
    print(f"Output: {OUT_DIR}")

    score_hist = {}
    for f in saved_files:
        # filename: sprint_wX_offY_scoreZ.json
        try:
            score = int(f.stem.split("score")[-1])
        except ValueError:
            continue
        score_hist[score] = score_hist.get(score, 0) + 1

    print("\nScore distribution:")
    for sc in sorted(score_hist.keys(), reverse=True):
        print(f"  {sc}: {score_hist[sc]} files")


if __name__ == "__main__":
    main()
