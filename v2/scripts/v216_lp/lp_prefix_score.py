#!/usr/bin/env python3
"""Vol-216 binding 2: assignment-LP prefix scoring.

For a pinned perfect prefix on a bordered+hinted 14x14 interior, solve
the LP relaxation of the max-matched-edges completion over the remaining
(cells x pieces):

  max  sum_fixed-side matches + sum_internal-edge matches
  s.t. each empty cell gets 1 fractional piece,
       each remaining piece is used exactly once,
       internal-edge match y[e,k] <= color-k mass on either endpoint.

The LP optimum is a SOUND UPPER BOUND on II+IB achievable from the
prefix (relaxation of the integer completion). The vol-216 question is
whether this *global* lens ranks prefixes the triple-null's local lenses
could not (prediction gate: d146-seed63 must outrank d146-seed24/36).

Usage:
  lp_prefix_score.py --puzzle CSV --frame FRAME.json PREFIX.json...
  [--depth-override K] emits TSV rows to stdout:
  prefix_tag  depth  lp_obj  fixed_matches  ub_total  n_empty  ms
"""
import argparse
import json
import os
import sys
import time

import numpy as np
import highspy

BORDER = 0
N = 14  # interior grid


def load_puzzle(path):
    lines = [l.strip() for l in open(path) if l.strip()]
    size = int(lines[0])
    assert size == 16
    pieces, hints = [], []
    for pid, line in enumerate(lines[1:]):
        cols = line.split(",")
        e = [BORDER if int(c, 2) == 65535 else int(c, 2) for c in cols[:4]]
        pieces.append(e)  # [N,E,S,W] base orientation
        if len(cols) >= 7:
            x, y, rot = int(cols[4]), int(cols[5]), int(cols[6])
            if not (x == 0 and y == 0 and rot == 0):
                hints.append((y * 16 + x, pid, rot))
    return pieces, hints


def oriented(base, rot):
    return [base[(s + 4 - rot) % 4] for s in range(4)]


def build_interior(pieces):
    """global pid -> local id for the 196 zero-border pieces"""
    g2l, l2g, rot_edges = {}, [], []
    for pid, e in enumerate(pieces):
        if BORDER not in e:
            g2l[pid] = len(l2g)
            l2g.append(pid)
            rot_edges.append([oriented(e, r) for r in range(4)])
    assert len(l2g) == N * N
    return g2l, l2g, rot_edges


def rim_targets_from_frame(frame_path, pieces):
    """interior cell -> [N,E,S,W] required color or None, from ring"""
    pl = json.load(open(frame_path))["placement"]
    ring = {}
    for ent in pl:
        pos = ent["pos"]
        r, c = pos // 16, pos % 16
        if r in (0, 15) or c in (0, 15):
            ring[(r, c)] = oriented(pieces[ent["piece_id"]], ent["rotation"])
    tg = {}

    def set_t(cell, side, color):
        tg.setdefault(cell, [None] * 4)[side] = color

    for x in range(1, 15):
        if (0, x) in ring:
            set_t((0) * N + (x - 1), 0, ring[(0, x)][2])      # top ring S side
        if (15, x) in ring:
            set_t((13) * N + (x - 1), 2, ring[(15, x)][0])    # bottom ring N
    for y in range(1, 15):
        if (y, 0) in ring:
            set_t((y - 1) * N + 0, 3, ring[(y, 0)][1])        # left ring E
        if (y, 15) in ring:
            set_t((y - 1) * N + 13, 1, ring[(y, 15)][3])      # right ring W
    return tg


def interior_cell(pos):
    r, c = pos // 16, pos % 16
    if 1 <= r <= 14 and 1 <= c <= 14:
        return (r - 1) * N + (c - 1)
    return None


