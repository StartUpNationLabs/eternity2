#!/usr/bin/env python3
"""Vol-122 K8 — Targeted Interior MIP (TIMF).

NEW INVENTION: given a full board, FIX the 60 border cells, then solve
a MIP that finds the integer-optimal interior-piece-rotation assignment
maximizing matched edges (interior-interior + interior-boundary).

This answers: "given the boundary, what's the integer ceiling of the
interior arrangement?"

For our perm0_444 board, this measures the integer-optimal interior
score (currently 329 II + 55 IB = 384). If MIP gives 354 II + 55 IB,
our ALNS just didn't search enough. If MIP gives only 330 II, the
basin is structurally limited.
"""

from __future__ import annotations
import json
import sys
from collections import defaultdict
from pathlib import Path
from time import time

import pulp


def parse_color(s):
    v = int(s.strip(), 2)
    return 0 if v == 65535 else v

def load_pieces():
    pieces = []
    with open("../data/puzzles/size_16_official_eternity.csv") as f:
        lines = [l.strip() for l in f if l.strip()]
    pid = 0
    for line in lines[1:]:
        cols = line.split(',')
        if len(cols) >= 4:
            try:
                pieces.append(tuple(parse_color(cols[i]) for i in range(4)))
            except ValueError: pass
    return pieces

