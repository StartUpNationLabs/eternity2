#!/usr/bin/env python3
"""H4 probe (vol-217): is the band floor explained by FRONTIER BIGRAM
infeasibility? For adjacent north-target pairs (t_c, t_{c+1}) of the
band's top row, count pool pairs (u,v) with u.N=t_c, v.N=t_{c+1},
u.E=v.W, u!=v (cell-type aware). A bigram with zero serving pairs
forces a break nearby. Reports per-board: #infeasible bigrams, the
weak-pair profile, vs the known oracle floor.

Usage: bigram_probe.py --rows R --truncate-rows T [--frame F] BOARD...
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import fb_oracle as F


def probe(ctx, placed, r0):
    rot_all, kind, hint_map = ctx
    t_n = []
    for c in range(16):
        p, rt = placed[(r0 - 1, c)]
        t_n.append(rot_all[p][rt][2])
    used = {p for p, _ in placed.values()}
    for (r, c), (p, rt) in hint_map.items():
        if (r, c) not in placed:
            used.add(p)
    pools = {k: [] for k in ("corner", "edge", "interior")}
    for p in range(256):
        if p not in used:
            pools[kind[p]].append(p)
    cands = [F.cell_cands(r0, c, pools, rot_all) for c in range(16)]
    counts = []
    for c in range(15):
        us = [(p, rt) for (p, rt) in cands[c]
              if rot_all[p][rt][0] == t_n[c]]
        vs = [(p, rt) for (p, rt) in cands[c + 1]
              if rot_all[p][rt][0] == t_n[c + 1]]
        n = 0
        by_e = {}
        for (p, rt) in us:
            by_e.setdefault(rot_all[p][rt][1], []).append(p)
        for (q, qt) in vs:
            w = rot_all[q][qt][3]
            for p in by_e.get(w, []):
                if p != q:
                    n += 1
        counts.append(n)
    return t_n, counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, required=True)
    ap.add_argument("--truncate-rows", type=int, default=None)
    ap.add_argument("--frame", default=None)
    ap.add_argument("boards", nargs="+")
    a = ap.parse_args()
    ctx = F.build_ctx()
    print("tag\tinfeasible\tmin_pairs\tbigram_counts")
    for b in a.boards:
        placed = F.load_board([b], a.truncate_rows, a.frame)
        _tn, counts = probe(ctx, placed, a.rows)
        infeas = sum(1 for n in counts if n == 0)
        tag = os.path.basename(b)[:-5]
        print(f"{tag}\t{infeas}\t{min(counts)}\t{counts}")


if __name__ == "__main__":
    main()
