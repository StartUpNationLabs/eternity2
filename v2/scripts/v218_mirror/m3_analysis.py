#!/usr/bin/env python3
"""Vol-218 M3 analysis: per-entry exactness/coverage + join-size
scaling from m23_<seed>.tsv. Reports per the prereg decision rule:
saw-vs-bb decision rates, agreement on mutually decided, wall-clock
ratio, bracket widths, join statistics distributions."""
import glob
import statistics as st
import sys

RUN = sys.argv[1] if len(sys.argv) > 1 else "output/vol-218/m_run_20260612T140054"

rows = []
for f in sorted(glob.glob(f"{RUN}/m23_*.tsv")):
    hdr = None
    for line in open(f):
        p = line.strip().split("\t")
        if p[0] == "seed":
            hdr = p
            continue
        if not hdr or len(p) != len(hdr):
            continue
        rows.append(dict(zip(hdr, p)))

n = len(rows)
if n == 0:
    print("no rows yet")
    sys.exit(0)

saw_dec = [r for r in rows if int(r["saw_best"]) >= 0]
bb_dec = [r for r in rows if int(r["bb_best"]) >= 0]
both = [r for r in rows if int(r["saw_best"]) >= 0 and int(r["bb_best"]) >= 0]
agree = [r for r in both if r["saw_best"] == r["bb_best"]]
print(f"entries: {n}")
print(f"saw decided: {len(saw_dec)} ({100*len(saw_dec)/n:.0f}%) | bb decided: {len(bb_dec)} ({100*len(bb_dec)/n:.0f}%)")
print(f"mutually decided: {len(both)} | agree: {len(agree)} | DISAGREE: {len(both)-len(agree)}")

floors = [int(r["floor"]) for r in rows]
lbs = [int(r["saw_lb"]) for r in rows]
ubs = [int(r["saw_ub"]) for r in rows if int(r["saw_ub"]) >= 0]
print(f"\nfloors: {min(floors)}/{st.median(floors)}/{max(floors)}")
print(f"certified LB: {min(lbs)}/{st.median(lbs)}/{max(lbs)} | LB-floor lift: med {st.median([int(r['saw_lb'])-int(r['floor']) for r in rows])}")
if ubs:
    print(f"saw UB (where found): {min(ubs)}/{st.median(ubs)}/{max(ubs)} (n={len(ubs)})")

def med(xs):
    return st.median(xs) if xs else None

print("\njoin-size stats (per ID run, final budget):")
for col in ("top_raw", "bottom_raw", "top_keys", "bottom_keys", "mask_groups", "join_pairs"):
    vals = [int(r[col]) for r in rows]
    print(f"  {col}: {min(vals)}/{med(vals):.0f}/{max(vals)}")

saw_ms = [int(r["saw_ms"]) for r in rows]
bb_ms = [int(r["bb_ms"]) for r in rows]
print(f"\nwall-clock ms: saw {min(saw_ms)}/{med(saw_ms):.0f}/{max(saw_ms)} | bb {min(bb_ms)}/{med(bb_ms):.0f}/{max(bb_ms)}")
if both:
    ratios = [int(r["saw_ms"]) / max(1, int(r["bb_ms"])) for r in both]
    print(f"saw/bb wall ratio on mutually decided: med {med(ratios):.1f}")

# gap at b* where exact counts landed
g = [r for r in rows if int(r["exact_at_bstar"]) > 0 and int(r["exact_capped"]) == 0]
if g:
    import math
    gaps = [math.log10(float(r["relax_at_bstar"]) / int(r["exact_at_bstar"])) for r in g]
    print(f"\ngap@b* (n={len(g)}): log10 {min(gaps):.2f}/{med(gaps):.2f}/{max(gaps):.2f}")
