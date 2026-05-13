"""Vol-26 gate measurement.

Run engine on the 200 test puzzles twice:
  - BorderFirstMRV + LeastConstraining (baseline)
  - BorderFirstMRV + Learned (subprocess bridge)

Compute the three gate conditions:
  (a) Learned solves >= 95% of MRV's solved set.
  (b) Median (nodes_learned / nodes_mrv) on commonly-solved <= 0.80.
  (c) >= 1 MRV-failure solved by Learned.

The engine is invoked via a tiny Rust shim binary (`bench-eval`) that
takes JSON puzzles on stdin and writes JSON results on stdout. We can't
just import the Rust engine into Python — go through the bin.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
from pathlib import Path


def run_bench(jsonl_path: Path, mode: str, model_path: str | None) -> list[dict]:
    """Invoke ../target/release/bench-eval with the requested mode."""
    env = os.environ.copy()
    if model_path is not None:
        env["E2_LEARNED_MODEL"] = str(model_path)
    # Tell the bridge to start the Python subprocess in this dir so it
    # finds infer_bridge.py + model files.
    env["E2_BRIDGE_CWD"] = str(Path(__file__).parent.resolve())
    env["E2_BRIDGE_CMD"] = "uv run python infer_bridge.py"
    cmd = [
        "../target/release/bench-eval",
        "--mode", mode,
        "--in", str(jsonl_path),
    ]
    print(f"+ {' '.join(cmd)}  (mode={mode})", flush=True)
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"bench-eval failed (mode={mode})")
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", default="data/test_6x6_5c.jsonl")
    ap.add_argument("--model", default="runs/v1/model.pt")
    ap.add_argument("--out", default="runs/v1/gate.json")
    args = ap.parse_args()

    test_path = Path(args.test)
    model_path = Path(args.model)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"baseline run -> {test_path}")
    baseline = run_bench(test_path, mode="mrv", model_path=None)
    print(f"  {len(baseline)} puzzles, solved={sum(r['solved'] for r in baseline)}")

    print(f"learned run -> {test_path}")
    learned = run_bench(test_path, mode="learned", model_path=model_path)
    print(f"  {len(learned)} puzzles, solved={sum(r['solved'] for r in learned)}")

    by_seed_b = {r["seed"]: r for r in baseline}
    by_seed_l = {r["seed"]: r for r in learned}
    seeds = sorted(set(by_seed_b) & set(by_seed_l))

    # Condition (a)
    mrv_solved = {s for s in seeds if by_seed_b[s]["solved"]}
    lrn_solved = {s for s in seeds if by_seed_l[s]["solved"]}
    cov = len(mrv_solved & lrn_solved) / max(1, len(mrv_solved))
    cond_a = cov >= 0.95

    # Condition (b)
    common = sorted(mrv_solved & lrn_solved)
    ratios = []
    for s in common:
        b = by_seed_b[s]["nodes"]
        l = by_seed_l[s]["nodes"]
        if b > 0:
            ratios.append(l / b)
    if ratios:
        med_ratio = statistics.median(ratios)
    else:
        med_ratio = float("inf")
    cond_b = med_ratio <= 0.80

    # Condition (c)
    mrv_failed_lrn_solved = lrn_solved - mrv_solved
    cond_c = len(mrv_failed_lrn_solved) >= 1

    passed = cond_a and cond_b and cond_c

    summary = {
        "n_test": len(seeds),
        "mrv_solved": len(mrv_solved),
        "learned_solved": len(lrn_solved),
        "common_solved": len(common),
        "coverage_ratio": cov,
        "median_nodes_ratio": med_ratio,
        "mrv_failed_learned_solved": sorted(mrv_failed_lrn_solved),
        "cond_a_coverage_ge_95": cond_a,
        "cond_b_median_ratio_le_80": cond_b,
        "cond_c_mrv_fail_learned_pass": cond_c,
        "gate_passed": passed,
    }

    out_path.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print(f"\ngate: {'PASS' if passed else 'FAIL'} -> {out_path}")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
