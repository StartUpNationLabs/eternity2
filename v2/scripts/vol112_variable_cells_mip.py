#!/usr/bin/env python3
"""Vol-112 T2 — variable-cells MIP.

Building on T1's basin-mix MIP refutation: instead of restricting
each cell to OBSERVED basin placements, allow:
- The 3 invariant cells: pinned to the unique placement.
- The 212 "swap pair" cells: choose between the 2 observed placements.
- The 24 fully-variable cells: choose ANY (piece, rotation), subject
  to piece-uniqueness with the rest.

The cell space is largest at the 24 variable cells. Piece-uniqueness
constraints connect them to the 232 constrained cells (a piece used
in a constrained cell can't be reused in a variable cell).

Optimisation: maximise matched edges. If MIP optimum > 459, we've
broken the 459 ceiling for the basin-skeleton-anchored search space.
"""

import csv
import json
import sys
from collections import defaultdict
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
    ap.add_argument("--time-limit", type=int, default=300)
    args = ap.parse_args()

    pieces = load_puzzle(args.puzzle)
    boards = [load_board(p) for p in args.basins]
    print(f"loaded {len(boards)} basins, {len(pieces)} pieces")

    W, H = 16, 16

    # Categorize cells by variability across basins.
    cell_choices = defaultdict(set)  # cell -> set of (pid, rot)
    for b in boards:
        for c, (pid, rot) in b.items():
            cell_choices[c].add((pid, rot))

    invariant = [c for c, s in cell_choices.items() if len(s) == 1]
    variable = [c for c, s in cell_choices.items() if len(s) == len(boards)]
    semi = [c for c, s in cell_choices.items() if 1 < len(s) < len(boards)]

    print(f"cell categories: invariant={len(invariant)}, semi={len(semi)}, fully_variable={len(variable)}")

    # Cells we treat as "anchored" (≤ 2 placements): invariant + semi (and we cap at observed choices).
    # Cells we treat as "free": fully variable (any (pid, rot)).

    # Pieces already committed at invariant cells (always used regardless).
    invariant_pieces = set()
    for c in invariant:
        for pid, rot in cell_choices[c]:
            invariant_pieces.add(pid)
            break

    # For semi cells, build candidate (pid, rot) set.
    # For variable cells, candidates = all pieces - those that have invariant placements
    # (we could also exclude pieces only ever appearing in basins, but that's restrictive).
    # Actually for max flexibility, allow ANY piece at variable cells. The piece-uniqueness
    # constraint handles conflicts.

    # Compute per (cell, pid, rot) the rotated edges.
    cell_edges = {}  # (c, pid, rot) -> (t, r, b, l)

    # For all cells in invariant ∪ semi, candidates are the observed (pid, rot) set.
    candidates_by_cell = {}
    for c in invariant + semi:
        candidates_by_cell[c] = sorted(cell_choices[c])
        for (pid, rot) in cell_choices[c]:
            cell_edges[(c, pid, rot)] = rotate_edges(pieces[pid], rot)
    # For fully variable cells, candidates = all (pid, rot).
    # But pieces in invariant cells are FIXED — exclude them.
    # Pieces in semi cells are POTENTIALLY used — include all (pid, rot) but
    # piece-uniqueness will resolve.
    # For tractability, restrict variable cells to pieces NOT in invariant cells
    # (those are definitely used elsewhere).
    available_pieces = [pid for pid in pieces.keys() if pid not in invariant_pieces]
    print(f"available pieces for variable cells: {len(available_pieces)} (excluded {len(invariant_pieces)} invariant)")

    # Restrict to the union of (pid, rot) seen at any variable cell in any
    # basin — these are the "free pieces" identified by vol-111. This keeps
    # the MIP tractable while still allowing more flexibility than the 4-basin
    # mix (which used only 4 choices per cell).
    free_pieces = set()
    for c in variable:
        for (pid, rot) in cell_choices[c]:
            free_pieces.add(pid)
    print(f"free pieces (used at any variable cell in any basin): {len(free_pieces)}")

    for c in variable:
        cands = []
        for pid in sorted(free_pieces):
            if pid in invariant_pieces:
                continue
            for rot in range(4):
                cands.append((pid, rot))
                cell_edges[(c, pid, rot)] = rotate_edges(pieces[pid], rot)
        candidates_by_cell[c] = cands

    print(f"per-cell candidate counts: invariant={1}, semi={len(boards)} (≤{len(boards)}), variable={len(available_pieces) * 4}")

    # Build MIP.
    import pulp
    prob = pulp.LpProblem("variable_cells_mix", pulp.LpMaximize)

    # x[c, pid, rot] = 1 if cell c uses (pid, rot).
    x = {}
    for c, cands in candidates_by_cell.items():
        for (pid, rot) in cands:
            x[(c, pid, rot)] = pulp.LpVariable(f"x_{c}_{pid}_{rot}", cat="Binary")

    # Exactly one placement per cell.
    for c, cands in candidates_by_cell.items():
        prob += pulp.lpSum(x[(c, pid, rot)] for (pid, rot) in cands) == 1, f"cell_{c}_one"

    # Piece-uniqueness: each piece used at most once across all cells.
    piece_uses = defaultdict(list)
    for (c, pid, rot), var in x.items():
        piece_uses[pid].append(var)
    for pid, uses in piece_uses.items():
        prob += pulp.lpSum(uses) <= 1, f"piece_{pid}_unique"

    # Edge-match variables.
    # For each adjacent pair (c1, c2) and each (c1, p1, r1, c2, p2, r2)
    # where the edges match, add a y var.
    y_h = {}
    y_v = {}
    for c1 in candidates_by_cell:
        x1 = c1 % W
        y1 = c1 // W
        if x1 + 1 < W and (c1 + 1) in candidates_by_cell:
            c2 = c1 + 1
            for (p1, r1) in candidates_by_cell[c1]:
                e1 = cell_edges.get((c1, p1, r1))
                if e1 is None: continue
                if e1[1] == 0: continue  # right edge is BORDER; no internal match
                for (p2, r2) in candidates_by_cell[c2]:
                    e2 = cell_edges.get((c2, p2, r2))
                    if e2 is None: continue
                    if e1[1] == e2[3]:
                        key = (c1, p1, r1, p2, r2)
                        y_h[key] = pulp.LpVariable(f"yh_{c1}_{p1}_{r1}_{p2}_{r2}", cat="Binary")
                        prob += y_h[key] <= x[(c1, p1, r1)]
                        prob += y_h[key] <= x[(c2, p2, r2)]
        if y1 + 1 < H and (c1 + W) in candidates_by_cell:
            c2 = c1 + W
            for (p1, r1) in candidates_by_cell[c1]:
                e1 = cell_edges.get((c1, p1, r1))
                if e1 is None: continue
                if e1[2] == 0: continue
                for (p2, r2) in candidates_by_cell[c2]:
                    e2 = cell_edges.get((c2, p2, r2))
                    if e2 is None: continue
                    if e1[2] == e2[0]:
                        key = (c1, p1, r1, p2, r2)
                        y_v[key] = pulp.LpVariable(f"yv_{c1}_{p1}_{r1}_{p2}_{r2}", cat="Binary")
                        prob += y_v[key] <= x[(c1, p1, r1)]
                        prob += y_v[key] <= x[(c2, p2, r2)]

    # Objective.
    prob += pulp.lpSum(y_h.values()) + pulp.lpSum(y_v.values())

    print(f"MIP: {len(x)} x-vars, {len(y_h) + len(y_v)} y-vars, "
          f"{len(prob.constraints)} constraints")

    # Solve.
    solver = pulp.PULP_CBC_CMD(timeLimit=args.time_limit, msg=True)
    prob.solve(solver)

    print(f"\nStatus: {pulp.LpStatus[prob.status]}")
    print(f"Objective: {pulp.value(prob.objective)}")


if __name__ == "__main__":
    main()
