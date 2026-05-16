#!/usr/bin/env python3
"""Vol-112 T1 — basin-mix MIP.

Given N basin boards (each placing 256 pieces), formulate an MIP:
- For each cell c, choose ONE of the N basin assignments at c.
- Subject to piece-uniqueness across the whole board.
- Maximise matched edges.

If MIP optimum > 459, we've found a strictly better board reachable
by mixing existing 459 basins. If MIP optimum = 459, the 4 basins
are the local optima of this convex hull.

Uses PuLP for the LP/MIP (lightweight Python, no need for HiGHS
bindings).
"""

import csv
import json
import sys
from itertools import product
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


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle")
    ap.add_argument("basins", nargs="+")
    args = ap.parse_args()

    pieces = load_puzzle(args.puzzle)
    print(f"loaded {len(pieces)} pieces")

    boards = [load_board(p) for p in args.basins]
    print(f"loaded {len(boards)} basins from:")
    for p in args.basins:
        print(f"  {p}")

    W, H = 16, 16
    N = len(boards)

    # For each cell c and basin b, get (piece_id, rotation).
    cell_choices = {}  # cell -> list of (b, pid, rot)
    for c in range(W * H):
        cell_choices[c] = []
        for b in range(N):
            if c in boards[b]:
                pid, rot = boards[b][c]
                cell_choices[c].append((b, pid, rot))
        if not cell_choices[c]:
            # No basin placed at this cell — drop from optimisation.
            del cell_choices[c]

    # For each candidate (c, b, pid, rot), pre-compute the rotated edges.
    cell_edges = {}  # (c, b) -> (t, r, b_edge, l)
    for c, choices in cell_choices.items():
        for b, pid, rot in choices:
            if pid in pieces:
                cell_edges[(c, b)] = rotate_edges(pieces[pid], rot)

    # For each pair of adjacent cells (c1, c2) and each pair of basin
    # choices (b1, b2), pre-compute whether the edge matches.
    horizontal_matches = {}  # (c, b1, b2) -> 1 if c.right == (c+1).left match
    vertical_matches = {}
    for c, choices in cell_choices.items():
        x = c % W
        y = c // W
        if x + 1 < W and (c + 1) in cell_choices:
            for b1, _, _ in choices:
                e1 = cell_edges.get((c, b1))
                if e1 is None:
                    continue
                for b2, _, _ in cell_choices[c + 1]:
                    e2 = cell_edges.get((c + 1, b2))
                    if e2 is None:
                        continue
                    # right of c1 == left of c2, both non-border
                    if e1[1] == e2[3] and e1[1] != 0:
                        horizontal_matches[(c, b1, b2)] = 1
        if y + 1 < H and (c + W) in cell_choices:
            for b1, _, _ in choices:
                e1 = cell_edges.get((c, b1))
                if e1 is None:
                    continue
                for b2, _, _ in cell_choices[c + W]:
                    e2 = cell_edges.get((c + W, b2))
                    if e2 is None:
                        continue
                    # bottom of c1 == top of c2
                    if e1[2] == e2[0] and e1[2] != 0:
                        vertical_matches[(c, b1, b2)] = 1

    # Now build the MIP.
    import pulp
    prob = pulp.LpProblem("basin_mix", pulp.LpMaximize)

    # x[c, b] = 1 if cell c uses basin b's placement.
    x = {}
    for c, choices in cell_choices.items():
        for b, _, _ in choices:
            x[(c, b)] = pulp.LpVariable(f"x_{c}_{b}", cat="Binary")

    # y_h[c, b1, b2] = product term — edge match at right edge of c.
    y_h = {}
    for (c, b1, b2) in horizontal_matches:
        y_h[(c, b1, b2)] = pulp.LpVariable(f"yh_{c}_{b1}_{b2}", cat="Binary")
    y_v = {}
    for (c, b1, b2) in vertical_matches:
        y_v[(c, b1, b2)] = pulp.LpVariable(f"yv_{c}_{b1}_{b2}", cat="Binary")

    # Constraint: exactly one basin per cell.
    for c, choices in cell_choices.items():
        prob += pulp.lpSum(x[(c, b)] for b, _, _ in choices) == 1, f"cell_{c}_one"

    # Linking constraints: y_h <= x[c, b1], y_h <= x[c+1, b2], y_h >= x[c,b1] + x[c+1,b2] - 1.
    for (c, b1, b2), _ in horizontal_matches.items():
        prob += y_h[(c, b1, b2)] <= x[(c, b1)], f"yh_lo1_{c}_{b1}_{b2}"
        prob += y_h[(c, b1, b2)] <= x[(c + 1, b2)], f"yh_lo2_{c}_{b1}_{b2}"
    for (c, b1, b2), _ in vertical_matches.items():
        prob += y_v[(c, b1, b2)] <= x[(c, b1)], f"yv_lo1_{c}_{b1}_{b2}"
        prob += y_v[(c, b1, b2)] <= x[(c + W, b2)], f"yv_lo2_{c}_{b1}_{b2}"

    # Piece-uniqueness constraint: each piece can appear at most once total.
    # For each piece pid, find all (c, b) such that the placement at (c, b)
    # uses that piece.
    from collections import defaultdict
    piece_uses = defaultdict(list)  # pid -> list of (c, b)
    for c, choices in cell_choices.items():
        for b, pid, _ in choices:
            piece_uses[pid].append((c, b))
    for pid, uses in piece_uses.items():
        if len(uses) > 1:
            # Each cell that uses pid: at most one such cell can have x=1.
            prob += pulp.lpSum(x[(c, b)] for (c, b) in uses) <= 1, f"piece_{pid}_unique"

    # Objective: maximise matched edges = sum of y vars.
    prob += pulp.lpSum(y_h.values()) + pulp.lpSum(y_v.values())

    print(f"Built MIP: {len(x)} x-vars, {len(y_h)+len(y_v)} y-vars, "
          f"{len(prob.constraints)} constraints")

    # Solve.
    solver = pulp.PULP_CBC_CMD(timeLimit=120, msg=True)
    prob.solve(solver)

    print(f"\nStatus: {pulp.LpStatus[prob.status]}")
    print(f"Objective: {pulp.value(prob.objective)}")

    # Decode the solution: which basin was chosen at each cell?
    basin_counts = [0] * N
    for (c, b), var in x.items():
        if var.value() and var.value() > 0.5:
            basin_counts[b] += 1
    print(f"Basin selection counts: {basin_counts}")


if __name__ == "__main__":
    main()
