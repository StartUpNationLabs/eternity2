#!/usr/bin/env python3
"""LADDER phase-1 ranking: pick top-K deep, mutually-diverse prefixes.

Usage: ladder_rank.py <probe_run_dir> <k> <max_overlap>
Prints one line per selected prefix: <path> <pin_depth>
pin_depth = banked depth - 15 (breathing room for the re-search).
"""
import json
import sys
from glob import glob

run_dir, k, max_ov = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
cands = []
for f in glob(f"{run_dir}/prefix_d*.json"):
    pl = json.load(open(f))["placement"]
    cells = {e["pos"]: (e["piece_id"], e["rotation"]) for e in pl}
    cands.append((len(cells), f, cells))
cands.sort(key=lambda t: -t[0])

kept = []
for depth, f, cells in cands:
    if len(kept) >= k:
        break
    ok = True
    for _, _, kc in kept:
        common = sum(1 for p, v in cells.items() if kc.get(p) == v)
        if common / min(len(cells), len(kc)) > max_ov:
            ok = False
            break
    if ok:
        kept.append((depth, f, cells))

for depth, f, _ in kept:
    print(f, max(20, depth - 15))
