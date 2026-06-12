#!/usr/bin/env python3
"""ACTUARY (vol-216 invention) — Verhaard-class markov schedule optimizer.

Model: the break-DFS walk is a branching process over depths. From
cost-split FITSTAT calibration (cloister2 fitstats TSVs, vol-216
columns y0/y1/visits_open):

    b0(d) = y0(d) / visits(d)          cost-0 (perfect) branching
    b1(d) = y1(d) / visits_open(d)     cost-1 branching when gate open

DP over states (depth d, breaks spent s) with a schedule G
(G[s] = min depth to spend break s+1, budget B = len(G)):

    V(d+1, s)   += V(d, s) * b0(d)
    V(d+1, s+1) += V(d, s) * b1(d) * [s < B and d >= G[s]]

V(dmax, s) = expected arrivals at the exact-tail frontier per epoch
root, by spent level. nodes ~ sum V (per-epoch search cost).
Objective: quality-weighted arrivals per node, sum_s V(dmax,s)*gamma^s.

Subcommands:
  fit       — read fitstats TSVs, emit b-curve TSV + diagnostics
  eval      — DP-evaluate a given schedule against fitted curves
  optimize  — simulated-annealing search over schedules
"""
import argparse
import csv
import json
import math
import random
import sys


def read_fitstats(paths):
    """sum fitstats TSVs (vol-216 format) -> dict d -> [y0,y1,starts,open]"""
    agg = {}
    for p in paths:
        for r in csv.DictReader(open(p), delimiter="\t"):
            d = int(r["depth"])
            if "starts" not in r:
                sys.exit(f"{p}: pre-vol-216 fitstats (no starts column)")
            e = agg.setdefault(d, [0] * 4)
            e[0] += int(r["y0"])
            e[1] += int(r["y1"])
            e[2] += int(r["starts"])
            e[3] += int(r["starts_open"])
    return agg


def fit_curves(agg, dmin, dmax, min_n=50):
    """b0(d) = y0/starts, b1(d) = y1/starts_open; absent where support
    is too thin"""
    b0, b1 = {}, {}
    for d in range(dmin, dmax + 1):
        e = agg.get(d)
        if not e:
            continue
        if e[2] >= min_n:
            b0[d] = e[0] / e[2]
        if e[3] >= min_n:
            b1[d] = e[1] / e[3]
    return b0, b1


def interp(curve, d, lo, hi):
    """nearest-neighbor fill inside [lo,hi]"""
    if d in curve:
        return curve[d]
    for w in range(1, hi - lo + 1):
        if d - w in curve:
            return curve[d - w]
        if d + w in curve:
            return curve[d + w]
    return 0.0


def dp_eval(b0, b1, gates, k0, dmax, budget):
    """returns (arrivals[s] at dmax, nodes) per epoch root at depth k0"""
    nb = budget + 1
    v = [0.0] * nb
    v[0] = 1.0
    nodes = 0.0
    for d in range(k0, dmax):
        nodes += sum(v)
        c0 = interp(b0, d, k0, dmax)
        c1 = interp(b1, d, k0, dmax)
        nv = [0.0] * nb
        for s in range(nb):
            if v[s] <= 0.0:
                continue
            nv[s] += v[s] * c0
            if s < budget and d >= gates[s]:
                nv[s + 1] += v[s] * c1
        v = nv
        if sum(v) < 1e-300:
            break
    return v, nodes


def objective(b0, b1, gates, k0, dmax, gamma):
    arr, nodes = dp_eval(b0, b1, gates, k0, dmax, len(gates))
    q = sum(a * gamma**s for s, a in enumerate(arr))
    return q / max(nodes, 1e-12), arr, nodes


