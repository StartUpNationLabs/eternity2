#!/usr/bin/env python3
"""Vol-119 — region-restricted basin-mix MIP.

Halo-K cluster repair using ONLY corpus's (piece, rot) options for the
free cells. The other cells are pinned from one base basin.

Why this might work where vol-44/95/100 didn't:
- vol-44 used the FULL puzzle (all 196 pieces × 4 rotations) for the
  free region. Larger search space.
- This restricts to corpus options (~5 (pid, rot) per cell). MUCH
  smaller MIP — solves in seconds even for halo-3, while exploring
  the same OBSERVED basin variations.
- If the corpus has a structurally novel piece-arrangement nobody's
  ALNS-explored, the MIP will find it.

Usage:
    vol119_region_basin_mix_mip.py <puzzle> <base_board> <corpus1> <corpus2> ... \\
        --halo 2 --time-limit 300 [--out out.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


W, H = 16, 16


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


def find_mismatch_cells(board, pieces):
    weak = []
    for pos in board:
        pid, rot = board[pos]
        x, y = pos % W, pos // W
        e = rotate_edges(pieces[pid], rot)
        cnt = 0
        n_edges = 0
        if x < W - 1 and (pos + 1) in board:
            npid, nrot = board[pos + 1]
            ne = rotate_edges(pieces[npid], nrot)
            n_edges += 1
            if e[1] == ne[3] and not (e[1] == 0 and ne[3] == 0):
                cnt += 1
        if x > 0 and (pos - 1) in board:
            npid, nrot = board[pos - 1]
            ne = rotate_edges(pieces[npid], nrot)
            n_edges += 1
            if e[3] == ne[1] and not (e[3] == 0 and ne[1] == 0):
                cnt += 1
        if y < H - 1 and (pos + W) in board:
            npid, nrot = board[pos + W]
            ne = rotate_edges(pieces[npid], nrot)
            n_edges += 1
            if e[2] == ne[0] and not (e[2] == 0 and ne[0] == 0):
                cnt += 1
        if y > 0 and (pos - W) in board:
            npid, nrot = board[pos - W]
            ne = rotate_edges(pieces[npid], nrot)
            n_edges += 1
            if e[0] == ne[2] and not (e[0] == 0 and ne[2] == 0):
                cnt += 1
        if cnt < n_edges:
            weak.append(pos)
    return weak


def grid_neighbors(p):
    x, y = p % W, p // W
    out = []
    if x > 0: out.append(p - 1)
    if x < W - 1: out.append(p + 1)
    if y > 0: out.append(p - W)
    if y < H - 1: out.append(p + W)
    return out


def matched_edges(board, pieces):
    matched = 0
    for pos, (pid, rot) in board.items():
        x, y = pos % W, pos // W
        e = rotate_edges(pieces[pid], rot)
        if x < W - 1 and (pos + 1) in board:
            npid, nrot = board[pos + 1]
            ne = rotate_edges(pieces[npid], nrot)
            if e[1] == ne[3] and not (e[1] == 0 and ne[3] == 0):
                matched += 1
        if y < H - 1 and (pos + W) in board:
            npid, nrot = board[pos + W]
            ne = rotate_edges(pieces[npid], nrot)
            if e[2] == ne[0] and not (e[2] == 0 and ne[0] == 0):
                matched += 1
    return matched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle")
    ap.add_argument("base_board", help="board to repair (pinned outside free region)")
    ap.add_argument("corpus", nargs="*", help="other boards (cell-choice source)")
    ap.add_argument("--halo", type=int, default=2)
    ap.add_argument("--time-limit", type=int, default=300)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    pieces = load_puzzle(args.puzzle)
    base = load_board(Path(args.base_board))
    print(f"# base score: {matched_edges(base, pieces)}/480", file=sys.stderr)

    # Find mismatch + halo region.
    mismatch = set(find_mismatch_cells(base, pieces))
    free = set(mismatch)
    for _ in range(args.halo):
        snapshot = list(free)
        for p in snapshot:
            free.update(grid_neighbors(p))
    free = sorted(free)
    print(f"# mismatch cells: {len(mismatch)}, halo-{args.halo} free region: {len(free)} cells",
          file=sys.stderr)

    # Build cell-choice set per free cell from corpus
    corpus_boards = [base] + [load_board(Path(p)) for p in args.corpus]
    cell_choices = defaultdict(set)  # pos -> {(pid, rot)}
    for b in corpus_boards:
        for pos, (pid, rot) in b.items():
            if pos in free:
                cell_choices[pos].add((pid, rot))

    n_options = sum(len(s) for s in cell_choices.values())
    print(f"# corpus cell-choice options in free region: {n_options} total, "
          f"mean {n_options/max(1, len(free)):.1f} per cell", file=sys.stderr)

    # Pinned cells (outside free): use base's (pid, rot).
    pinned_pids = set()
    pinned_placement = {}
    for pos, val in base.items():
        if pos not in free:
            pinned_placement[pos] = val
            pinned_pids.add(val[0])

    # MIP: x[(pos, pid, rot)] = 1 if we put this piece at this pos.
    import pulp
    prob = pulp.LpProblem("region_basin_mix", pulp.LpMaximize)

    x = {}
    for pos, options in cell_choices.items():
        for (pid, rot) in options:
            if pid in pinned_pids:
                # piece already pinned outside; can't use it here
                continue
            x[(pos, pid, rot)] = pulp.LpVariable(f"x_{pos}_{pid}_{rot}", cat="Binary")

    # Edge match indicators between free cells and adjacency to pinned cells.
    # y_h[(pos1, pos2, pid1, rot1, pid2, rot2)] = 1 if both placed AND edge matches
    # For pinned cells, the "choice" is fixed; embed it as known data.

    y_vars = {}
    edge_count_const = 0  # matched edges that are entirely pinned (constant)

    def edges_match(pid1, rot1, side1, pid2, rot2, side2):
        """side1, side2 are 0=top,1=right,2=bottom,3=left."""
        e1 = rotate_edges(pieces[pid1], rot1)
        e2 = rotate_edges(pieces[pid2], rot2)
        return e1[side1] == e2[side2] and not (e1[side1] == 0 and e2[side2] == 0)

    # Iterate over all adjacent cell pairs
    for pos in range(W * H):
        if pos not in free and pos not in pinned_placement:
            continue
        x_col = pos % W
        # right neighbor
        if x_col < W - 1:
            npos = pos + 1
            if npos not in free and npos not in pinned_placement:
                continue
            if pos in free and npos in free:
                # both free: y depends on both x's
                for (pid1, rot1) in cell_choices[pos]:
                    if pid1 in pinned_pids:
                        continue
                    for (pid2, rot2) in cell_choices[npos]:
                        if pid2 in pinned_pids:
                            continue
                        if pid1 == pid2:
                            continue
                        if edges_match(pid1, rot1, 1, pid2, rot2, 3):
                            v = pulp.LpVariable(f"y_h_{pos}_{pid1}_{rot1}_{pid2}_{rot2}",
                                                cat="Binary")
                            prob += v <= x[(pos, pid1, rot1)]
                            prob += v <= x[(npos, pid2, rot2)]
                            y_vars[("h", pos, pid1, rot1, pid2, rot2)] = v
            elif pos in free:
                npid, nrot = pinned_placement[npos]
                # y depends only on x at pos
                for (pid1, rot1) in cell_choices[pos]:
                    if pid1 in pinned_pids:
                        continue
                    if pid1 == npid:
                        continue  # piece-uniqueness
                    if edges_match(pid1, rot1, 1, npid, nrot, 3):
                        v = pulp.LpVariable(f"y_h_{pos}_{pid1}_{rot1}_PINNED",
                                            cat="Binary")
                        prob += v <= x[(pos, pid1, rot1)]
                        y_vars[("h", pos, pid1, rot1, "pinned")] = v
            elif npos in free:
                pid1, rot1 = pinned_placement[pos]
                for (pid2, rot2) in cell_choices[npos]:
                    if pid2 in pinned_pids:
                        continue
                    if pid1 == pid2:
                        continue
                    if edges_match(pid1, rot1, 1, pid2, rot2, 3):
                        v = pulp.LpVariable(f"y_h_PINNED_{npos}_{pid2}_{rot2}",
                                            cat="Binary")
                        prob += v <= x[(npos, pid2, rot2)]
                        y_vars[("h", "pinned", npos, pid2, rot2)] = v
            else:
                # both pinned: edge is constant
                pid1, rot1 = pinned_placement[pos]
                pid2, rot2 = pinned_placement[npos]
                if edges_match(pid1, rot1, 1, pid2, rot2, 3):
                    edge_count_const += 1
        # bottom neighbor
        y_row = pos // W
        if y_row < H - 1:
            npos = pos + W
            if npos not in free and npos not in pinned_placement:
                continue
            if pos in free and npos in free:
                for (pid1, rot1) in cell_choices[pos]:
                    if pid1 in pinned_pids:
                        continue
                    for (pid2, rot2) in cell_choices[npos]:
                        if pid2 in pinned_pids:
                            continue
                        if pid1 == pid2:
                            continue
                        if edges_match(pid1, rot1, 2, pid2, rot2, 0):
                            v = pulp.LpVariable(f"y_v_{pos}_{pid1}_{rot1}_{pid2}_{rot2}",
                                                cat="Binary")
                            prob += v <= x[(pos, pid1, rot1)]
                            prob += v <= x[(npos, pid2, rot2)]
                            y_vars[("v", pos, pid1, rot1, pid2, rot2)] = v
            elif pos in free:
                npid, nrot = pinned_placement[npos]
                for (pid1, rot1) in cell_choices[pos]:
                    if pid1 in pinned_pids:
                        continue
                    if pid1 == npid:
                        continue
                    if edges_match(pid1, rot1, 2, npid, nrot, 0):
                        v = pulp.LpVariable(f"y_v_{pos}_{pid1}_{rot1}_PINNED",
                                            cat="Binary")
                        prob += v <= x[(pos, pid1, rot1)]
                        y_vars[("v", pos, pid1, rot1, "pinned")] = v
            elif npos in free:
                pid1, rot1 = pinned_placement[pos]
                for (pid2, rot2) in cell_choices[npos]:
                    if pid2 in pinned_pids:
                        continue
                    if pid1 == pid2:
                        continue
                    if edges_match(pid1, rot1, 2, pid2, rot2, 0):
                        v = pulp.LpVariable(f"y_v_PINNED_{npos}_{pid2}_{rot2}",
                                            cat="Binary")
                        prob += v <= x[(npos, pid2, rot2)]
                        y_vars[("v", "pinned", npos, pid2, rot2)] = v
            else:
                pid1, rot1 = pinned_placement[pos]
                pid2, rot2 = pinned_placement[npos]
                if edges_match(pid1, rot1, 2, pid2, rot2, 0):
                    edge_count_const += 1

    # Constraint: exactly one (pid, rot) per free cell.
    for pos in free:
        opts = [(pid, rot) for (pid, rot) in cell_choices[pos] if pid not in pinned_pids]
        if not opts:
            print(f"WARN: free cell {pos} has no non-pinned options", file=sys.stderr)
            continue
        prob += pulp.lpSum(x[(pos, pid, rot)] for (pid, rot) in opts) == 1, f"cell_{pos}_one"

    # Constraint: each piece used at most once across free cells.
    piece_uses = defaultdict(list)
    for (pos, pid, rot), _ in x.items():
        piece_uses[pid].append((pos, pid, rot))
    for pid, uses in piece_uses.items():
        if len(uses) > 1:
            prob += pulp.lpSum(x[u] for u in uses) <= 1, f"piece_{pid}_unique"

    prob += pulp.lpSum(y_vars.values()) + edge_count_const

    print(f"# Built MIP: {len(x)} x-vars, {len(y_vars)} y-vars, "
          f"{len(prob.constraints)} constraints, "
          f"pinned-edge constant = {edge_count_const}", file=sys.stderr)

    solver = pulp.PULP_CBC_CMD(timeLimit=args.time_limit, msg=True)
    prob.solve(solver)

    status = pulp.LpStatus[prob.status]
    objective = pulp.value(prob.objective)
    print(f"\nStatus: {status}")
    print(f"Objective: {objective}")

    # Extract solution
    new_board = dict(pinned_placement)
    for (pos, pid, rot), var in x.items():
        if var.value() and var.value() > 0.5:
            new_board[pos] = (pid, rot)

    final_score = matched_edges(new_board, pieces)
    base_score = matched_edges(base, pieces)
    print(f"# base score: {base_score}, final score: {final_score}, "
          f"Δ = {final_score - base_score:+d}")

    if args.out:
        placement = []
        for pos in sorted(new_board):
            pid, rot = new_board[pos]
            placement.append({"pos": pos, "piece_id": pid, "rotation": rot})
        doc = {
            "placement": placement,
            "metadata": {
                "source": "vol119_region_basin_mix_mip",
                "halo": args.halo,
                "free_size": len(free),
                "mip_objective": objective,
                "mip_status": status,
                "base": args.base_board,
            },
        }
        with open(args.out, "w") as f:
            json.dump(doc, f, indent=2)
        print(f"# wrote: {args.out}")


if __name__ == "__main__":
    main()
