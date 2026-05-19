#!/usr/bin/env python3
"""V148 — basin compute sweep driver.

For each (basin, seed, ops) tuple:
  alns_only --cp-board <basin.path> --ops <ops>
            --alns-budget-ms <BUDGET_MS> --seed <seed>
  → log to output/vol-148/<ts>/<basin_tag>_s<seed>_<ops>.log

Throttles to MAX_PARALLEL concurrent jobs (CLAUDE.md mandate: 7 cores
max, leave 1 free).

Total: 18 basins × 3 seeds × 2 ops = 108 jobs.
At 2h budget × 108 jobs = 216 CPU-hr.
On 7 cores parallel: ~31 wallclock hours.

Result: each log contains "matched=N" lines + final bucas URL.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget-ms", type=int, default=7_200_000,
                    help="ALNS budget per job in ms (default 2h)")
    ap.add_argument("--max-parallel", type=int, default=7)
    ap.add_argument("--seeds", type=str, default="1,7,42")
    ap.add_argument("--ops", type=str, default="basic,basic_lkh")
    ap.add_argument("--out-dir", type=str, default=None)
    ap.add_argument("--manifest", type=str,
                    default=str(REPO / "scripts/v148_basin_sweep/manifest.json"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    manifest = json.load(open(args.manifest))
    seeds = [int(s) for s in args.seeds.split(",")]
    ops_list = args.ops.split(",")

    ts = time.strftime("%Y%m%dT%H%M%S")
    if args.out_dir:
        out_dir = Path(args.out_dir)
    else:
        out_dir = REPO / "output" / "vol-148" / ts
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[v148] out_dir={out_dir}", flush=True)

    config_log = out_dir / "config.json"
    json.dump({
        "budget_ms": args.budget_ms, "seeds": seeds, "ops": ops_list,
        "max_parallel": args.max_parallel,
        "n_basins": len(manifest),
        "n_jobs": len(manifest) * len(seeds) * len(ops_list),
    }, open(config_log, "w"), indent=2)

    jobs = []
    for entry in manifest:
        cp_tag = "_".join(str(c) for c in entry["cp"])
        score = entry["base_score"]
        for seed in seeds:
            for ops in ops_list:
                log = out_dir / f"cp{cp_tag}_s{score}_seed{seed}_{ops}.log"
                cmd = [str(REPO / "target/bench-fast/alns_only"),
                       "--cp-board", str(entry["path"]),
                       "--ops", ops,
                       "--alns-budget-ms", str(args.budget_ms),
                       "--seed", str(seed)]
                jobs.append({
                    "cp_tag": cp_tag, "base_score": score,
                    "seed": seed, "ops": ops,
                    "cmd": cmd, "log": log,
                })

    print(f"[v148] total jobs: {len(jobs)}", flush=True)
    print(f"[v148] budget per job: {args.budget_ms/1000:.0f}s = {args.budget_ms/3_600_000:.2f}h", flush=True)
    print(f"[v148] estimated wallclock: {len(jobs) * args.budget_ms / 1000 / args.max_parallel / 3600:.1f}h",
          flush=True)

    if args.dry_run:
        for j in jobs[:5]:
            print(f"  {' '.join(j['cmd'])}", flush=True)
        print(f"  ... ({len(jobs)} jobs total)", flush=True)
        return

    procs = []
    completed = []

    for j in jobs:
        f = open(j["log"], "w")
        p = subprocess.Popen(j["cmd"], stdout=f, stderr=subprocess.STDOUT, cwd=str(REPO))
        procs.append({"job": j, "p": p, "f": f, "start": time.time()})
        print(f"[launch] cp={j['cp_tag']} s{j['seed']} {j['ops']} pid={p.pid}", flush=True)

        # Throttle
        while True:
            running = [x for x in procs if x["p"].poll() is None]
            if len(running) < args.max_parallel:
                break
            time.sleep(15)

        # Reap finished
        for x in procs[:]:
            if x["p"].poll() is not None and x not in completed:
                completed.append(x)
                x["f"].close()
                elapsed = time.time() - x["start"]
                print(f"[done] cp={x['job']['cp_tag']} s{x['job']['seed']} {x['job']['ops']} "
                      f"elapsed={elapsed:.0f}s", flush=True)

    # Wait all
    print(f"\n[wait] {len(procs) - len(completed)} jobs remaining", flush=True)
    for x in procs:
        if x not in completed:
            x["p"].wait()
            x["f"].close()
            completed.append(x)
            print(f"[done] cp={x['job']['cp_tag']} s{x['job']['seed']} {x['job']['ops']}", flush=True)

    print(f"\n[v148] all {len(jobs)} jobs done. Logs in {out_dir}", flush=True)


if __name__ == "__main__":
    main()
