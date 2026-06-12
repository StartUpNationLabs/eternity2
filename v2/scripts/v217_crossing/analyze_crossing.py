#!/usr/bin/env python3
"""Vol-217 secondary gate: population signal of the crossing oracle vs
LP and band oracle, on the vol-216 homogeneous >=300 s label set
(budget 300s, src_root output/vol-214/ladder_*), same protocol as
vol-216: depth-residualized Spearman vs max- and median-finish.

Usage: analyze_crossing.py LP_DIR CROSSING.tsv
  LP_DIR = output/vol-216/lp_scoring_* (labels.tsv, scores.tsv,
  band_scores.tsv)
"""
import csv
import os
import sys

import numpy as np


def ranks(x):
    x = np.asarray(x, dtype=float)
    order = np.argsort(x, kind="mergesort")
    r = np.empty(len(x))
    r[order] = np.arange(len(x), dtype=float)
    # average ties
    vals, inv, cnt = np.unique(x, return_inverse=True, return_counts=True)
    csum = np.concatenate([[0], np.cumsum(cnt)])
    avg = (csum[:-1] + csum[1:] - 1) / 2.0
    return avg[inv]


def spearman(a, b):
    ra, rb = ranks(a), ranks(b)
    ra -= ra.mean()
    rb -= rb.mean()
    d = np.sqrt((ra ** 2).sum() * (rb ** 2).sum())
    return float((ra * rb).sum() / d) if d > 0 else float("nan")


def residualize(score, depth):
    A = np.vstack([np.ones_like(depth), depth]).T
    coef, *_ = np.linalg.lstsq(A, score, rcond=None)
    return score - A @ coef, coef[1]


def load_tsv(path):
    with open(path) as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def main():
    lp_dir, crossing_path = sys.argv[1], sys.argv[2]
    labels = load_tsv(os.path.join(lp_dir, "labels.tsv"))
    lp = {r["tag"]: r for r in load_tsv(os.path.join(lp_dir, "scores.tsv"))}
    band = {r["tag"]: r
            for r in load_tsv(os.path.join(lp_dir, "band_scores.tsv"))}
    cross = {r["tag"]: r for r in load_tsv(crossing_path)}

    homog = {}
    for r in labels:
        if r["budget"] != "300s":
            continue
        if "/ladder_" not in r["src_root"]:
            continue
        t = r["tag"]
        e = homog.setdefault(t, dict(max=-1, med=[], depth=int(r["depth"])))
        e["max"] = max(e["max"], int(r["max"]))
        e["med"].append(int(r["med"]))

    rows = []
    for t, e in homog.items():
        if t in lp and t in band and t in cross:
            rows.append(dict(
                tag=t, depth=e["depth"], maxf=e["max"],
                medf=float(np.median(e["med"])),
                lp=float(lp[t]["ub_total"]),
                band=float(band[t]["soft_g03"]),
                xsoft=float(cross[t]["soft_g03"]),
                xfloor=int(cross[t]["bmin"])))
    n = len(rows)
    depth = np.array([r["depth"] for r in rows], dtype=float)
    maxf = np.array([r["maxf"] for r in rows], dtype=float)
    medf = np.array([r["medf"] for r in rows], dtype=float)

    print(f"n = {n} homogeneous >=300s prefixes")
    res = {}
    for name, key in [("LP(ub_total)", "lp"), ("band(soft)", "band"),
                      ("crossing(soft)", "xsoft"),
                      ("crossing(-floor)", "xfloor")]:
        v = np.array([r[key] for r in rows], dtype=float)
        if key == "xfloor":
            v = -v
        rv, slope = residualize(v, depth)
        res[name] = rv
        print(f"{name:18s} slope={slope:+.3f}  "
              f"rho(resid,max)={spearman(rv, maxf):+.3f}  "
              f"rho(resid,med)={spearman(rv, medf):+.3f}")

    print("\ninter-instrument residual Spearman:")
    names = list(res)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            print(f"  {a} vs {b}: {spearman(res[a], res[b]):+.3f}")

    # star rank + top-quartile enrichment for crossing soft
    rv = res["crossing(soft)"]
    order = np.argsort(-rv)
    tags = [rows[i]["tag"] for i in order]
    star = "prefix_d146_strict460a_seed63"
    if star in tags:
        print(f"\nstar {star} rank by crossing resid: "
              f"#{tags.index(star) + 1}/{n}")
    q = max(1, n // 4)
    topq = set(order[:q])
    hi = {i for i in range(n) if maxf[i] >= 450}
    enr = len(topq & hi) / q
    base = len(hi) / n
    print(f"top-quartile enrichment max>=450: {len(topq & hi)}/{q} = "
          f"{enr:.2f} vs base {base:.2f} "
          f"({enr / base:.1f}x)" if base > 0 else "no max>=450 rows")

    # combined rank-sum (crossing + LP), (crossing + band)
    for other in ["LP(ub_total)", "band(soft)"]:
        comb = ranks(res["crossing(soft)"]) + ranks(res[other])
        print(f"combined crossing+{other}: rho(max)="
              f"{spearman(comb, maxf):+.3f} rho(med)="
              f"{spearman(comb, medf):+.3f}")

    out = os.path.join(os.path.dirname(crossing_path), "analysis_joined.tsv")
    with open(out, "w") as fh:
        fh.write("tag\tdepth\tmaxf\tmedf\tlp\tband\txsoft\txfloor\n")
        for r in rows:
            fh.write(f"{r['tag']}\t{r['depth']}\t{r['maxf']}\t{r['medf']}"
                     f"\t{r['lp']}\t{r['band']}\t{r['xsoft']}"
                     f"\t{r['xfloor']}\n")
    print(f"\njoined table -> {out}")


if __name__ == "__main__":
    main()
