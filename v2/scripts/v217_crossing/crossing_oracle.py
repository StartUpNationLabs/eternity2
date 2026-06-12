#!/usr/bin/env python3
"""Vol-217 CROSSING ORACLE (binding 1, named invention).

Break-profile transfer DP over interior rows 10-12 — the wall-crossing
region where vol-216 localized the entire 452->460 gap — conditioned on
the prefix's ACTUAL placed frontier:

  - N targets of row 10 = exact south colors of placed row 9
    (no free-N relaxation: sharper than the band oracle by construction)
  - cells already placed in rows 10-12 (partial row 10 etc.) are FORCED
  - clue hints at interior (12,1), (12,12) pinned
  - S side of row 12 free (row 13 unknown at prefix time; uniform)
  - W/E rim targets from the prefix's frame
  - ALL counted edges break-tolerant.

Counted edge set (exactly the 87 "crossing" edges of attribution.py):
V full-rows 10-11, 11-12, 12-13 (14 each) + H full-rows 11, 12, 13
(15 each incl. the two rim H edges per row).

State: V[e10, e11, e12, b] between columns; within a column the three
cells are placed top->mid->bot with carried s-dimension for vertical
coupling and match/mismatch marginal contractions for horizontal
coupling. Repeats-allowed everywhere (declared relaxation: unlike the
2-row band oracle, within-column distinctness is NOT enforced — see
preregistration sanity A/B).

Pre-registered (output/vol-217/crossing_oracle_20260612T095808/
preregistration.txt, BEFORE any score): floor = bmin; soft =
log10 sum_b N_b gamma^b, gamma=0.3; witness-separation primary gate.

Usage:
  crossing_oracle.py --frame F.json [--truncate 146] PREFIX.json...
  crossing_oracle.py --selftest
"""
import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "v216_lp"))
import lp_prefix_score as L

NC = 23
BMAX = 14
B = BMAX + 1
GAMMA = 0.3
N = 14
ROW_T, ROW_M, ROW_B = 10, 11, 12

PUZZLE = os.path.join(os.path.dirname(__file__), "..", "..", "..",
                      "data", "puzzles", "size_16_official_eternity.csv")


def build_ctx():
    pieces, hints = L.load_puzzle(PUZZLE)
    g2l, _, rot_edges = L.build_interior(pieces)
    ih = {}
    for pos, pid, rot in hints:
        r, c = pos // 16, pos % 16
        ih[(r - 1) * N + (c - 1)] = (g2l[pid], rot)
    return pieces, g2l, rot_edges, ih


def shift_add(dst, src, c):
    if c == 0:
        dst += src
    elif c <= BMAX:
        dst[..., c:] += src[..., :B - c]