def score_prefix(prefix_path, g2l, rot_edges, rim_tg, hints, depth_override=None):
    pj = json.load(open(prefix_path))
    depth = pj.get("prefix_depth", len(pj["placement"]))
    placed = {}  # interior cell -> oriented edges
    used = set()  # local pids
    for ent in pj["placement"]:
        cell = interior_cell(ent["pos"])
        assert cell is not None, f"ring position in prefix: {ent['pos']}"
        lp = g2l[ent["piece_id"]]
        placed[cell] = rot_edges[lp][ent["rotation"]]
        used.add(lp)
    # hints beyond the prefix are forced
    for pos, pid, rot in hints:
        cell = interior_cell(pos)
        if cell is None or cell in placed:
            continue
        lp = g2l[pid]
        placed[cell] = rot_edges[lp][rot]
        used.add(lp)

    empty = [c for c in range(N * N) if c not in placed]
    rem = [lp for lp in range(N * N) if lp not in used]
    ne, nr = len(empty), len(rem)
    assert ne == nr, (ne, nr)
    eidx = {c: i for i, c in enumerate(empty)}

    # fixed matches among placed cells + placed-vs-rim (constant term)
    fixed = 0
    for cell, e in placed.items():
        # E and S neighbors only (count each edge once)
        r, c = divmod(cell, N)
        if c + 1 < N and cell + 1 in placed:
            fixed += e[1] == placed[cell + 1][3]
        if r + 1 < N and cell + N in placed:
            fixed += e[2] == placed[cell + N][0]
        t = rim_tg.get(cell)
        if t:
            for s in range(4):
                if t[s] is not None and e[s] == t[s]:
                    fixed += 1

    # ---- LP ----
    t0 = time.time()
    nx = ne * nr * 4  # x[ci, pj, rot]
    xid = lambda ci, pj_, rot: (ci * nr + pj_) * 4 + rot

    obj = np.zeros(nx)
    # fixed-side coefficients
    fixed_sides = []  # per empty cell: [(side, color)]
    for cell in empty:
        fs = []
        r, c = divmod(cell, N)
        for s, (dr, dc) in enumerate([(-1, 0), (0, 1), (1, 0), (0, -1)]):
            rr, cc = r + dr, c + dc
            if 0 <= rr < N and 0 <= cc < N:
                nb = rr * N + cc
                if nb in placed:
                    fs.append((s, placed[nb][(s + 2) % 4]))
        t = rim_tg.get(cell)
        if t:
            for s in range(4):
                if t[s] is not None:
                    fs.append((s, t[s]))
        fixed_sides.append(fs)
    for ci in range(ne):
        for pj_ in range(nr):
            re = rot_edges[rem[pj_]]
            for rot in range(4):
                e = re[rot]
                v = sum(e[s] == k for s, k in fixed_sides[ci])
                if v:
                    obj[xid(ci, pj_, rot)] = v

    # internal empty-empty edges
    pairs = []  # (ci_a, side_a, ci_b)
    for cell in empty:
        r, c = divmod(cell, N)
        if c + 1 < N and cell + 1 in eidx:
            pairs.append((eidx[cell], 1, eidx[cell + 1]))
        if r + 1 < N and cell + N in eidx:
            pairs.append((eidx[cell], 2, eidx[cell + N]))

    colors = sorted({e[s] for lp in rem for rot in range(4)
                     for s in range(4) for e in [rot_edges[lp][rot]]})
    ny = len(pairs) * len(colors)
    kidx = {k: i for i, k in enumerate(colors)}

    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("threads", 1)
    # dual simplex needs ~35 s on this degenerate assignment polytope;
    # IPM solves it in 0.7 s with the same objective to 6 decimals
    h.setOptionValue("solver", "ipm")
    h.setOptionValue("ipm_optimality_tolerance", 1e-9)
    inf = highspy.kHighsInf

    ncols = nx + ny
    col_lower = np.zeros(ncols)
    col_upper = np.ones(ncols)
    col_cost = np.zeros(ncols)
    col_cost[:nx] = -obj  # HiGHS minimizes
    col_cost[nx:] = -1.0

    # rows: cell sum=1 (ne), piece sum=1 (nr), y constraints (2*ny)
    rows_lo, rows_hi = [], []
    starts, indices, values = [0], [], []

    def add_row(idx, val, lo, hi):
        indices.extend(idx)
        values.extend(val)
        starts.append(len(indices))
        rows_lo.append(lo)
        rows_hi.append(hi)

    for ci in range(ne):
        idx = [xid(ci, pj_, rot) for pj_ in range(nr) for rot in range(4)]
        add_row(idx, [1.0] * len(idx), 1.0, 1.0)
    for pj_ in range(nr):
        idx = [xid(ci, pj_, rot) for ci in range(ne) for rot in range(4)]
        add_row(idx, [1.0] * len(idx), 1.0, 1.0)

    # color-mass per (pair endpoint, color): y - mass <= 0
    # precompute per (ci, side, k) -> list of x ids
    for pi, (ca, sa, cb) in enumerate(pairs):
        sb = (sa + 2) % 4
        for k in colors:
            yi = nx + pi * len(colors) + kidx[k]
            ia = [xid(ca, pj_, rot) for pj_ in range(nr) for rot in range(4)
                  if rot_edges[rem[pj_]][rot][sa] == k]
            ib = [xid(cb, pj_, rot) for pj_ in range(nr) for rot in range(4)
                  if rot_edges[rem[pj_]][rot][sb] == k]
            add_row([yi] + ia, [1.0] + [-1.0] * len(ia), -inf, 0.0)
            add_row([yi] + ib, [1.0] + [-1.0] * len(ib), -inf, 0.0)

    lp = highspy.HighsLp()
    lp.num_col_ = ncols
    lp.num_row_ = len(rows_lo)
    lp.col_cost_ = col_cost
    lp.col_lower_ = col_lower
    lp.col_upper_ = col_upper
    lp.row_lower_ = np.array(rows_lo)
    lp.row_upper_ = np.array(rows_hi)
    lp.a_matrix_.format_ = highspy.MatrixFormat.kRowwise
    lp.a_matrix_.start_ = np.array(starts)
    lp.a_matrix_.index_ = np.array(indices, dtype=np.int32)
    lp.a_matrix_.value_ = np.array(values)
    h.passModel(lp)
    h.run()
    assert h.getModelStatus() == highspy.HighsModelStatus.kOptimal, \
        h.modelStatusToString(h.getModelStatus())
    lp_obj = -h.getObjectiveValue()
    ms = (time.time() - t0) * 1000

    tag = os.path.basename(prefix_path)[:-5]
    return dict(tag=tag, depth=depth, lp_obj=lp_obj, fixed=fixed,
                ub_total=fixed + lp_obj + 60, n_empty=ne, ms=ms)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", default="../data/puzzles/size_16_official_eternity.csv")
    ap.add_argument("--frame", required=True)
    ap.add_argument("prefixes", nargs="+")
    a = ap.parse_args()

    pieces, hints = load_puzzle(a.puzzle)
    g2l, _l2g, rot_edges = build_interior(pieces)
    rim_tg = rim_targets_from_frame(a.frame, pieces)

    print("\t".join(["tag", "depth", "lp_obj", "fixed", "ub_total",
                     "n_empty", "ms"]))
    for pf in a.prefixes:
        r = score_prefix(pf, g2l, rot_edges, rim_tg, hints)
        print(f"{r['tag']}\t{r['depth']}\t{r['lp_obj']:.4f}\t{r['fixed']}"
              f"\t{r['ub_total']:.4f}\t{r['n_empty']}\t{r['ms']:.0f}")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