def rotate(edges, rot):
    return tuple(edges[(i - rot) % 4] for i in range(4))


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} BOARD.json [TIME_LIMIT_SECS=600]")
        sys.exit(1)
    board_path = Path(sys.argv[1])
    time_limit = int(sys.argv[2]) if len(sys.argv) > 2 else 600

    pieces = load_pieces()
    side = 16
    n_pieces = len(pieces)

    with open(board_path) as f:
        d = json.load(f)
    placed = {e['pos']: (e['piece_id'], e['rotation']) for e in d.get('placement', []) if e is not None}
    print(f"loaded: {board_path.name}, {len(placed)} placed cells")

    # Border cells (fixed): 60 positions
    border_pos = []
    for r in range(side):
        for c in range(side):
            if r in (0, side - 1) or c in (0, side - 1):
                border_pos.append(r * side + c)
    interior_pos = [p for p in range(side * side) if p not in border_pos]
    print(f"border cells (fixed): {len(border_pos)}, interior cells (MIP variables): {len(interior_pos)}")

    used_border_pids = {placed[pos][0] for pos in border_pos if pos in placed}
    interior_pids = [pid for pid in range(n_pieces) if pid not in used_border_pids]
    print(f"interior pieces available: {len(interior_pids)}")

    # Build feasible (cell, piece, rotation) triples
    triples = []
    for pos in interior_pos:
        for pid in interior_pids:
            for rot in range(4):
                e = rotate(pieces[pid], rot)
                # Interior cells: all 4 sides must be non-BORDER (color != 0)
                if any(c == 0 for c in e):
                    continue
                triples.append((pos, pid, rot))
    print(f"feasible triples: {len(triples)}")

    # LP/MIP setup
    prob = pulp.LpProblem("interior_mip", pulp.LpMaximize)
    x = {}
    for (pos, pid, rot) in triples:
        x[(pos, pid, rot)] = pulp.LpVariable(f"x_{pos}_{pid}_{rot}", cat='Binary')

    # Constraint: each cell placed exactly once
    print("adding cell constraints...")
    cell_triples = defaultdict(list)
    for t in triples:
        cell_triples[t[0]].append(t)
    for pos in interior_pos:
        terms = [x[t] for t in cell_triples[pos]]
        prob += pulp.lpSum(terms) == 1, f"cell_{pos}"

    # Constraint: each piece used at most once
    print("adding piece constraints...")
    piece_triples = defaultdict(list)
    for t in triples:
        piece_triples[t[1]].append(t)
    for pid in interior_pids:
        terms = [x[t] for t in piece_triples[pid]]
        prob += pulp.lpSum(terms) <= 1, f"piece_{pid}"

    # Objective: count matched adjacencies
    # For each adjacency (pos1, pos2), define y_{(pos1, pos2)} = match indicator.
    # y_{(pos1, pos2)} ≤ sum of x[pos1, p, r] with color c on facing side
    # AND
    # y_{(pos1, pos2)} ≤ sum of x[pos2, p, r] with color c on facing side
    # for matching color c.

    # Cleaner: enumerate (adjacency, color, both-pieces-fit) → matched bool
    # For each adjacency a between pos1 and pos2:
    #   for each color k:
    #     y_{a, k} = pulp.LpVariable(..., cat='Binary')
    #     y_{a, k} ≤ sum of x[pos1, p1, r1] where piece p1 in rot r1 shows color k on facing side
    #     y_{a, k} ≤ sum of x[pos2, p2, r2] where piece p2 in rot r2 shows color k on facing side
    #     (only one color per adjacency: sum_k y_{a,k} ≤ 1)
    # objective = sum y_{a, k}

    # First enumerate adjacencies
    adjs = []
    # interior-interior: between adjacent interior cells
    for r in range(1, side - 1):
        for c in range(1, side - 1):
            pos = r * side + c
            if c < side - 2:  # has right interior neighbor
                adjs.append((pos, 1, pos + 1, 3))  # my right ↔ neighbor left
            if r < side - 2:  # has bottom interior neighbor
                adjs.append((pos, 2, pos + side, 0))
    # interior-boundary: interior cell + border cell
    for r in range(1, side - 1):
        for c in range(1, side - 1):
            pos = r * side + c
            # if r == 1: north neighbor is border (row 0)
            # but the BORDER cell is fixed; we encode its color as a constant.
            pass  # handled below as a different constraint type

    print(f"interior-interior adjacencies: {len(adjs)}")

    # For interior-boundary, the boundary side has a FIXED color (from placed border).
    # So the IB constraint is simpler: for each (interior_cell, side, required_color),
    # we count matches via: y_{ib,_} = sum of x[interior_cell, p, r] where piece shows required_color on side.
    ib_constraints = []  # (interior_pos, side, required_color)
    for c in range(1, side - 1):
        # top border at (0, c) has bottom edge facing interior cell (1, c)
        bpos = c
        bpid, brot = placed[bpos]
        be = rotate(pieces[bpid], brot)
        ib_constraints.append((1 * side + c, 0, be[2]))  # interior cell (1, c) TOP side must = border's BOTTOM
    for c in range(1, side - 1):
        # bottom border
        bpos = side * (side - 1) + c
        bpid, brot = placed[bpos]
        be = rotate(pieces[bpid], brot)
        ib_constraints.append(((side - 2) * side + c, 2, be[0]))
    for r in range(1, side - 1):
        bpos = r * side + (side - 1)
        bpid, brot = placed[bpos]
        be = rotate(pieces[bpid], brot)
        ib_constraints.append((r * side + (side - 2), 1, be[3]))
    for r in range(1, side - 1):
        bpos = r * side
        bpid, brot = placed[bpos]
        be = rotate(pieces[bpid], brot)
        ib_constraints.append((r * side + 1, 3, be[1]))

    print(f"interior-boundary constraints: {len(ib_constraints)}")

    # Create y vars for II
    print("creating y variables...")
    y = {}
    n_y = 0
    for (pos1, s1, pos2, s2) in adjs:
        # Possible colors at this adjacency = colors a piece can present on s1, restricted to non-zero
        # Just enumerate triples filtering by color on s1
        colors_at_pos1_s1 = set()
        for t in cell_triples[pos1]:
            (_, pid, rot) = t
            colors_at_pos1_s1.add(rotate(pieces[pid], rot)[s1])
        colors_at_pos2_s2 = set()
        for t in cell_triples[pos2]:
            (_, pid, rot) = t
            colors_at_pos2_s2.add(rotate(pieces[pid], rot)[s2])
        common_colors = colors_at_pos1_s1 & colors_at_pos2_s2
        common_colors.discard(0)
        for k in common_colors:
            yv = pulp.LpVariable(f"y_{pos1}_{s1}_{pos2}_{s2}_{k}", cat='Binary')
            y[(pos1, s1, pos2, s2, k)] = yv
            n_y += 1
        # one-color-per-adj constraint
        if common_colors:
            prob += pulp.lpSum([y[(pos1, s1, pos2, s2, k)] for k in common_colors]) <= 1
    print(f"y variables (II): {n_y}")

    # Add y ≤ sum x (for each side)
    print("adding y ≤ x constraints...")
    for (pos1, s1, pos2, s2, k) in y:
        # y ≤ sum of x[pos1, p, r] where piece shows color k on side s1
        terms1 = [x[t] for t in cell_triples[pos1] if rotate(pieces[t[1]], t[2])[s1] == k]
        prob += y[(pos1, s1, pos2, s2, k)] <= pulp.lpSum(terms1) if terms1 else 0
        terms2 = [x[t] for t in cell_triples[pos2] if rotate(pieces[t[1]], t[2])[s2] == k]
        prob += y[(pos1, s1, pos2, s2, k)] <= pulp.lpSum(terms2) if terms2 else 0

    # IB: similar y_ib vars
    print("adding IB indicators...")
    y_ib = {}
    for (pos, side_idx, req_color) in ib_constraints:
        if req_color == 0:
            continue  # boundary side is BORDER; no match possible (interior pieces have no BORDER edge)
        terms = [x[t] for t in cell_triples[pos] if rotate(pieces[t[1]], t[2])[side_idx] == req_color]
        if terms:
            yv = pulp.LpVariable(f"yib_{pos}_{side_idx}_{req_color}", cat='Binary')
            y_ib[(pos, side_idx, req_color)] = yv
            prob += yv <= pulp.lpSum(terms)

    print(f"y_ib variables: {len(y_ib)}")

    # Objective
    obj_terms = list(y.values()) + list(y_ib.values())
    prob += pulp.lpSum(obj_terms)
    print(f"objective terms: {len(obj_terms)}")
    print(f"total constraints: {len(prob.constraints)}")
    print(f"total variables: {len(prob.variables())}")

    # Solve
    print(f"\nsolving MIP (time limit {time_limit}s)...")
    t0 = time()
    solver = pulp.HiGHS(msg=True, timeLimit=time_limit, threads=4)
    prob.solve(solver)
    elapsed = time() - t0
    status = pulp.LpStatus[prob.status]
    obj = pulp.value(prob.objective)
    print(f"\nstatus: {status}")
    print(f"objective (II + IB matches): {obj}")
    print(f"+ 60 BB = total: {(obj or 0) + 60}")
    print(f"elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
