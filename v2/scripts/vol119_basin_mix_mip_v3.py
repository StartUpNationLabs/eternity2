#!/usr/bin/env python3
"""Vol-119 T2 v3 — basin-mix MIP with warm-start + objective floor.

Improvements over v2:
- WARM START: initialize x variables with values from one full basin
  (binds CBC's branch from a valid 459 immediately).
- OBJECTIVE FLOOR: --min-score N adds constraint sum(y) >= N, focuses
  branch on solutions ≥ N.
- HiGHS solver alternative via --solver highs.

Usage:
    vol119_basin_mix_mip_v3.py <puzzle> <board1.json> ... \\
        --warm-from 0 --min-score 460 --time-limit 3600 --out out.json
"""

from __future__ import annotations

import argparse
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
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle")
    ap.add_argument("basins", nargs="+")
    ap.add_argument("--out", default=None)
    ap.add_argument("--time-limit", type=int, default=600)
    ap.add_argument("--gap", type=float, default=0.0)
    ap.add_argument("--warm-from", type=int, default=0,
                    help="basin index to use as warm-start (default 0)")
    ap.add_argument("--min-score", type=int, default=0,
                    help="objective floor; adds constraint sum(y) >= min-score")
    ap.add_argument("--solver", choices=["cbc", "highs"], default="cbc")
    args = ap.parse_args()

    pieces = load_puzzle(args.puzzle)
    print(f"loaded {len(pieces)} pieces", file=sys.stderr)

    boards = [load_board(p) for p in args.basins]
    print(f"loaded {len(boards)} basins from:", file=sys.stderr)
    for i, p in enumerate(args.basins):
        print(f"  [{i}] {p}", file=sys.stderr)

    W, H = 16, 16
    N = len(boards)

    cell_choices = {}
    for c in range(W * H):
        cell_choices[c] = []
        for b in range(N):
            if c in boards[b]:
                pid, rot = boards[b][c]
                cell_choices[c].append((b, pid, rot))
        if not cell_choices[c]:
            del cell_choices[c]

    cell_edges = {}
    for c, choices in cell_choices.items():
        for b, pid, rot in choices:
            if pid in pieces:
                cell_edges[(c, b)] = rotate_edges(pieces[pid], rot)

    horizontal_matches = {}
    vertical_matches = {}
    for c, choices in cell_choices.items():
        x_col = c % W
        y_row = c // W
        if x_col + 1 < W and (c + 1) in cell_choices:
            for b1, _, _ in choices:
                e1 = cell_edges.get((c, b1))
                if e1 is None:
                    continue
                for b2, _, _ in cell_choices[c + 1]:
                    e2 = cell_edges.get((c + 1, b2))
                    if e2 is None:
                        continue
                    if e1[1] == e2[3] and e1[1] != 0:
                        horizontal_matches[(c, b1, b2)] = 1
        if y_row + 1 < H and (c + W) in cell_choices:
            for b1, _, _ in choices:
                e1 = cell_edges.get((c, b1))
                if e1 is None:
                    continue
                for b2, _, _ in cell_choices[c + W]:
                    e2 = cell_edges.get((c + W, b2))
                    if e2 is None:
                        continue
                    if e1[2] == e2[0] and e1[2] != 0:
                        vertical_matches[(c, b1, b2)] = 1

    import pulp
    prob = pulp.LpProblem("basin_mix_v3", pulp.LpMaximize)

    x = {}
    for c, choices in cell_choices.items():
        for b, _, _ in choices:
            x[(c, b)] = pulp.LpVariable(f"x_{c}_{b}", cat="Binary")

    y_h = {}
    for (c, b1, b2) in horizontal_matches:
        y_h[(c, b1, b2)] = pulp.LpVariable(f"yh_{c}_{b1}_{b2}", cat="Binary")
    y_v = {}
    for (c, b1, b2) in vertical_matches:
        y_v[(c, b1, b2)] = pulp.LpVariable(f"yv_{c}_{b1}_{b2}", cat="Binary")

    for c, choices in cell_choices.items():
        prob += pulp.lpSum(x[(c, b)] for b, _, _ in choices) == 1, f"cell_{c}_one"

    for (c, b1, b2), _ in horizontal_matches.items():
        prob += y_h[(c, b1, b2)] <= x[(c, b1)], f"yh_lo1_{c}_{b1}_{b2}"
        prob += y_h[(c, b1, b2)] <= x[(c + 1, b2)], f"yh_lo2_{c}_{b1}_{b2}"
    for (c, b1, b2), _ in vertical_matches.items():
        prob += y_v[(c, b1, b2)] <= x[(c, b1)], f"yv_lo1_{c}_{b1}_{b2}"
        prob += y_v[(c, b1, b2)] <= x[(c + W, b2)], f"yv_lo2_{c}_{b1}_{b2}"

    piece_uses = defaultdict(list)
    for c, choices in cell_choices.items():
        for b, pid, _ in choices:
            piece_uses[pid].append((c, b))
    for pid, uses in piece_uses.items():
        if len(uses) > 1:
            prob += pulp.lpSum(x[(c, b)] for (c, b) in uses) <= 1, f"piece_{pid}_unique"

    y_sum = pulp.lpSum(y_h.values()) + pulp.lpSum(y_v.values())
    prob += y_sum  # objective

    if args.min_score > 0:
        prob += y_sum >= args.min_score, "min_score_floor"

    print(f"Built MIP: N={N}, {len(x)} x-vars, {len(y_h)+len(y_v)} y-vars, "
          f"{len(prob.constraints)} constraints", file=sys.stderr)

    # Warm start using basin `args.warm_from`
    wb = args.warm_from
    if 0 <= wb < N:
        for (c, b), var in x.items():
            if b == wb and c in boards[wb]:
                var.setInitialValue(1)
            else:
                var.setInitialValue(0)
        # Set y vars based on adjacent agreement in basin wb
        for (c, b1, b2), var in y_h.items():
            if b1 == wb and b2 == wb:
                var.setInitialValue(1)
            else:
                var.setInitialValue(0)
        for (c, b1, b2), var in y_v.items():
            if b1 == wb and b2 == wb:
                var.setInitialValue(1)
            else:
                var.setInitialValue(0)
        print(f"# warm-start set: basin {wb}", file=sys.stderr)

    if args.solver == "cbc":
        solver = pulp.PULP_CBC_CMD(
            timeLimit=args.time_limit, msg=True, gapRel=args.gap,
            warmStart=True,
        )
    elif args.solver == "highs":
        solver = pulp.HiGHS_CMD(timeLimit=args.time_limit, msg=True, gapRel=args.gap)
    prob.solve(solver)

    status = pulp.LpStatus[prob.status]
    objective = pulp.value(prob.objective)
    print(f"\nStatus: {status}")
    print(f"Objective: {objective}")

    basin_counts = [0] * N
    selected = {}
    for (c, b), var in x.items():
        if var.value() and var.value() > 0.5:
            basin_counts[b] += 1
            selected[c] = b
    print(f"Basin selection counts: {basin_counts}")

    if args.out and selected:
        placement = []
        for c, b in sorted(selected.items()):
            for bb, pid, rot in cell_choices[c]:
                if bb == b:
                    placement.append({"pos": c, "piece_id": pid, "rotation": rot})
                    break
        out_doc = {
            "placement": placement,
            "metadata": {
                "source": "vol119_basin_mix_mip_v3",
                "n_basins": N,
                "mip_objective": objective,
                "mip_status": status,
                "warm_from": wb,
                "min_score": args.min_score,
            },
        }
        with open(args.out, "w") as f:
            json.dump(out_doc, f, indent=2)
        print(f"Wrote mix board: {args.out}")


if __name__ == "__main__":
    main()
