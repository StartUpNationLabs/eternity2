#!/usr/bin/env python3
"""ACTUARY (vol-216 invention) — Verhaard-class markov schedule optimizer.

Model: the break-DFS walk is a branching process over STATES (depth d,
breaks spent s) — the same state space Verhaard's optimizer used. From
(d, s)-conditional FITSTAT calibration (cloister2 fitstats2 TSVs):

    b0(d,s) = y0(d,s) / starts(d,s)        cost-0 branching
    b1(d,s) = y1(d,s) / starts_open(d,s)   cost-1 branching, gate open

DP for a candidate schedule G (G[s] = min depth to spend break s+1):

    V(d+1, s)   += V(d, s) * b0(d, s)
    V(d+1, s+1) += V(d, s) * b1(d, s) * [s < B and d >= G[s]]

V(dmax, s) = expected arrivals at the exact-tail frontier per epoch
root, by spent. nodes ~ sum V. Objective: gamma^s-weighted arrivals
per node.

Depth-marginal rates telescope into an identity (they reproduce the
calibration run and carry NO schedule signal — vol-216 measurement:
the depth-only DP overestimated arrivals 2.3e5x). The (d, s) split is
what transfers across schedules. Cells the calibration never visited
fall back to depth-marginals; the DP reports the V-mass fraction that
flowed through MEASURED cells (coverage) — candidates are only
trusted at coverage >= ~0.8, and the loop is iterative: race the
chosen schedule, pool its FITSTAT, refit.

Subcommands: fit | eval | optimize  (--fitstats takes fitstats2 TSVs)
"""
import argparse
import csv
import json
import math
import random
import sys


def read_fitstats2(paths):
    """sum fitstats2 TSVs -> dict (d, s) -> [starts, open, y0, y1, y2]"""
    agg = {}
    for p in paths:
        for r in csv.DictReader(open(p), delimiter="\t"):
            if "spent" not in r:
                sys.exit(f"{p}: not a fitstats2 TSV (no spent column)")
            key = (int(r["depth"]), int(r["spent"]))
            e = agg.setdefault(key, [0] * 5)
            e[0] += int(r["starts"])
            e[1] += int(r["starts_open"])
            e[2] += int(r["y0"])
            e[3] += int(r["y1"])
            e[4] += int(r.get("y2", 0))
    return agg


class Curves:
    """Per-(d,s) rates with LANE-COHERENT fallback. Depth-marginal
    fallback is forbidden: it mixes spent-lanes and hands healthy
    branching to lanes whose true dynamics are death (measured vol-216:
    marginal fallback inflated self-consistency 410k/epoch vs 8.5
    measured; lane-coherent closes it). Unvisited cells fall back to
    the nearest measured depth in the SAME lane, then to a MORE-spent
    lane at the same depth (damage-monotone, conservative), else 0."""

    def __init__(self, agg, min_n=10):
        self.b0 = {}   # (d,s) -> rate
        self.b1 = {}
        self.b2 = {}   # forced hint cells paying 2 (flow exactness)
        for (d, s), e in agg.items():
            if e[0] >= min_n:
                self.b0[(d, s)] = e[2] / e[0]
                self.b2[(d, s)] = e[4] / e[0]
            if e[1] >= min_n:
                self.b1[(d, s)] = e[3] / e[1]
            elif e[0] >= min_n and e[1] == 0:
                # forced (hint) cell: break placements are per-arrival,
                # not per-open-enumeration (open counted at free cells
                # only). Without this, lane fallback hands hint cells
                # the free-cell b1 ~ 20 (x400 over two hint cells).
                self.b1[(d, s)] = e[3] / e[0]

    @staticmethod
    def _lane(tbl, d, s, dwin=10, smax=31):
        for w in range(1, dwin + 1):
            if (d - w, s) in tbl:
                return tbl[(d - w, s)]
            if (d + w, s) in tbl:
                return tbl[(d + w, s)]
        for s2 in range(s + 1, smax):
            if (d, s2) in tbl:
                return tbl[(d, s2)]
        return 0.0

    def rate0(self, d, s):
        """(rate, measured?) — measured means the exact (d,s) cell"""
        if (d, s) in self.b0:
            return self.b0[(d, s)], True
        return self._lane(self.b0, d, s), False

    def rate1(self, d, s):
        if (d, s) in self.b1:
            return self.b1[(d, s)], True
        return self._lane(self.b1, d, s), False

    def rate2(self, d, s):
        """forced cost-2; no fallback (hint-cell specific)"""
        return self.b2.get((d, s), 0.0)


