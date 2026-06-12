#!/usr/bin/env python3
"""Vol-218 M4 cohort analysis (prereg P4.1-P4.3).

Reads m4_<seed>.tsv (seed idx floor greedy exact saw_ub saw_lb
saw_capped). Cohorts: top-10 by floor, top-10 by greedy label,
top-10 by saw bracket (ub, lb), random-10 (RNG seed 7, registered).
Achieved = min/median over the cohort of the best-known UB
(min(greedy, saw_ub) where >=0) and the certified LB.
P4.1: greedy cohort beats floor cohort (median achieved UB) — count
of instances. P4.2: floor ~ random (|median diff| <= 1). P4.3:
saw-bracket cohort beats greedy cohort — only claimable where
brackets separate; reported with decidability counts.
"""
import glob
import random
import statistics as st
import sys

RUN = sys.argv[1] if len(sys.argv) > 1 else "output/vol-218/m_run_20260612T140054"


def ub_of(r):
    cands = [x for x in (r["greedy"], r["saw_ub"]) if x >= 0]
    return min(cands) if cands else None


def cohort_stats(rows):
    ubs = [ub_of(r) for r in rows]
    ubs = [u for u in ubs if u is not None]
    lbs = [r["saw_lb"] for r in rows]
    return {
        "ub_min": min(ubs) if ubs else None,
        "ub_med": st.median(ubs) if ubs else None,
        "lb_med": st.median(lbs),
        "n_ub": len(ubs),
    }


p41 = p42 = p43 = 0
p43_decidable = 0
n_inst = 0
print("seed\tfloor_med\tgreedy_med\trandom_med\tsaw_med\tp41\tp42\tp43")
for f in sorted(glob.glob(f"{RUN}/m4_*.tsv")):
    rows = []
    for line in open(f):
        p = line.strip().split("\t")
        if not p or p[0] == "seed":
            continue
        rows.append({
            "idx": int(p[1]), "floor": int(p[2]), "greedy": int(p[3]),
            "exact": int(p[4]), "saw_ub": int(p[5]), "saw_lb": int(p[6]),
            "capped": int(p[7]),
        })
    if not rows:
        continue
    n_inst += 1
    seed = f.split("_")[-1].split(".")[0]
    by_floor = sorted(rows, key=lambda r: (r["floor"], r["idx"]))[:10]
    # greedy -1 (DNF) ranks WORST
    by_greedy = sorted(rows, key=lambda r: (r["greedy"] if r["greedy"] >= 0 else 10**6, r["idx"]))[:10]
    by_saw = sorted(rows, key=lambda r: (
        r["saw_ub"] if r["saw_ub"] >= 0 else 10**6, r["saw_lb"], r["idx"]))[:10]
    rng = random.Random(7)
    by_rand = rng.sample(rows, 10)

    s_floor = cohort_stats(by_floor)
    s_greedy = cohort_stats(by_greedy)
    s_saw = cohort_stats(by_saw)
    s_rand = cohort_stats(by_rand)

    ok41 = (s_greedy["ub_med"] is not None and s_floor["ub_med"] is not None
            and s_greedy["ub_med"] < s_floor["ub_med"])
    ok42 = (s_floor["ub_med"] is not None and s_rand["ub_med"] is not None
            and abs(s_floor["ub_med"] - s_rand["ub_med"]) <= 1)
    # P4.3 decidable only if saw cohort's UB median strictly below
    # greedy cohort's; equality/overlap -> not decided
    dec43 = s_saw["ub_med"] is not None and s_greedy["ub_med"] is not None
    ok43 = dec43 and s_saw["ub_med"] < s_greedy["ub_med"]
    p41 += ok41
    p42 += ok42
    p43 += ok43
    p43_decidable += dec43
    print(f"{seed}\t{s_floor['ub_med']}\t{s_greedy['ub_med']}\t{s_rand['ub_med']}\t{s_saw['ub_med']}\t{int(ok41)}\t{int(ok42)}\t{int(ok43)}")

print(f"\nP4.1 greedy<floor: {p41}/{n_inst} (bar: >=6/8)")
print(f"P4.2 |floor-random|<=1: {p42}/{n_inst} (bar: >=5/8)")
print(f"P4.3 saw<greedy: {p43}/{n_inst} decided {p43_decidable} (bar: >=6/8; only claimable where decided)")