def anneal(b0, b1, k0, dmax, budget, gamma, iters, seed, g_init=None):
    rng = random.Random(seed)
    g = sorted(g_init) if g_init else sorted(
        rng.randint(k0 + 2, dmax) for _ in range(budget))
    best_g, (best_o, _, _) = list(g), objective(b0, b1, g, k0, dmax, gamma)
    cur_o = best_o
    t0, t1 = 0.3, 0.005
    for it in range(iters):
        t = t0 * (t1 / t0) ** (it / max(iters - 1, 1))
        cand = list(g)
        i = rng.randrange(budget)
        cand[i] = min(dmax, max(k0 + 2, cand[i] + rng.choice(
            [-8, -4, -2, -1, 1, 2, 4, 8])))
        cand.sort()
        o, _, _ = objective(b0, b1, cand, k0, dmax, gamma)
        # relative acceptance on log-objective (objectives span decades)
        if o > 0 and (o >= cur_o or
                      rng.random() < math.exp((math.log(o) - math.log(max(cur_o, 1e-300))) / t)):
            g, cur_o = cand, o
            if o > best_o:
                best_g, best_o = list(cand), o
    return best_g, best_o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fit", "eval", "optimize"])
    ap.add_argument("--fitstats", nargs="+", required=True)
    ap.add_argument("--k0", type=int, required=True,
                    help="root depth (prefix pin K, or 0 from scratch)")
    ap.add_argument("--dmax", type=int, default=182,
                    help="exact-tail frontier (196 - et_k)")
    ap.add_argument("--budget", type=int, default=14)
    ap.add_argument("--gamma", type=float, default=1.0,
                    help="per-spent quality discount on arrivals")
    ap.add_argument("--gates", help="comma list, for eval / anneal init")
    ap.add_argument("--iters", type=int, default=20000)
    ap.add_argument("--seeds", type=int, default=8,
                    help="anneal restarts (best-of)")
    ap.add_argument("--min-n", type=int, default=50)
    a = ap.parse_args()

    agg = read_fitstats(a.fitstats)
    b0, b1 = fit_curves(agg, 0, a.dmax, a.min_n)

    if a.cmd == "fit":
        print("depth\tstarts\tstarts_open\tb0\tb1")
        for d in sorted(agg):
            e = agg[d]
            s0 = f"{b0[d]:.4f}" if d in b0 else "-"
            s1 = f"{b1[d]:.4f}" if d in b1 else "-"
            print(f"{d}\t{e[2]}\t{e[3]}\t{s0}\t{s1}")
        cov0 = sum(1 for d in range(a.k0, a.dmax) if d in b0)
        cov1 = sum(1 for d in range(a.k0, a.dmax) if d in b1)
        print(f"# b0 coverage {cov0}/{a.dmax-a.k0}  b1 coverage "
              f"{cov1}/{a.dmax-a.k0}", file=sys.stderr)
        # consistency: starts(d) ~ y0(d-1)+y1(d-1) (arrival identity)
        bad = 0
        for d in sorted(agg):
            if d - 1 in agg and agg[d - 1][0] + agg[d - 1][1] > 0:
                arr = agg[d - 1][0] + agg[d - 1][1]
                if agg[d][2] > 0 and not 0.5 < agg[d][2] / arr < 2.0:
                    bad += 1
        print(f"# arrival-identity violations (>2x): {bad}", file=sys.stderr)
        return

    if a.cmd == "eval":
        gates = [int(x) for x in a.gates.split(",")]
        o, arr, nodes = objective(b0, b1, sorted(gates), a.k0, a.dmax, a.gamma)
        print(json.dumps(dict(
            gates=sorted(gates), obj=o, nodes_per_epoch=nodes,
            arrivals_by_spent=[f"{x:.3e}" for x in arr],
            total_arrivals=f"{sum(arr):.3e}")))
        return

    # optimize
    g_init = [int(x) for x in a.gates.split(",")] if a.gates else None
    best = None
    for s in range(a.seeds):
        g, o = anneal(b0, b1, a.k0, a.dmax, a.budget, a.gamma,
                      a.iters, seed=1000 + s, g_init=g_init if s == 0 else None)
        if best is None or o > best[1]:
            best = (g, o)
        print(f"# restart {s}: obj {o:.3e} gates {g}", file=sys.stderr)
    o, arr, nodes = objective(b0, b1, best[0], a.k0, a.dmax, a.gamma)
    print(json.dumps(dict(
        gates=best[0], obj=o, nodes_per_epoch=nodes,
        arrivals_by_spent=[f"{x:.3e}" for x in arr],
        total_arrivals=f"{sum(arr):.3e}")))


if __name__ == "__main__":
    main()
