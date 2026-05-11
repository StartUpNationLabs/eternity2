#!/usr/bin/env python3
"""Load a WCNF (new format) produced by sat_e2 and run RC2 MaxSAT.

Reports: validity of the encoding (does pysat parse it?), optimum
upper bound discovered within a time budget, and the model count.

Usage:
    python3 run_maxsat.py <wcnf_path> [--budget-s 600] [--solver g3]
"""
import argparse
import signal
import sys
import time
from pathlib import Path


def parse_wcnf_new(path):
    """Parse 'new' WCNF format: lines starting with 'h ' are hard,
    lines starting with a positive integer are soft (the integer is
    the weight). Lines starting with 'c ' are comments."""
    hard = []
    soft = []
    weights = []
    n_vars = 0
    with open(path, "r") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("c "):
                continue
            parts = line.split()
            if parts[-1] != "0":
                # malformed — skip but warn
                continue
            lits = parts[:-1]
            if lits and lits[0] == "h":
                clause = [int(x) for x in lits[1:]]
                hard.append(clause)
                if clause:
                    for l in clause:
                        v = abs(l)
                        if v > n_vars:
                            n_vars = v
            else:
                # soft: first token is weight (integer), rest are literals
                weight = int(lits[0])
                clause = [int(x) for x in lits[1:]]
                soft.append(clause)
                weights.append(weight)
                for l in clause:
                    v = abs(l)
                    if v > n_vars:
                        n_vars = v
    return n_vars, hard, soft, weights


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wcnf", help="path to WCNF file")
    ap.add_argument("--budget-s", type=int, default=600)
    ap.add_argument("--solver", default="g3", help="SAT backend (g3, g4, m22, mc, cadical)")
    args = ap.parse_args()

    print(f"Loading {args.wcnf}...", flush=True)
    t0 = time.time()
    n_vars, hard, soft, weights = parse_wcnf_new(args.wcnf)
    print(f"  parsed in {time.time()-t0:.1f}s", flush=True)
    print(f"  vars: {n_vars}", flush=True)
    print(f"  hard clauses: {len(hard)}", flush=True)
    print(f"  soft clauses: {len(soft)}", flush=True)
    n_empty_hard = sum(1 for c in hard if not c)
    if n_empty_hard > 0:
        print(f"  WARN: {n_empty_hard} empty hard clauses (instance trivially UNSAT)", flush=True)

    from pysat.formula import WCNF
    from pysat.examples.rc2 import RC2

    wcnf = WCNF()
    for c in hard:
        wcnf.append(c)
    for c, w in zip(soft, weights):
        wcnf.append(c, weight=w)
    print(f"  WCNF built in {time.time()-t0:.1f}s", flush=True)

    print(f"\nRunning RC2 ({args.solver}, budget={args.budget_s}s)...", flush=True)
    t1 = time.time()

    # Use signal-based timeout to interrupt RC2 if it doesn't finish.
    def timeout_handler(signum, frame):
        raise TimeoutError(f"RC2 exceeded {args.budget_s}s budget")
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(args.budget_s)

    try:
        with RC2(wcnf, solver=args.solver) as rc2:
            model = rc2.compute()
            cost = rc2.cost
            elapsed = time.time() - t1
            n_soft = len(soft)
            satisfied = n_soft - cost
            print(f"  RC2 finished in {elapsed:.1f}s", flush=True)
            print(f"  cost (unsatisfied soft): {cost}", flush=True)
            print(f"  satisfied soft clauses: {satisfied}/{n_soft}", flush=True)
            if model is not None:
                print(f"  model length: {len(model)}", flush=True)
            else:
                print(f"  no model returned (UNSAT)", flush=True)
    except TimeoutError as e:
        print(f"  {e}", flush=True)
        sys.exit(2)
    except Exception as e:
        print(f"  RC2 error: {type(e).__name__}: {e}", flush=True)
        sys.exit(3)


if __name__ == "__main__":
    main()
