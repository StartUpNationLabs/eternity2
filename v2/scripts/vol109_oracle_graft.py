#!/usr/bin/env python3
"""Vol-109 T1.a — empirical test of oracle-graft.

Take a partial board + oracle good basin. For each σ-cycle (sorted
by size desc), GRAFT the oracle's (piece_id, rotation) at those
cycle positions into the partial. Score the result.

If the grafted board's score > the partial's ALNS-ceiling, then
the analytical concern in [[oracle-aware-alns-repair]] was wrong
and the multi-day infra is justified.

If grafted score ~= partial's ALNS-ceiling, the concern is
confirmed and we move on.

Usage:
    vol109_oracle_graft.py <partial.json> <oracle.json> <puzzle.csv>
"""

import argparse
import csv
import json
import sys
from pathlib import Path


def parse_color(s):
    """Parse a 16-bit binary color word. 65535 (all ones) = BORDER (0)."""
    s = s.strip()
    v = int(s, 2)
    if v == 65535:
        return 0  # BORDER
    return v


def load_puzzle(csv_path):
    """Load piece edges from a Selby-Riordan E2 CSV.
    Format: first line = size; each piece line =
    top_binary,right_binary,bottom_binary,left_binary,x,y,rot.
    """
    pieces = {}
    with open(csv_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    # First line: size (single integer).
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
    """edges = (top, right, bottom, left). Rotate CW by rot quarter turns.
    CW rotation: top <- left, right <- top, bottom <- right, left <- bottom.
    After rot=1: (left, top, right, bottom).
    """
    t, r, b, l = edges
    if rot == 0:
        return (t, r, b, l)
    elif rot == 1:
        return (l, t, r, b)
    elif rot == 2:
        return (b, l, t, r)
    else:  # rot == 3
        return (r, b, l, t)


def load_board(path):
    """Return dict {pos: (piece_id, rotation)}."""
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
    """Count matched adjacent edges. Border (color 0) doesn't count."""
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
            # right edge with cell (x+1, y)
            if x + 1 < width:
                npos = pos + 1
                if npos in board:
                    npid, nrot = board[npos]
                    if npid in pieces:
                        nt, nr, nb, nl = rotate_edges(pieces[npid], nrot)
                        if r == nl and r != 0:
                            matched += 1
            # bottom edge with cell (x, y+1)
            if y + 1 < height:
                npos = pos + width
                if npos in board:
                    npid, nrot = board[npos]
                    if npid in pieces:
                        nt, nr, nb, nl = rotate_edges(pieces[npid], nrot)
                        if b == nt and b != 0:
                            matched += 1
    return matched, placed


def sigma_cycles(partial, oracle):
    """σ on positions: σ(p) = oracle_pos[piece at p in partial].
    Returns list of cycles (lists of positions), sorted by length desc.
    """
    # piece -> oracle_pos
    ora_pos = {}
    for pos, (pid, _) in oracle.items():
        ora_pos[pid] = pos
    # σ for each placed position in partial
    sigma = {}
    for pos, (pid, _) in partial.items():
        if pid in ora_pos:
            sigma[pos] = ora_pos[pid]
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


def graft(partial, oracle, cells):
    """Return a new board = partial with `cells` replaced by oracle's
    (piece_id, rotation) at those positions."""
    out = dict(partial)
    for c in cells:
        if c in oracle:
            out[c] = oracle[c]
        else:
            # Oracle doesn't have this position placed; drop the partial's piece too.
            out.pop(c, None)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("partial")
    ap.add_argument("oracle")
    ap.add_argument("puzzle")
    args = ap.parse_args()

    pieces = load_puzzle(args.puzzle)
    print(f"loaded {len(pieces)} pieces from {args.puzzle}")

    partial = load_board(args.partial)
    oracle = load_board(args.oracle)

    p_score, p_placed = score_board(partial, pieces)
    o_score, o_placed = score_board(oracle, pieces)
    print(f"partial: {p_placed} placed, {p_score}/480 matched ({args.partial})")
    print(f"oracle:  {o_placed} placed, {o_score}/480 matched ({args.oracle})")

    cycles = sigma_cycles(partial, oracle)
    print(f"σ-cycles: {len(cycles)} cycles, sizes={[len(c) for c in cycles[:10]]}...")

    if not cycles:
        print("no cycles — partial matches oracle on placed cells")
        return

    # Graft the largest cycle.
    big = cycles[0]
    print(f"\n=== GRAFT largest cycle ({len(big)} cells) ===")
    grafted = graft(partial, oracle, big)
    g_score, g_placed = score_board(grafted, pieces)
    print(f"  grafted: {g_placed} placed, {g_score}/480 matched (vs partial {p_score}, oracle {o_score})")

    # Graft cumulative cycles.
    cum_cells = []
    for i, cyc in enumerate(cycles):
        cum_cells.extend(cyc)
        grafted = graft(partial, oracle, cum_cells)
        g_score, g_placed = score_board(grafted, pieces)
        print(f"  graft top-{i+1} cycles ({len(cum_cells)} cells total): {g_placed} placed, {g_score}/480")
        if i >= 5:
            break


if __name__ == "__main__":
    main()