def dp_eval(cv, gates, k0, dmax, budget):
    """-> (arrivals[s], nodes, coverage) per epoch root at depth k0.
    coverage = V-mass-weighted fraction of transitions through measured
    (d,s) cells."""
    nb = budget + 1
    v = [0.0] * nb
    v[0] = 1.0
    nodes = 0.0
    mass_meas, mass_tot = 0.0, 0.0
    for d in range(k0, dmax):
        nodes += sum(v)
        nv = [0.0] * nb
        for s in range(nb):
            if v[s] <= 0.0:
                continue
            r0, ok0 = cv.rate0(d, s)
            nv[s] += v[s] * r0
            mass_tot += v[s]
            if ok0:
                mass_meas += v[s]
            if s < budget and d >= gates[s]:
                r1, ok1 = cv.rate1(d, s)
                nv[s + 1] += v[s] * r1
                if not ok1:
                    mass_meas -= 0.5 * v[s]  # penalize unmeasured break cell
            if s + 1 < budget and d >= gates[s + 1]:
                nv[s + 2] += v[s] * cv.rate2(d, s)
        v = nv
        if sum(v) < 1e-300:
            break
    cov = mass_meas / mass_tot if mass_tot > 0 else 0.0
    return v, nodes, cov


def objective(cv, gates, k0, dmax, gamma):
    arr, nodes, cov = dp_eval(cv, gates, k0, dmax, len(gates))
    q = sum(a * gamma**s for s, a in enumerate(arr))
    return q / max(nodes, 1e-12), arr, nodes, cov


def anneal(cv, k0, dmax, budget, gamma, iters, seed, g_init=None,
           min_cov=0.8):
    rng = random.Random(seed)
    g = sorted(g_init) if g_init else sorted(
        rng.randint(k0 + 2, dmax) for _ in range(budget))
    o, _, _, cov = objective(cv, g, k0, dmax, gamma)
    best_g, best_o = list(g), (o if cov >= min_cov else 0.0)
    cur_o = max(o, 1e-300)
    t0, t1 = 0.3, 0.005
    for it in range(iters):
        t = t0 * (t1 / t0) ** (it / max(iters - 1, 1))
        cand = list(g)
        i = rng.randrange(budget)
        cand[i] = min(dmax, max(k0 + 2, cand[i] + rng.choice(
            [-8, -4, -2, -1, 1, 2, 4, 8])))
        cand.sort()
        o, _, _, cov = objective(cv, cand, k0, dmax, gamma)
        if cov < min_cov:
            continue
        if o >= cur_o or rng.random() < math.exp(
                (math.log(max(o, 1e-300)) - math.log(cur_o)) / t):
            g, cur_o = cand, max(o, 1e-300)
            if o > best_o:
                best_g, best_o = list(cand), o
    return best_g, best_o


def report(cv, gates, k0, dmax, gamma):
    o, arr, nodes, cov = objective(cv, gates, k0, dmax, gamma)
    return dict(
        gates=sorted(gates), obj=o, nodes_per_epoch=nodes, coverage=cov,
        arrivals_by_spent=[f"{x:.3e}" for x in arr],
        total_arrivals=f"{sum(arr):.4f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fit", "eval", "optimize"])
    ap.add_argument("--fitstats", nargs="+", required=True,
                    help="fitstats2 TSVs (pool multiple calibration runs)")
    ap.add_argument("--k0", type=int, required=True)
    ap.add_argument("--dmax", type=int, default=182)
    ap.add_argument("--budget", type=int, default=14)
    ap.add_argument("--gamma", type=float, default=1.0)
    ap.add_argument("--gates", help="comma list, for eval / anneal init")
    ap.add_argument("--iters", type=int, default=20000)
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--min-n", type=int, default=10)
    ap.add_argument("--min-cov", type=float, default=0.8)
    a = ap.parse_args()

    agg = read_fitstats2(a.fitstats)
    cv = Curves(agg, a.min_n)

    if a.cmd == "fit":
        print("d\ts\tstarts\topen\tb0\tb1")
        for (d, s) in sorted(agg):
            e = agg[(d, s)]
            r0 = f"{cv.b0[(d,s)]:.4f}" if (d, s) in cv.b0 else "-"
            r1 = f"{cv.b1[(d,s)]:.4f}" if (d, s) in cv.b1 else "-"
            print(f"{d}\t{s}\t{e[0]}\t{e[1]}\t{r0}\t{r1}")
        print(f"# measured cells: b0 {len(cv.b0)} b1 {len(cv.b1)}",
              file=sys.stderr)
        return

    if a.cmd == "eval":
        gates = [int(x) for x in a.gates.split(",")]
        print(json.dumps(report(cv, gates, a.k0, a.dmax, a.gamma)))
        return

    g_init = [int(x) for x in a.gates.split(",")] if a.gates else None
    best = None
    for s in range(a.seeds):
        g, o = anneal(cv, a.k0, a.dmax, a.budget, a.gamma, a.iters,
                      seed=1000 + s, g_init=g_init if s == 0 else None,
                      min_cov=a.min_cov)
        if best is None or o > best[1]:
            best = (g, o)
        print(f"# restart {s}: obj {o:.3e} gates {g}", file=sys.stderr)
    print(json.dumps(report(cv, best[0], a.k0, a.dmax, a.gamma)))


if __name__ == "__main__":
    main()