def crossing_profile(rot_edges, rim, pool, forced, t_n, ncols=N):
    """forced: {(row, col): (lp, rot)}; t_n[col] = exact N target of the
    row-10 cell. Returns (counts[b], log10_scale)."""
    pool_or = [(p, r) for p in pool for r in range(4)]
    V = None
    logscale = 0.0
    for col in range(ncols):
        last = col == ncols - 1

        def cands(row):
            f = forced.get((row, col))
            return [f] if f is not None else pool_or

        # ---- TOP (row 10): north = exact target, or (for d139-class
        # prefixes) a marginalized pre-cell: t_n[col] is a list of
        # (pre_cost, south, count) over candidates for the missing
        # row-9 cell, whose own 3 edge costs ride along in b ----
        g = {}
        rimt = rim.get(ROW_T * N + col, [None] * 4)
        tn = t_n[col]
        tn_groups = tn if isinstance(tn, list) else [(0, tn, 1)]
        for (p, r) in cands(ROW_T):
            o = rot_edges[p][r]
            cb0 = 0
            if last and rimt[1] is not None and o[1] != rimt[1]:
                cb0 += 1
            if col == 0 and rimt[3] is not None and o[3] != rimt[3]:
                cb0 += 1
            for (pc, s9, mult) in tn_groups:
                cb = cb0 + pc + int(o[0] != s9)
                if col == 0:
                    k = (cb, o[1], o[2])
                else:
                    k = (cb, o[3], o[1], o[2])
                g[k] = g.get(k, 0) + mult
        W1 = np.zeros((NC, NC, NC, NC, B))  # (s10, e10', e11, e12, b)
        if col == 0:
            for (cb, e, s), m in g.items():
                if cb <= BMAX:
                    W1[s, e, 0, 0, cb] += m
        else:
            S0 = V.sum(axis=0)
            for (cb, w, e, s), m in g.items():
                Am = V[w]
                shift_add(W1[s, e], m * Am, cb)
                shift_add(W1[s, e], m * (S0 - Am), cb + 1)

        # ---- MID (row 11): north = carried s10 ----
        g = {}
        rimt = rim.get(ROW_M * N + col, [None] * 4)
        for (p, r) in cands(ROW_M):
            o = rot_edges[p][r]
            cb = 0
            if last and rimt[1] is not None and o[1] != rimt[1]:
                cb += 1
            if col == 0:
                if rimt[3] is not None and o[3] != rimt[3]:
                    cb += 1
                k = (cb, o[0], o[1], o[2])
            else:
                k = (cb, o[0], o[3], o[1], o[2])
            g[k] = g.get(k, 0) + 1
        W2 = np.zeros((NC, NC, NC, NC, B))  # (s11, e10', e11', e12, b)
        SM = W1.sum(axis=2)                  # (s10, e10', e12, b)
        if col == 0:
            S02 = SM.sum(axis=0)
            for (cb, n, e, s), m in g.items():
                Am = SM[n]
                shift_add(W2[s, :, e], m * Am, cb)
                shift_add(W2[s, :, e], m * (S02 - Am), cb + 1)
        else:
            S0 = W1.sum(axis=0)              # (e10', e11, e12, b)
            S02 = SM.sum(axis=0)             # (e10', e12, b)
            for (cb, n, w, e, s), m in g.items():
                Amm = W1[n][:, w]
                Amx = SM[n] - Amm
                Axm = S0[:, w] - Amm
                Axx = S02 - SM[n] - S0[:, w] + Amm
                dst = W2[s, :, e]
                shift_add(dst, m * Amm, cb)
                shift_add(dst, m * (Amx + Axm), cb + 1)
                shift_add(dst, m * Axx, cb + 2)

        # ---- BOT (row 12): north = carried s11; S free ----
        g = {}
        rimt = rim.get(ROW_B * N + col, [None] * 4)
        for (p, r) in cands(ROW_B):
            o = rot_edges[p][r]
            cb = 0
            if last and rimt[1] is not None and o[1] != rimt[1]:
                cb += 1
            if col == 0:
                if rimt[3] is not None and o[3] != rimt[3]:
                    cb += 1
                k = (cb, o[0], o[1])
            else:
                k = (cb, o[0], o[3], o[1])
            g[k] = g.get(k, 0) + 1
        Vn = np.zeros((NC, NC, NC, B))       # (e10', e11', e12', b)
        SMb = W2.sum(axis=3)                 # (s11, e10', e11', b)
        if col == 0:
            S03 = SMb.sum(axis=0)
            for (cb, n, e), m in g.items():
                Am = SMb[n]
                shift_add(Vn[:, :, e], m * Am, cb)
                shift_add(Vn[:, :, e], m * (S03 - Am), cb + 1)
        else:
            S0b = W2.sum(axis=0)             # (e10', e11', e12, b)
            S03 = SMb.sum(axis=0)            # (e10', e11', b)
            for (cb, n, w, e), m in g.items():
                Amm = W2[n][:, :, w]
                Amx = SMb[n] - Amm
                Axm = S0b[:, :, w] - Amm
                Axx = S03 - SMb[n] - S0b[:, :, w] + Amm
                dst = Vn[:, :, e]
                shift_add(dst, m * Amm, cb)
                shift_add(dst, m * (Amx + Axm), cb + 1)
                shift_add(dst, m * Axx, cb + 2)
        V = Vn
        mx = V.max()
        if mx > 1e250:
            V /= mx
            logscale += np.log10(mx)
    return V.sum(axis=(0, 1, 2)), logscale


