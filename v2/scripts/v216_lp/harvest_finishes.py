#!/usr/bin/env python3
"""Vol-216 binding 2: harvest (prefix -> measured finish) labels from the
vol-214/215 LADDER trees.

A label row is one (prefix file, budget class) with the totals of every
seed raced from that pinned prefix. Budget classes: r2 (30 s), r3/final
(>= 300 s), l3 (600 s wave-3), fitsig (60 s vol-215 signature runs),
incumbent (>= 600 s vol-214/215 controls on d146-seed63).

Usage: python3 scripts/v216_lp/harvest_finishes.py > labels.tsv
"""
import csv
import glob
import json
import os
import re
import sys

V2 = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(V2)

# tag -> canonical prefix file (first occurrence wins; identical tags in
# later runs are re-banked copies of the same walk only if content-equal,
# so keep (tag, sha) pairs)
def prefix_index():
    idx = {}
    for pf in glob.glob("output/vol-214/ladder*_*/cloister2_dfs_*/prefix_d*.json") + \
              glob.glob("output/vol-214/climb_*/round*/cloister2_dfs_*/prefix_d*.json") + \
              glob.glob("output/vol-214/wave3_*/**/prefix_d*.json", recursive=True):
        tag = os.path.basename(pf)[:-5]
        idx.setdefault(tag, pf)
    return idx

def totals_of(run_glob):
    """all (seed,total,breaks) rows under run dirs matching glob"""
    out = []
    for d in glob.glob(run_glob):
        st = os.path.join(d, "summary.tsv")
        if not os.path.exists(st):
            continue
        for r in csv.DictReader(open(st), delimiter="\t"):
            if r["breaks"] == "-":
                continue
            out.append((int(r["seed"]), int(r["total"]), int(r["breaks"]),
                        int(r["ii"]), int(r["ib"])))
    return out

def emit(rows, label_budget, tag, pf, root):
    if not rows:
        return
    ts = sorted(t for _, t, *_ in rows)
    m = re.match(r"prefix_d(\d+)_(.+)_seed(\d+)", tag)
    depth, frame, pseed = m.group(1), m.group(2), m.group(3)
    print("\t".join([
        tag, pf or "?", frame, depth, pseed, label_budget, str(len(ts)),
        str(ts[0]), str(ts[len(ts) // 2]), str(ts[-1]), root,
    ]))

idx = prefix_index()
print("\t".join(["tag", "prefix_file", "frame", "depth", "probe_seed",
                 "budget", "n", "min", "med", "max", "src_root"]))

seen = set()
for root in sorted(glob.glob("output/vol-214/ladder*_*") +
                   glob.glob("output/vol-214/wave3_*")):
    for rd in sorted(glob.glob(os.path.join(root, "r2_prefix_*")) +
                     glob.glob(os.path.join(root, "r3_prefix_*")) +
                     glob.glob(os.path.join(root, "l3_prefix_*"))):
        base = os.path.basename(rd)
        kind, tag = base.split("_", 1)
        rows = totals_of(os.path.join(rd, "cloister2_dfs_*"))
        budget = {"r2": "30s", "r3": "300s", "l3": "600s"}[kind]
        key = (tag, budget, root)
        if key in seen:
            continue
        seen.add(key)
        emit(rows, budget, tag, idx.get(tag, ""), root)

# vol-215 fitsig (60 s) + incumbent controls (d146-seed63)
for d, tag in [("output/vol-215/fitsig__seed24", "prefix_d146_strict460a_seed24"),
               ("output/vol-215/fitsig__seed36", "prefix_d146_strict460a_seed36"),
               ("output/vol-215/fitsig__seed63", "prefix_d146_strict460a_seed63"),
               ("output/vol-215/fitsig_eed1053", "prefix_d146_strict460a_seed1053")]:
    emit(totals_of(os.path.join(d, "cloister2_dfs_*")), "60s", tag,
         idx.get(tag, ""), d)

for d, budget in [("output/vol-214/ladder4_*/incumbent", "600s"),
                  ("output/vol-215/incumbent3600", "3600s"),
                  ("output/vol-215/incumbent6h", "21600s")]:
    emit(totals_of(os.path.join(d, "cloister2_dfs_*")), budget,
         "prefix_d146_strict460a_seed63",
         idx.get("prefix_d146_strict460a_seed63", ""), d)
