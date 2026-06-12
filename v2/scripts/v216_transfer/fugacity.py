#!/usr/bin/env python3
"""Fugacity-corrected transfer counts (vol-216, user-directed).

Problem: transfer/MPS counts allow piece repeats — vol-209 measured a
10^101 overcount at board scale. Statistical-mechanics fix: weight each
piece p by a fugacity z_p in the transfer DP (grand-canonical ensemble
Z(z)), then solve the saddle  u_p(z) = E[usage of p] = 1  by Sinkhorn-
style iteration z_p <- z_p / u_p. Mean-field estimate of the TRUE
(distinct-pieces) count:

    log N_mf = log Z(z*) - sum_p log z*_p        (equal case:
                                                  #cells == #pool)

Validation playground: 2-row bands cut from a REAL record board (rows
12-13 of the vol-215 452 board), with the board's true north boundary,
pool = exactly the pieces the board used there. Ground truth by exact
DFS enumeration (distinctness enforced). Compare:
    naive   = repeats-allowed transfer count
    mf      = fugacity-corrected count
against exact. Success = mf cuts the log10 error by a large factor.
"""
import argparse
import json
import sys
import numpy as np

sys.path.insert(0, "scripts/v216_lp")
import lp_prefix_score as L

NC = 23


def oriented(base, rot):
    return [base[(s + 4 - rot) % 4] for s in range(4)]


