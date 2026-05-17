#!/usr/bin/env python3
"""Vol-122 INVENTION 3 — corner-perm × border-ring DP (per-side upper bound).

For each of 24 corner-perms × 4 corner rotations each, solve 4 independent
border-chain DPs (top/right/bottom/left). Each chain DP computes max
matched-edge count assuming pieces can be reused freely (UB, not feasible).

If best UB < 60, no corner-perm admits a perfect border ring (even
ignoring piece-uniqueness). This sharpens vol-44's class-A border = 60
matched finding.

Output is upper bound only; piece-uniqueness sweep is a follow-up.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from itertools import permutations
from pathlib import Path


def parse_color(s):
    v = int(s.strip(), 2)
    return 0 if v == 65535 else v


def load_puzzle(csv_path):
    pieces = {}
    with open(csv_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    pid = 0
    for line in lines[1:]:
        cols = line.split(',')
        if len(cols) >= 4:
            try:
                t = parse_color(cols[0])
                r = parse_color(cols[1])
                b = parse_color(cols[2])
                l = parse_color(cols[3])
                pieces[pid] = (t, r, b, l)
                pid += 1
            except ValueError:
                pass
    return pieces


def rotate(edges, rot):
    t, r, b, l = edges
    return [(t, r, b, l), (l, t, r, b), (b, l, t, r), (r, b, l, t)][rot]


def classify(pieces):
    corners, edges, interiors = [], [], []
    for pid, e in pieces.items():
        n = sum(1 for c in e if c == 0)
        if n == 2:
            corners.append(pid)
        elif n == 1:
            edges.append(pid)
        else:
            interiors.append(pid)
    return corners, edges, interiors


def corner_rots(pieces, pid, pos):
    e = pieces[pid]
    out = []
    for r in range(4):
        t, ri, b, l = rotate(e, r)
        if (pos == 'TL' and t == 0 and l == 0) or \
           (pos == 'TR' and t == 0 and ri == 0) or \
           (pos == 'BL' and b == 0 and l == 0) or \
           (pos == 'BR' and b == 0 and ri == 0):
            out.append(r)
    return out


def edge_options(pieces, edge_pids, side):
    """Return dict: back_color -> list of (pid, rot, forward_color)."""
    by_back = defaultdict(list)
    for pid in edge_pids:
        for r in range(4):
            t, ri, b, l = rotate(pieces[pid], r)
            if side == 'T' and t == 0:
                by_back[l].append((pid, r, ri))    # back=L, fwd=R
            elif side == 'R' and ri == 0:
                by_back[t].append((pid, r, b))     # back=T, fwd=B
            elif side == 'B' and b == 0:
                by_back[ri].append((pid, r, l))    # back=R, fwd=L
            elif side == 'L' and l == 0:
                by_back[b].append((pid, r, t))     # back=B, fwd=T
    return by_back


def all_edge_options(pieces, edge_pids, side):
    """Return ALL (pid, rot, back_color, forward_color) tuples for `side`."""
    out = []
    for pid in edge_pids:
        for r in range(4):
            t, ri, b, l = rotate(pieces[pid], r)
            if side == 'T' and t == 0:
                out.append((pid, r, l, ri))
            elif side == 'R' and ri == 0:
                out.append((pid, r, t, b))
            elif side == 'B' and b == 0:
                out.append((pid, r, ri, l))
            elif side == 'L' and l == 0:
                out.append((pid, r, b, t))
    return out


def chain_max_matched(start_color, target_color, side_options, n_cells=14):
    """DP: max matched-edge count over 14-cell chain, no piece-uniqueness.
    Match = back equals state color (counts +1).
    Last cell forward must equal target_color for +1 extra.
    """
    cur = {start_color: 0}
    for i in range(n_cells):
        nxt = {}
        for state_color, matched in cur.items():
            for (pid, r, back, fwd) in side_options:
                m = matched + (1 if back == state_color else 0)
                if i == n_cells - 1 and fwd == target_color:
                    m += 1
                if fwd not in nxt or nxt[fwd] < m:
                    nxt[fwd] = m
        cur = nxt
        if not cur:
            return 0
    return max(cur.values())


def main():
    pieces = load_puzzle(Path("../data/puzzles/size_16_official_eternity.csv"))
    corners, edges, interiors = classify(pieces)
    print(f"# {len(corners)}c {len(edges)}e {len(interiors)}i", file=sys.stderr)

    # Precompute per-side options
    sides = {s: all_edge_options(pieces, edges, s) for s in 'TRBL'}
    for s, opts in sides.items():
        print(f"# side {s}: {len(opts)} (piece,rot) options", file=sys.stderr)

    best_total = 0
    best_config = None
    perfect_configs = []  # all configs hitting 60

    for perm_i, (tl, tr, br, bl) in enumerate(permutations(corners)):
        tl_rs = corner_rots(pieces, tl, 'TL')
        tr_rs = corner_rots(pieces, tr, 'TR')
        bl_rs = corner_rots(pieces, bl, 'BL')
        br_rs = corner_rots(pieces, br, 'BR')
        if not (tl_rs and tr_rs and bl_rs and br_rs):
            continue
        for tl_r in tl_rs:
            te = rotate(pieces[tl], tl_r)  # (T,R,B,L)
            for tr_r in tr_rs:
                tre = rotate(pieces[tr], tr_r)
                for br_r in br_rs:
                    bre = rotate(pieces[br], br_r)
                    for bl_r in bl_rs:
                        ble = rotate(pieces[bl], bl_r)
                        # Chain starts/targets per CW ring:
                        # TL → top row (14 cells) → TR → right col (14) → BR → bottom row (14) → BL → left col (14) → TL
                        c1 = chain_max_matched(te[1], tre[3], sides['T'])  # top
                        c2 = chain_max_matched(tre[2], bre[0], sides['R'])  # right
                        c3 = chain_max_matched(bre[3], ble[1], sides['B'])  # bottom (CW reversal)
                        c4 = chain_max_matched(ble[0], te[2], sides['L'])   # left
                        total = c1 + c2 + c3 + c4
                        if total > best_total:
                            best_total = total
                            best_config = (perm_i, (tl, tl_r), (tr, tr_r), (br, br_r), (bl, bl_r),
                                           c1, c2, c3, c4)
                        if total == 60:
                            perfect_configs.append((perm_i, (tl, tl_r), (tr, tr_r), (br, br_r), (bl, bl_r)))

    print(f"# Best border UB = {best_total}/60")
    print(f"# Best config = {best_config}")
    print(f"# Number of (corner-perm, rotation) configs achieving UB-60: {len(perfect_configs)}")
    if perfect_configs:
        print(f"# First 5 perfect configs:")
        for c in perfect_configs[:5]:
            print(f"  {c}")
    print()
    print("# Interpretation:")
    if best_total < 60:
        print(f"#   No (corner-perm, rot) admits a perfect border ring even ignoring piece-uniqueness.")
        print(f"#   This sharpens vol-44 border-class-A=60 finding to UB={best_total}/60 across all rots.")
    elif perfect_configs:
        print(f"#   {len(perfect_configs)} configs admit UB-60 borders. Piece-uniqueness sweep is the next step.")


if __name__ == "__main__":
    main()
