#!/usr/bin/env python3
"""Vol-110 Path B — piece-set blend between two 459 basins.

Given $b_60$ and $b_{110}$, both score 459, structurally disjoint.
Sample blends: for each cell, pick the piece from $b_{60}$ or
$b_{110}$ with probability p ∈ {0.1, 0.2, ..., 0.9}.

But: a blend must be VALID (piece-uniqueness preserved). The naive
sample violates this — both basins place piece P at different
positions, so a mix may have P appearing twice.

Two strategies:
1. Sample by CELL, then reject if invalid. Most samples fail.
2. Sample by ELEMENT of σ-cycle decomposition: for each cycle in
   σ_{b_60 → b_110}, choose whether to apply the cycle (take
   $b_{110}$'s arrangement for those cells) or not (keep $b_{60}$'s).
   Each cycle is INDIVIDUALLY a valid permutation, so any subset
   of cycles is also a valid permutation. Score the result.

Strategy 2 is principled. There are 2^n_cycles = 2^8 = 256 subsets
for the 8 cycles between the two 459 basins. Trivially enumerable.

Usage:
    vol110_basin_blend.py <board_60> <board_110> <puzzle.csv>
"""

import csv
import json
import sys
from itertools import combinations
from pathlib import Path


def parse_color(s):
    s = s.strip()
    v = int(s, 2)
    if v == 65535:
        return 0
    return v


def load_puzzle(csv_path):
    pieces = {}
    with open(csv_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    pid = 0
    for line in lines[1:]:
        cols = line.split(',')
        if len(cols) < 4:
            continue
        try:
            t = parse_color(cols[0])
            r = parse_color(cols[1])
            b = parse_color(cols[2])
            l = parse_color(cols[3])
        except ValueError:
            continue
        pieces[pid] = (t, r, b, l)
        pid += 1
    return pieces


def rotate_edges(edges, rot):
    t, r, b, l = edges
    if rot == 0:
        return (t, r, b, l)
    elif rot == 1:
        return (l, t, r, b)
    elif rot == 2:
        return (b, l, t, r)
    else:
        return (r, b, l, t)


def load_board(path):
    with open(path) as f:
        d = json.load(f)
    arr = d.get("placement") or d.get("board", {}).get("placement", [])
    out = {}
    for idx, item in enumerate(arr):
        if item is None:
            continue
        pos = int(item.get("pos", idx))
        out[pos] = (int(item["piece_id"]), int(item["rotation"]))
    return out


def score_board(board, pieces, width=16, height=16):
    matched = 0
    placed = 0
    for y in range(height):
        for x in range(width):
            pos = y * width + x
            if pos not in board:
                continue
            placed += 1
            pid, rot = board[pos]
            if pid not in pieces:
                continue
            t, r, b, l = rotate_edges(pieces[pid], rot)
            if x + 1 < width:
                npos = pos + 1
                if npos in board:
                    npid, nrot = board[npos]
                    if npid in pieces:
                        nt, nr, nb, nl = rotate_edges(pieces[npid], nrot)
                        if r == nl and r != 0:
                            matched += 1
            if y + 1 < height:
                npos = pos + width
                if npos in board:
                    npid, nrot = board[npos]
                    if npid in pieces:
                        nt, nr, nb, nl = rotate_edges(pieces[npid], nrot)
                        if b == nt and b != 0:
                            matched += 1
    return matched, placed


def sigma_cycles(board_a, board_b):
    """σ on positions: σ(p) = b_inv_pos[a_pid(p)]."""
    b_pos = {}
    for pos, (pid, _) in board_b.items():
        b_pos[pid] = pos
    sigma = {}
    for pos, (pid, _) in board_a.items():
        if pid in b_pos:
            sigma[pos] = b_pos[pid]
    seen = set()
    cycles = []
    for start in list(sigma.keys()):
        if start in seen:
            continue
        cyc = []
        q = start
        while q not in seen and q in sigma:
            seen.add(q)
            cyc.append(q)
            q = sigma[q]
        if len(cyc) >= 2:
            cycles.append(cyc)
    cycles.sort(key=lambda c: -len(c))
    return cycles


def apply_cycles_subset(base, target, cycles, subset_indices):
    """For each cycle index in subset_indices, replace base[cells]
    with target[cells]. Returns new board dict."""
    out = dict(base)
    for i in subset_indices:
        for p in cycles[i]:
            if p in target:
                out[p] = target[p]
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("board_a")
    ap.add_argument("board_b")
    ap.add_argument("puzzle")
    args = ap.parse_args()

    pieces = load_puzzle(args.puzzle)
    a = load_board(args.board_a)
    b = load_board(args.board_b)

    s_a, _ = score_board(a, pieces)
    s_b, _ = score_board(b, pieces)
    print(f"board_a: {s_a}/480 ({args.board_a})")
    print(f"board_b: {s_b}/480 ({args.board_b})")

    cycles = sigma_cycles(a, b)
    print(f"σ-cycles a → b: {len(cycles)} cycles, sizes={[len(c) for c in cycles]}")

    # Enumerate all 2^n subsets of cycles. For 8 cycles → 256 subsets.
    n = len(cycles)
    best = (s_a, "empty")
    print(f"\nEnumerating {2**n} cycle subsets...")
    for mask in range(2**n):
        subset = [i for i in range(n) if (mask >> i) & 1]
        blend = apply_cycles_subset(a, b, cycles, subset)
        s, _ = score_board(blend, pieces)
        if s > best[0]:
            best = (s, str(subset))
            print(f"  NEW BEST: subset={subset} (sizes={[len(cycles[i]) for i in subset]}), score={s}")
        elif s == s_a or s == s_b:
            # Suppress same-score noise.
            pass
        elif s > 450:
            print(f"  subset={subset}: score={s}")

    print(f"\nBEST: score={best[0]}, subset={best[1]}")


if __name__ == "__main__":
    main()
