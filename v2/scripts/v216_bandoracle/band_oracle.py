#!/usr/bin/env python3
"""Band-4 oracle PoC (vol-216, user-directed): coupled 2-row
break-tolerant transfer profile of interior rows 12-13.

For a prefix's remaining pool, count (repeats-allowed) the fillings of
the bottom two interior rows paying exactly b total mismatches over:
row12-row13 vertical edges, W-E chains in both rows, W/E rim entries
and exits, S rim targets, with the two clue hints FORCED in-band at
(12,1) and (12,12). North side of row 12 is left free (row 11 unknown
at prefix time) — uniform relaxation across prefixes.

State: V[e12, e13, b] over columns left->right. Per column, candidate
fillings are (piece,rot) pairs (distinct, both from pool or the forced
hint at hint columns); transitions grouped into per-cost sparse
operators for numpy matmuls.

PRE-REGISTERED (before any score computed): primary score =
log sum_b N_b * gamma^b with gamma = 0.3; gate = d146-seed63 must
outrank seed24 AND seed36; secondary = Spearman vs >=300s max-finish
on the homogeneous ladder.sh set, success >= ~0.2.

Usage:
  band_oracle.py --frame F.json PREFIX.json...   -> TSV rows
"""
import argparse
import json
import os
import sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "v216_lp"))
import lp_prefix_score as L

NC = 23
BMAX = 10
GAMMA = 0.3
ROW_T, ROW_B = 12, 13   # interior rows of the band
# vol-217 sanity A/B: drop within-column distinctness (the 3-row
# crossing oracle's relaxation) to check ranking stability
NODISTINCT = os.environ.get("E2_BAND_NODISTINCT") == "1"


def build_ctx():
    pieces, hints = L.load_puzzle("../data/puzzles/size_16_official_eternity.csv")
    g2l, _, rot_edges = L.build_interior(pieces)
    ih = {}
    for pos, pid, rot in hints:
        r, c = pos // 16, pos % 16
        ih[((r - 1) * 14 + (c - 1))] = (g2l[pid], rot)
    return pieces, g2l, rot_edges, ih


def band_profile(rot_edges, rim, pool, forced_top):
    """forced_top: {col: (lp, rot)} for row-12 forced cells.
    Returns counts[b] for b in 0..BMAX (log scale tracked in .scale).
    ALL edges break-tolerant, including horizontal between-column edges
    (cost via the exact/row-marginal/total decomposition)."""
    V = None  # (NC, NC, BMAX+1): V[e12, e13, b]

    def shift_add(dst, src, c):
        if c == 0:
            dst += src
        elif c <= BMAX:
            dst[c:] += src[:BMAX + 1 - c]

    for col in range(14):
        tgt = rim.get(ROW_T * 14 + col, [None] * 4)
        tgb = rim.get(ROW_B * 14 + col, [None] * 4)
        tops = ([forced_top[col]] if col in forced_top else
                [(p, r) for p in pool for r in range(4)])
        # fillings aggregated by (cost, w12, w13, e12, e13)
        fills = {}
        for (pt, rt) in tops:
            ot = rot_edges[pt][rt]
            cost_t = 0
            if col == 0 and tgt[3] is not None and ot[3] != tgt[3]:
                cost_t += 1
            if col == 13 and tgt[1] is not None and ot[1] != tgt[1]:
                cost_t += 1
            for pb in pool:
                if pb == pt and not NODISTINCT:
                    continue
                for rb in range(4):
                    ob = rot_edges[pb][rb]
                    c = cost_t + (ot[2] != ob[0])
                    if tgb[2] is not None and ob[2] != tgb[2]:
                        c += 1
                    if col == 0 and tgb[3] is not None and ob[3] != tgb[3]:
                        c += 1
                    if col == 13 and tgb[1] is not None and ob[1] != tgb[1]:
                        c += 1
                    if c > BMAX:
                        continue
                    k = (c, ot[3], ob[3], ot[1], ob[1])
                    fills[k] = fills.get(k, 0) + 1
        if V is None:
            V = np.zeros((NC, NC, BMAX + 1))
            for (c, _w12, _w13, e12, e13), n in fills.items():
                if c <= BMAX:
                    V[e12, e13, c] += n
            continue
        # marginals for horizontal-mismatch decomposition
        marg_top = V.sum(axis=1)          # (NC, B): match w12 only
        marg_bot = V.sum(axis=0)          # (NC, B): match w13 only
        tot = V.sum(axis=(0, 1))          # (B,)
        Vn = np.zeros_like(V)
        for (c, w12, w13, e12, e13), n in fills.items():
            a = V[w12, w13]               # both horizontal edges match
            b_ = marg_top[w12] - a        # bottom-horizontal mismatch
            c_ = marg_bot[w13] - a        # top-horizontal mismatch
            d_ = tot - marg_top[w12] - marg_bot[w13] + a   # both mismatch
            dst = Vn[e12, e13]
            shift_add(dst, n * a, c)
            shift_add(dst, n * (b_ + c_), c + 1)
            shift_add(dst, n * d_, c + 2)
        V = Vn
        m = V.max()
        if m > 1e250:
            V /= m
            band_profile.scale += np.log10(m)
    return V.sum(axis=(0, 1))


def score_prefix(ctx, rim, prefix_path):
    pieces, g2l, rot_edges, ih = ctx
    pj = json.load(open(prefix_path))
    used = set()
    placed_cells = set()
    for e in pj["placement"]:
        cell = L.interior_cell(e["pos"])
        placed_cells.add(cell)
        used.add(g2l[e["piece_id"]])
    forced_top = {}
    for cell, (lp, rot) in ih.items():
        if cell in placed_cells:
            continue
        used.add(lp)  # reserved
        r, c = divmod(cell, 14)
        if r == ROW_T:
            forced_top[c] = (lp, rot)
    pool = [lp for lp in range(196) if lp not in used]
    band_profile.scale = 0.0
    counts = band_profile(rot_edges, rim, pool, forced_top)
    logs = np.full(BMAX + 1, -np.inf)
    nz = counts > 0
    logs[nz] = np.log10(counts[nz]) + band_profile.scale
    # primary (pre-registered): soft log-count, gamma=0.3
    w = logs + np.arange(BMAX + 1) * np.log10(GAMMA)
    soft = w.max() + np.log10(np.sum(10 ** (w - w.max()))) \
        if np.isfinite(w.max()) else -np.inf
    bmin = int(np.argmax(nz)) if nz.any() else -1
    return dict(soft=soft, bmin=bmin, logs=logs, n_pool=len(pool))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frame", required=True)
    ap.add_argument("prefixes", nargs="+")
    a = ap.parse_args()
    ctx = build_ctx()
    rim = L.rim_targets_from_frame(a.frame, ctx[0])
    print("tag\tsoft_g03\tbmin\tlog_at_bmin\tlog_bmin1\tn_pool")
    for pf in a.prefixes:
        tag = os.path.basename(pf)[:-5]
        r = score_prefix(ctx, rim, pf)
        lb = r["logs"][r["bmin"]] if r["bmin"] >= 0 else float("-inf")
        lb1 = r["logs"][r["bmin"] + 1] if 0 <= r["bmin"] < BMAX else float("-inf")
        print(f"{tag}\t{r['soft']:.4f}\t{r['bmin']}\t{lb:.3f}\t{lb1:.3f}"
              f"\t{r['n_pool']}")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
