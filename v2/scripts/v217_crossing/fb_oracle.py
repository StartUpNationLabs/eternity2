#!/usr/bin/env python3
"""Vol-217 binding 3, component 1: FULL-BOARD band oracle (frame-free).

Generalizes the crossing oracle to the real 16x16 with all 256 pieces:
N-row break-profile transfer over a contiguous band of full-board rows
(16 columns wide), with the border ring EMERGING rather than fixed:

  - flank columns 0/15: candidates = remaining EDGE pieces oriented
    with their border side facing out (structural, not a cost term);
    row 15: bottom-edge pieces (S side = 0), corners at (15,0)/(15,15)
  - interior columns: remaining interior pieces, any rotation
  - N targets of the band's top row = exact south colors of the placed
    row above (frontier conditioning; rows above must be complete)
  - in-band cells already placed (validation mode) and clue hints are
    FORCED; unplaced hints outside the band are reserved from pools
  - S side of the bottom band row free (unknown rows below), unless
    row 15 (structural border, satisfied by candidate type)
  - ALL counted edges break-tolerant: V above-band->band (16), H per
    band row (15 each), V in-band (16 per row pair). For a 3-row band
    that is 93 edges (the 87 crossing edges + 6 flank verticals).
  - repeats-allowed everywhere (same declared relaxation as the
    crossing oracle; vol-217 sanity A/B found it benign for ranking)

State between columns: (e_row0..e_row{k-1}, b); within a column a
carried s-dimension couples vertical edges; horizontal coupling via
match/mismatch marginal contractions (exact; selftest vs brute force).

Usage:
  fb_oracle.py --selftest
  fb_oracle.py --rows R0 --k K [--truncate-rows R] [--bmax N] \
      BOARD.json [MORE.json ...]      # placements merged (prefix+frame)
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
PUZZLE = os.path.join(os.path.dirname(__file__), "..", "..", "..",
                      "data", "puzzles", "size_16_official_eternity.csv")


def build_ctx():
    pieces, hints = L.load_puzzle(PUZZLE)
    rot_all = [[L.oriented(p, r) for r in range(4)] for p in pieces]
    kind = []
    for p in pieces:
        z = sum(1 for s in p if s == 0)
        kind.append({2: "corner", 1: "edge", 0: "interior"}[z])
    hint_map = {(pos // 16, pos % 16): (pid, rot) for pos, pid, rot in hints}
    return rot_all, kind, hint_map


def cell_cands(r, c, pools, rot_all):
    out = []
    if r == 15 and c in (0, 15):
        want = (2, 3) if c == 0 else (2, 1)
        for p in pools["corner"]:
            for rt in range(4):
                o = rot_all[p][rt]
                if o[want[0]] == 0 and o[want[1]] == 0:
                    out.append((p, rt))
    elif r == 15 or c in (0, 15):
        side = 2 if r == 15 else (3 if c == 0 else 1)
        for p in pools["edge"]:
            for rt in range(4):
                if rot_all[p][rt][side] == 0:
                    out.append((p, rt))
    else:
        out = [(p, rt) for p in pools["interior"] for rt in range(4)]
    return out


def band_profile(ctx, rows, t_n, forced, pools, bmax=14, ncols=16):
    rot_all, _kind, _h = ctx
    k = len(rows)
    B = bmax + 1

    def shift_add(dst, src, c):
        if c == 0:
            dst += src
        elif c <= bmax:
            dst[..., c:] += src[..., :B - c]

    T = None
    logscale = 0.0
    for c in range(ncols):
        first_col = c == 0
        for i, r in enumerate(rows):
            last_row = i == k - 1
            f = forced.get((r, c))
            cands = [f] if f else cell_cands(r, c, pools, rot_all)
            assert cands, f"no candidates at ({r},{c})"
            g = {}
            for (p, rt) in cands:
                o = rot_all[p][rt]
                cb = 0
                kn = None
                if i == 0:
                    cb += int(o[0] != t_n[c])
                else:
                    kn = o[0]
                kw = None if first_col else o[3]
                ks = None if last_row else o[2]
                kk = (cb, kn, kw, o[1], ks)
                g[kk] = g.get(kk, 0) + 1

            out_shape = ([NC] if not last_row else []) + [NC] * k + [B]
            O = np.zeros(out_shape)
            if T is None:                      # very first cell (0-row, 0-col)
                for (cb, kn, kw, e, s), m in g.items():
                    if cb <= bmax:
                        idx = ([s] if not last_row else []) + [e] + [0] * (k - 1)
                        O[tuple(idx)][cb] += m
            elif first_col:                    # i>0: contract n via s-axis
                ei_ax = 1 + i                  # T has s axis (k>=2 mid-column)
                Ts = T.sum(axis=ei_ax)         # consume dummy e_i
                sum_s = Ts.sum(axis=0)
                Ov = np.moveaxis(O, 1 + i, 1) if not last_row \
                    else np.moveaxis(O, i, 0)
                for (cb, kn, kw, e, s), m in g.items():
                    Am = Ts[kn]
                    Ax = sum_s - Am
                    dst = Ov[s, e] if not last_row else Ov[e]
                    shift_add(dst, m * Am, cb)
                    shift_add(dst, m * Ax, cb + 1)
            else:
                s_in = T.ndim == k + 2
                ei_ax = (1 if s_in else 0) + i
                Tm = np.moveaxis(T, ei_ax, 1 if s_in else 0)
                Ov = np.moveaxis(O, 1 + i, 1) if not last_row \
                    else np.moveaxis(O, i, 0)
                if s_in:                       # contract n (s-axis) + w (e_i)
                    sum_s = Tm.sum(axis=0)
                    sum_e = Tm.sum(axis=1)
                    sum_se = sum_s.sum(axis=0)
                    for (cb, kn, kw, e, s), m in g.items():
                        Amm = Tm[kn, kw]
                        Amx = sum_e[kn] - Amm
                        Axm = sum_s[kw] - Amm
                        Axx = sum_se - sum_e[kn] - sum_s[kw] + Amm
                        dst = Ov[s, e] if not last_row else Ov[e]
                        shift_add(dst, m * Amm, cb)
                        shift_add(dst, m * (Amx + Axm), cb + 1)
                        shift_add(dst, m * Axx, cb + 2)
                else:                          # i==0: contract w only
                    sum_e = Tm.sum(axis=0)
                    for (cb, kn, kw, e, s), m in g.items():
                        Am = Tm[kw]
                        Ax = sum_e - Am
                        dst = Ov[s, e] if not last_row else Ov[e]
                        shift_add(dst, m * Am, cb)
                        shift_add(dst, m * Ax, cb + 1)
            T = O
        mx = T.max()
        if mx > 1e250:
            T /= mx
            logscale += np.log10(mx)
        assert T.ndim == k + 1, "s axis must be consumed at column end"
    counts = T.sum(axis=tuple(range(k)))
    return counts, logscale


def load_board(paths, truncate_rows=None, frame=None):
    placed = {}

    def put(r, c, cur):
        if truncate_rows is not None and r >= truncate_rows:
            return
        assert placed.get((r, c), cur) == cur, f"conflict at {(r, c)}"
        placed[(r, c)] = cur

    for path in paths:
        for e in json.load(open(path))["placement"]:
            put(e["pos"] // 16, e["pos"] % 16,
                (e["piece_id"], e["rotation"]))
    if frame:  # ring cells only (frame files are full boards)
        for e in json.load(open(frame))["placement"]:
            r, c = e["pos"] // 16, e["pos"] % 16
            if r in (0, 15) or c in (0, 15):
                put(r, c, (e["piece_id"], e["rotation"]))
    return placed


def ask(ctx, placed, rows, bmax=14):
    rot_all, kind, hint_map = ctx
    r0 = rows[0]
    for c in range(16):
        assert (r0 - 1, c) in placed, f"row {r0 - 1} incomplete at col {c}"
    t_n = [rot_all[placed[(r0 - 1, c)][0]][placed[(r0 - 1, c)][1]][2]
           for c in range(16)]
    used = {p for p, _ in placed.values()}
    assert len(used) == len(placed), "duplicate pieces"
    forced = {}
    for (r, c), pr in placed.items():
        if r in rows:
            forced[(r, c)] = pr
    for (r, c), (p, rt) in hint_map.items():
        if (r, c) in placed:
            continue
        used.add(p)                            # reserve
        if r in rows:
            forced[(r, c)] = (p, rt)
    pools = {kd: [] for kd in ("corner", "edge", "interior")}
    for p in range(256):
        if p not in used:
            pools[kind[p]].append(p)
    counts, logscale = band_profile(ctx, rows, t_n, forced, pools, bmax)
    logs = np.full(bmax + 1, -np.inf)
    nz = counts > 0
    logs[nz] = np.log10(counts[nz]) + logscale
    w = logs + np.arange(bmax + 1) * np.log10(0.3)
    soft = (w.max() + np.log10(np.sum(10 ** (w - w.max())))
            if np.isfinite(w.max()) else -np.inf)
    bmin = int(np.argmax(nz)) if nz.any() else -1
    return dict(soft=soft, bmin=bmin, logs=logs,
                n_int=len(pools["interior"]), n_edge=len(pools["edge"]),
                n_corner=len(pools["corner"]))


# ---------------- exact brute-force self-test ----------------

def selftest():
    """Columns 0-1 of a 3-row band (12,13,14): flank-W edge pieces at
    col 0, interior at col 1; exact DP vs exhaustive enumeration.
    Exercises: border-candidate generation, structural W side, n/w/s
    couplings, forced cell, cost shifts."""
    ctx = build_ctx()
    rot_all, kind, _ = ctx
    edges = [p for p in range(256) if kind[p] == "edge"][:3]
    inter = [p for p in range(256) if kind[p] == "interior"][:3]
    pools = {"corner": [], "edge": edges, "interior": inter}
    forced = {(13, 1): (inter[0], 2)}
    t_n = [4, 7] + [1] * 14
    bmax = 14
    B = bmax + 1

    cnt, lsc = band_profile(ctx, (12, 13, 14), t_n, forced, pools,
                            bmax, ncols=2)
    counts = cnt * 10 ** lsc

    opts_c0 = {r: cell_cands(r, 0, pools, rot_all) for r in (12, 13, 14)}
    opts_c1 = {12: [(p, rt) for p in inter for rt in range(4)],
               13: [forced[(13, 1)]],
               14: [(p, rt) for p in inter for rt in range(4)]}
    bf = np.zeros(B)
    oe = lambda pr: rot_all[pr[0]][pr[1]]
    for a in opts_c0[12]:
        for b_ in opts_c0[13]:
            for cc in opts_c0[14]:
                A, Bo, C = oe(a), oe(b_), oe(cc)
                base = ((A[0] != t_n[0]) + (A[2] != Bo[0])
                        + (Bo[2] != C[0]))
                for d in opts_c1[12]:
                    D = oe(d)
                    cd = base + (D[0] != t_n[1]) + (A[1] != D[3])
                    for e in opts_c1[13]:
                        E = oe(e)
                        ce = cd + (D[2] != E[0]) + (Bo[1] != E[3])
                        for f in opts_c1[14]:
                            F = oe(f)
                            cf = ce + (E[2] != F[0]) + (C[1] != F[3])
                            if cf <= bmax:
                                bf[cf] += 1
    ok = np.allclose(counts, bf, rtol=0, atol=1e-6)
    print("selftest", "PASS" if ok else "FAIL")
    print("dp:", counts.astype(int))
    print("bf:", bf.astype(int))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--rows", type=int)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--truncate-rows", type=int, default=None)
    ap.add_argument("--bmax", type=int, default=14)
    ap.add_argument("--frame", default=None,
                    help="take RING cells only from this board file")
    ap.add_argument("boards", nargs="*")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    ctx = build_ctx()
    placed = load_board(a.boards, a.truncate_rows, a.frame)
    t0 = time.time()
    r = ask(ctx, placed, tuple(range(a.rows, a.rows + a.k)), a.bmax)
    ms = (time.time() - t0) * 1000
    tag = "+".join(os.path.basename(b)[:-5] for b in a.boards)
    lb = r["logs"][r["bmin"]] if r["bmin"] >= 0 else float("-inf")
    print("tag\trows\tsoft_g03\tbmin\tlog_at_bmin\tpool_i/e/c\tms")
    print(f"{tag}\t{a.rows}..{a.rows + a.k - 1}\t{r['soft']:.4f}\t{r['bmin']}"
          f"\t{lb:.3f}\t{r['n_int']}/{r['n_edge']}/{r['n_corner']}\t{ms:.0f}")


if __name__ == "__main__":
    main()