def load_prefix(ctx, path, truncate=None, rim=None):
    _pieces, g2l, rot_edges, ih = ctx
    pj = json.load(open(path))
    placed = {}
    for e in pj["placement"]:
        cell = L.interior_cell(e["pos"])
        if cell is None:
            continue  # ring entries (full boards in truncate mode)
        if truncate is not None and cell >= truncate:
            continue
        placed[cell] = (g2l[e["piece_id"]], e["rotation"])
    missing = [c for c in range(140) if c not in placed]
    assert missing in ([], [139]), \
        f"{path}: rows 0-9 incomplete beyond (9,13), e.g. {missing[:5]}"
    used = {lp for lp, _ in placed.values()}
    assert len(used) == len(placed), f"{path}: duplicate pieces"
    forced = {}
    for cell, (lp, rot) in placed.items():
        r, c = divmod(cell, N)
        if r in (ROW_T, ROW_M, ROW_B):
            forced[(r, c)] = (lp, rot)
    for cell, (lp, rot) in ih.items():
        if cell in placed:
            continue
        r, c = divmod(cell, N)
        assert r in (ROW_T, ROW_M, ROW_B), f"unplaced hint at row {r}"
        used.add(lp)
        forced[(r, c)] = (lp, rot)
    pool = [lp for lp in range(196) if lp not in used]
    t_n = [rot_edges[placed[9 * N + c][0]][placed[9 * N + c][1]][2]
           if 9 * N + c in placed else None for c in range(N)]
    if missing == [139]:
        # marginalized pre-cell (9,13): N/W known from placed, E from
        # rim; candidates from pool (repeats vs band relaxed, declared)
        n_t = rot_edges[placed[8 * N + 13][0]][placed[8 * N + 13][1]][2]
        w_t = rot_edges[placed[9 * N + 12][0]][placed[9 * N + 12][1]][1]
        e_t = (rim or {}).get(9 * N + 13, [None] * 4)[1]
        grp = {}
        for p in pool:
            for r in range(4):
                o = rot_edges[p][r]
                c0 = (int(o[0] != n_t) + int(o[3] != w_t)
                      + int(e_t is not None and o[1] != e_t))
                k = (c0, o[2])
                grp[k] = grp.get(k, 0) + 1
        t_n[13] = [(c0, s, m) for (c0, s), m in sorted(grp.items())]
    return placed, forced, pool, t_n


def prefix_breaks(ctx, rim, placed):
    """mismatches among placed interior cells + their frame-rim targets
    (perfect-walk check; should be 0)."""
    _pieces, _g2l, rot_edges, _ih = ctx
    bad = 0
    for cell, (lp, rot) in placed.items():
        o = rot_edges[lp][rot]
        r, c = divmod(cell, N)
        if c + 1 < N and cell + 1 in placed:
            q = placed[cell + 1]
            bad += o[1] != rot_edges[q[0]][q[1]][3]
        if r + 1 < N and cell + N in placed:
            q = placed[cell + N]
            bad += o[2] != rot_edges[q[0]][q[1]][0]
        t = rim.get(cell)
        if t:
            for s in range(4):
                if t[s] is not None and o[s] != t[s]:
                    bad += 1
    return bad


def score_prefix(ctx, rim, path, truncate=None):
    _pieces, _g2l, rot_edges, _ih = ctx
    t0 = time.time()
    placed, forced, pool, t_n = load_prefix(ctx, path, truncate, rim)
    pb = prefix_breaks(ctx, rim, placed)
    counts, logscale = crossing_profile(rot_edges, rim, pool, forced, t_n)
    logs = np.full(B, -np.inf)
    nz = counts > 0
    logs[nz] = np.log10(counts[nz]) + logscale
    w = logs + np.arange(B) * np.log10(GAMMA)
    soft = (w.max() + np.log10(np.sum(10 ** (w - w.max())))
            if np.isfinite(w.max()) else -np.inf)
    bmin = int(np.argmax(nz)) if nz.any() else -1
    return dict(soft=soft, bmin=bmin, logs=logs, n_pool=len(pool),
                n_placed=len(placed), prefix_breaks=pb,
                ms=(time.time() - t0) * 1000)