class Band:
    """r_rows x r_cols region with fixed N boundary colors, fixed W
    entry colors, free E exit, optional S targets; pool of piece ids."""

    def __init__(self, rot_edges, pool, north, west, south=None):
        self.re = rot_edges
        self.pool = list(pool)
        self.north = north      # [cols] color above row 0 per col
        self.west = west        # [rows] color entering col 0 per row
        self.south = south      # [cols] or None
        self.rows = len(west)
        self.cols = len(north)

    def exact_count(self):
        """DFS with distinctness, column-major; returns exact count"""
        rows, cols = self.rows, self.cols
        cnt = 0
        pool = self.pool
        re = self.re

        def go(col, row, west_cols, north_cols, used):
            nonlocal cnt
            if col == self.cols:
                cnt += 1
                return
            want_n = north_cols[row]
            want_w = west_cols[row]
            for i, p in enumerate(pool):
                if used >> i & 1:
                    continue
                for rot in range(4):
                    o = re[p][rot]
                    if o[0] != want_n or o[3] != want_w:
                        continue
                    if self.south is not None and row == rows - 1 \
                            and o[2] != self.south[col]:
                        continue
                    nw = list(west_cols)
                    nw[row] = o[1]
                    nn = list(north_cols)
                    nn[row] = None  # consumed
                    if row + 1 < rows:
                        nn2 = list(north_cols)
                        nn2[row] = north_cols[row]
                        # north for next row in same col = this S
                        go_next_row(col, row, o, nw, used | 1 << i)
                    else:
                        go(col + 1, 0,
                           nw, [self.north[col + 1] if col + 1 < cols
                                else None] * 1, used | 1 << i)
            return

        # simpler: explicit cell order, carry full state
        cnt = 0

        def rec(idx, east, norths, used):
            nonlocal cnt
            if idx == rows * cols:
                cnt += 1
                return
            col, row = divmod(idx, rows)
            want_w = east[row]
            want_n = norths[row]
            for i, p in enumerate(pool):
                if used >> i & 1:
                    continue
                for rot in range(4):
                    o = re[p][rot]
                    if o[0] != want_n or o[3] != want_w:
                        continue
                    if self.south is not None and row == rows - 1 \
                            and o[2] != self.south[col]:
                        continue
                    e2 = list(east)
                    e2[row] = o[1]
                    n2 = list(norths)
                    if row + 1 < rows:
                        n2[row + 1] = o[2]
                        rec(idx + 1, e2, n2, used | 1 << i)
                    else:
                        if col + 1 < cols:
                            n3 = [self.north[col + 1]] + [None] * (rows - 1)
                            rec(idx + 1, e2, n3, used | 1 << i)
                        else:
                            rec(idx + 1, e2, n2, used | 1 << i)

        rec(0, list(self.west), [self.north[0]] + [None] * (rows - 1), 0)
        return cnt

    def column_ops(self, logz):
        """per-column weighted transfer: state = tuple of E colors of
        each row; returns list of dict ops applied left to right, plus
        per-column per-piece usage bookkeeping via forward-backward."""
        rows, cols = self.rows, self.cols
        z = np.exp(logz)
        re = self.re
        pool = self.pool
        np_pool = len(pool)

        # enumerate column fillings: choose (piece, rot) per row with
        # vertical matching inside the column and N boundary at row 0
        col_fill = []   # per col: list of (w_in tuple, e_out tuple, weight, piece idx list)
        for c in range(cols):
            fills = []

            def grow(row, w_need_free, e_acc, idx_acc, north_color, wsum):
                # w colors are free inputs (state); we enumerate pieces by
                # rotation and record their W as the required input
                if row == rows:
                    fills.append((tuple(w_need_free), tuple(e_acc),
                                  wsum, tuple(idx_acc)))
                    return
                for i, p in enumerate(pool):
                    if i in idx_acc:
                        continue
                    for rot in range(4):
                        o = re[p][rot]
                        if o[0] != north_color:
                            continue
                        if self.south is not None and row == rows - 1 \
                                and o[2] != self.south[c]:
                            continue
                        grow(row + 1, w_need_free + [o[3]],
                             e_acc + [o[1]], idx_acc + [i],
                             o[2], wsum + logz[i])

            grow(0, [], [], [], self.north[c], 0.0)
            col_fill.append(fills)
        return col_fill

    def z_count(self, logz):
        """log Z(z) + per-piece expected usage, via forward-backward
        over column states"""
        rows, cols = self.rows, self.cols
        col_fill = self.column_ops(logz)
        # state index: tuple of E colors per row
        start = tuple(self.west)
        fwd = [dict() for _ in range(cols + 1)]
        fwd[0][start] = 0.0   # log mass

        def logsumexp_into(d, k, v):
            if k in d:
                m = max(d[k], v)
                d[k] = m + np.log1p(np.exp(min(d[k], v) - m))
            else:
                d[k] = v

        for c in range(cols):
            for st, lm in fwd[c].items():
                for (w_in, e_out, w, _idx) in col_fill[c]:
                    if w_in == st:
                        logsumexp_into(fwd[c + 1], e_out, lm + w)
        if not fwd[cols]:
            return -np.inf, np.zeros(len(self.pool))
        logZ = None
        for v in fwd[cols].values():
            logZ = v if logZ is None else max(logZ, v) + np.log1p(
                np.exp(min(logZ, v) - max(logZ, v)))
        # backward
        bwd = [dict() for _ in range(cols + 1)]
        for st in fwd[cols]:
            bwd[cols][st] = 0.0
        for c in range(cols - 1, -1, -1):
            for (w_in, e_out, w, _idx) in col_fill[c]:
                if e_out in bwd[c + 1]:
                    logsumexp_into(bwd[c], w_in, bwd[c + 1][e_out] + w)
        # usage
        u = np.zeros(len(self.pool))
        for c in range(cols):
            for (w_in, e_out, w, idx) in col_fill[c]:
                if w_in in fwd[c] and e_out in bwd[c + 1]:
                    lp_ = fwd[c][w_in] + w + bwd[c + 1][e_out] - logZ
                    m = np.exp(lp_)
                    for i in idx:
                        u[i] += m
        return logZ, u

    def fugacity_count(self, iters=400, lr=0.7, verbose=False):
        n = len(self.pool)
        logz = np.zeros(n)
        target = self.rows * self.cols / n  # equal case: 1 if n == cells
        for it in range(iters):
            logZ, u = self.z_count(logz)
            if not np.isfinite(logZ):
                return -np.inf, None
            err = np.max(np.abs(u - target))
            if verbose and it % 50 == 0:
                print(f"  it {it}: logZ {logZ:.3f} usage err {err:.4f}",
                      file=sys.stderr)
            if err < 1e-4:
                break
            with np.errstate(divide="ignore"):
                logz -= lr * (np.log(np.maximum(u, 1e-12)) - np.log(target))
        logZ, u = self.z_count(logz)
        # mean-field canonical estimate (equal case): all pieces used once
        log_n_mf = logZ - float(np.sum(logz) * target)
        return log_n_mf, logZ


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", required=True, help="record board JSON")
    ap.add_argument("--rows", type=int, default=2)
    ap.add_argument("--cols", type=int, nargs="+", default=[4, 5, 6])
    ap.add_argument("--row0", type=int, default=12,
                    help="interior row of the band's top row")
    ap.add_argument("--pool-cols", type=int, default=0,
                    help="draw the pool from this many columns (>= cols "
                         "gives the subset case); 0 = equal case")
    a = ap.parse_args()

    pieces, hints = L.load_puzzle("../data/puzzles/size_16_official_eternity.csv")
    g2l, _, rot_edges = L.build_interior(pieces)
    pl = json.load(open(a.board))["placement"]
    grid = {}
    for e in pl:
        cell = L.interior_cell(e["pos"])
        if cell is not None:
            grid[cell] = (g2l[e["piece_id"]], e["rotation"])

    print(f"{'cols':>4} {'cells':>5} {'exact':>10} {'naive_log10':>11} "
          f"{'mf_log10':>9} {'true_log10':>10} {'err_naive':>9} {'err_mf':>7}")
    for cols in a.cols:
        # band: rows row0..row0+rows-1, cols 0..cols-1, true boundary
        north = []
        west = []
        pool = []
        for c in range(cols):
            up = grid[(a.row0 - 1) * 14 + c]
            north.append(rot_edges[up[0]][up[1]][2])
        for r in range(a.rows):
            west.append(L.rim_targets_from_frame.__defaults__ if False else None)
        # west entry: rim targets (col 0 faces the ring)
        rim = L.rim_targets_from_frame(
            "output/vol-212/frames_best/strict460a.json", pieces)
        west = [rim[(a.row0 + r) * 14 + 0][3] for r in range(a.rows)]
        pc = max(a.pool_cols, cols)
        for r in range(a.rows):
            for c in range(pc):
                pool.append(grid[(a.row0 + r) * 14 + c][0])

        band = Band(rot_edges, pool, north, west, south=None)
        exact = band.exact_count()
        naive_logZ, u1 = band.z_count(np.zeros(len(pool)))
        if len(pool) == a.rows * cols:
            mf, _ = band.fugacity_count()       # equal case: Sinkhorn saddle
        else:
            # subset case: Poissonization square-free correction at z=1
            mf = naive_logZ + float(np.sum(np.log1p(u1) - u1))
        l10 = np.log10(np.e)
        true_l = np.log10(exact) if exact > 0 else -np.inf
        print(f"{cols:>4} {a.rows*cols:>5} {exact:>10} "
              f"{naive_logZ*l10:>11.3f} {mf*l10:>9.3f} {true_l:>10.3f} "
              f"{naive_logZ*l10-true_l:>9.3f} {mf*l10-true_l:>7.3f}")


if __name__ == "__main__":
    main()
