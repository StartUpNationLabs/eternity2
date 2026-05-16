#!/usr/bin/env python3
"""Vol-120 T2 — strict-canonical region MIP.

Same as vol119_region_basin_mix_mip.py but with HARD-PIN of the 5
canonical hints. The MIP must respect:
- pos 34: piece 207, rotation 1
- pos 45: piece 254, rotation 1
- pos 135: piece 138, rotation 0 (center)
- pos 210: piece 180, rotation 1
- pos 221: piece 248, rotation 2

Pieces 207, 254, 138, 180, 248 are then locked at those positions and
NEVER available elsewhere.

If MIP optimum > current strict-canonical record (457 via vol-32
blackwood_mrv), we have a NEW strict-canonical record.

Usage:
    vol120_strict_canonical_region_mip.py <puzzle> <base> <corpus...> --halo K
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

W, H = 16, 16

CANONICAL_HINTS = [
    (34, 207, 1),
    (45, 254, 1),
    (135, 138, 0),
    (210, 180, 1),
    (221, 248, 2),
]


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
    ap.add_argument("base_board")
    ap.add_argument("corpus", nargs="*")
    ap.add_argument("--halo", type=int, default=4)
    ap.add_argument("--time-limit", type=int, default=300)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    pieces = load_puzzle(args.puzzle)
    base = load_board(Path(args.base_board))
    print(f"# base score: {matched_edges(base, pieces)}/480", file=sys.stderr)

    # FORCE base to have canonical hints.
    for (pos, pid, rot) in CANONICAL_HINTS:
        base[pos] = (pid, rot)
    print(f"# base after hint pinning: {matched_edges(base, pieces)}/480", file=sys.stderr)

    # Free region = mismatch + halo, MINUS canonical hint positions.
    mismatch = set(find_mismatch_cells(base, pieces))
    free = set(mismatch)
    for _ in range(args.halo):
        snapshot = list(free)
        for p in snapshot:
            free.update(grid_neighbors(p))
    for (pos, _, _) in CANONICAL_HINTS:
        free.discard(pos)
    free = sorted(free)
    print(f"# free region (halo-{args.halo}, hints excluded): {len(free)} cells", file=sys.stderr)

    # Hint pieces lock: they can ONLY be at their canonical positions.
    hint_pids = {pid for _, pid, _ in CANONICAL_HINTS}

    # Build cell-choices from corpus + filter out hint pieces at non-hint positions.
    corpus_boards = [base] + [load_board(Path(p)) for p in args.corpus]
    cell_choices = defaultdict(set)
    for b in corpus_boards:
        for pos, (pid, rot) in b.items():
            if pos in free:
                if pid not in hint_pids:
                    cell_choices[pos].add((pid, rot))
    print(f"# free cell-choices (excl hint pieces): "
          f"{sum(len(s) for s in cell_choices.values())} total, "
          f"mean {sum(len(s) for s in cell_choices.values())/max(1, len(free)):.1f}/cell",
          file=sys.stderr)

    # Pinned cells outside free: base's (pid, rot).
    pinned_pids = set()
    pinned_placement = {}
    for pos, val in base.items():
        if pos not in free:
            pinned_placement[pos] = val
            pinned_pids.add(val[0])

    # All hint pids are pinned.
    for (pos, pid, rot) in CANONICAL_HINTS:
        pinned_placement[pos] = (pid, rot)
        pinned_pids.add(pid)

    import pulp
    prob = pulp.LpProblem("strict_canonical_region", pulp.LpMaximize)

    x = {}
    for pos, options in cell_choices.items():
        for (pid, rot) in options:
            if pid in pinned_pids:
                continue
            x[(pos, pid, rot)] = pulp.LpVariable(f"x_{pos}_{pid}_{rot}", cat="Binary")

    y_vars = {}
    edge_count_const = 0

    def edges_match(pid1, rot1, side1, pid2, rot2, side2):
        e1 = rotate_edges(pieces[pid1], rot1)
        e2 = rotate_edges(pieces[pid2], rot2)
        return e1[side1] == e2[side2] and not (e1[side1] == 0 and e2[side2] == 0)

    for pos in range(W * H):
        if pos not in free and pos not in pinned_placement:
            continue
        x_col = pos % W
        if x_col < W - 1:
            npos = pos + 1
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
                        if edges_match(pid1, rot1, 1, pid2, rot2, 3):
                            v = pulp.LpVariable(f"y_h_{pos}_{pid1}_{rot1}_{pid2}_{rot2}",
                                                cat="Binary")
                            prob += v <= x[(pos, pid1, rot1)]
                            prob += v <= x[(npos, pid2, rot2)]
                            y_vars[("h", pos, pid1, rot1, pid2, rot2)] = v
            elif pos in free:
                npid, nrot = pinned_placement[npos]
                for (pid1, rot1) in cell_choices[pos]:
                    if pid1 in pinned_pids:
                        continue
                    if pid1 == npid:
                        continue
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
                pid1, rot1 = pinned_placement[pos]
                pid2, rot2 = pinned_placement[npos]
                if edges_match(pid1, rot1, 1, pid2, rot2, 3):
                    edge_count_const += 1
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

    for pos in free:
        opts = [(pid, rot) for (pid, rot) in cell_choices[pos] if pid not in pinned_pids]
        if not opts:
            continue
        prob += pulp.lpSum(x[(pos, pid, rot)] for (pid, rot) in opts) == 1, f"cell_{pos}_one"

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
                "source": "vol120_strict_canonical_region_mip",
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