# ---------------- exact brute-force self-test ----------------

def selftest():
    """2 columns x 3 rows on a 3-piece pool with synthetic targets:
    DP profile must equal exhaustive enumeration exactly."""
    ctx = build_ctx()
    _pieces, _g2l, rot_edges, _ih = ctx
    pool = [7, 42, 105]
    forced = {(ROW_M, 1): (160, 2)}  # exercise the forced path
    t_n = [3, 8]
    rim = {ROW_T * N + 0: [None, None, None, 5],
           ROW_M * N + 0: [None, None, None, 6],
           ROW_B * N + 0: [None, None, None, 7],
           ROW_T * N + 1: [None, 9, None, None],
           ROW_M * N + 1: [None, 10, None, None],
           ROW_B * N + 1: [None, 11, None, None]}
    counts, logscale = crossing_profile(rot_edges, rim, pool, forced, t_n,
                                        ncols=2)
    dp = counts * (10 ** logscale)

    opts = [(p, r) for p in pool for r in range(4)]
    cell_opts = {}
    for row in (ROW_T, ROW_M, ROW_B):
        for col in (0, 1):
            f = forced.get((row, col))
            cell_opts[(row, col)] = [f] if f else opts
    bf = np.zeros(B)
    oe = lambda pr: rot_edges[pr[0]][pr[1]]
    for a in cell_opts[(ROW_T, 0)]:
        for b_ in cell_opts[(ROW_M, 0)]:
            for c in cell_opts[(ROW_B, 0)]:
                for d in cell_opts[(ROW_T, 1)]:
                    for e in cell_opts[(ROW_M, 1)]:
                        for f in cell_opts[(ROW_B, 1)]:
                            A, Bo, C = oe(a), oe(b_), oe(c)
                            D, E, F = oe(d), oe(e), oe(f)
                            cost = (
                                (A[0] != t_n[0]) + (D[0] != t_n[1])
                                + (A[2] != Bo[0]) + (Bo[2] != C[0])
                                + (D[2] != E[0]) + (E[2] != F[0])
                                + (A[1] != D[3]) + (Bo[1] != E[3])
                                + (C[1] != F[3])
                                + (A[3] != 5) + (Bo[3] != 6) + (C[3] != 7)
                                + (D[1] != 9) + (E[1] != 10) + (F[1] != 11))
                            if cost <= BMAX:
                                bf[cost] += 1
    ok = np.allclose(dp, bf, rtol=0, atol=1e-6)
    print("selftest", "PASS" if ok else "FAIL")
    print("dp:", dp.astype(int))
    print("bf:", bf.astype(int))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frame")
    ap.add_argument("--truncate", type=int, default=None)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("prefixes", nargs="*")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    ctx = build_ctx()
    rim = L.rim_targets_from_frame(a.frame, ctx[0])
    print("tag\tsoft_g03\tbmin\tlog_at_bmin\tlog_bmin1\tn_pool"
          "\tprefix_breaks\tms")
    for pf in a.prefixes:
        r = score_prefix(ctx, rim, pf, a.truncate)
        lb = r["logs"][r["bmin"]] if r["bmin"] >= 0 else float("-inf")
        lb1 = (r["logs"][r["bmin"] + 1]
               if 0 <= r["bmin"] < BMAX else float("-inf"))
        tag = os.path.basename(pf)[:-5]
        print(f"{tag}\t{r['soft']:.4f}\t{r['bmin']}\t{lb:.3f}\t{lb1:.3f}"
              f"\t{r['n_pool']}\t{r['prefix_breaks']}\t{r['ms']:.0f}")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
