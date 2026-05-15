#!/usr/bin/env python3
"""Vol-74 — Concentric Annular Solving (CAS) full pipeline.

Solve all 8 shells iteratively, each via MIP conditioned on
previous shells.

Each shell's cells form a "ring" within the shell-distance band.
For shell k ≥ 1, the cells are at shell_distance == k. They are
a ring of (14 - 2*(k-1)) × (14 - 2*(k-1)) minus the deeper interior.

Generalizes vol74_cas_shell1_mip.py.
"""

import collections
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix


def load_pieces():
    BORDER_RAW = 65535
    pieces = []
    with open("../data/puzzles/size_16_official_eternity.csv") as f:
        size = int(f.readline().strip())
        for idx, line in enumerate(f):
            line = line.strip()
            if not line: continue
            parts = line.split(",")
            def col(s):
                v = int(s.strip(), 2)
                return 0 if v == BORDER_RAW else v
            pieces.append((col(parts[0]), col(parts[1]), col(parts[2]), col(parts[3])))
    return pieces


def rotate(edges, k):
    n, e, s, w = edges
    if k == 0: return (n, e, s, w)
    if k == 1: return (w, n, e, s)
    if k == 2: return (s, w, n, e)
    if k == 3: return (e, s, w, n)


def piece_kind(edges):
    nb = sum(1 for c in edges if c == 0)
    return {0: "interior", 1: "edge", 2: "corner"}.get(nb)


def shell_distance(pos):
    r, c = divmod(pos, 16)
    return min(r, 15 - r, c, 15 - c)


def shell_cells_ring(shell):
    """Return shell-k cells in ring order around the kth ring.

    Shell k cells: r==k or r==15-k or c==k or c==15-k, with all in
    [k, 15-k] (otherwise they'd be deeper).
    """
    if shell == 0:
        # Frame: r==0 or r==15 or c==0 or c==15 (any of those, all in 0..15)
        cells = []
        for c in range(16): cells.append(c)
        for r in range(1, 16): cells.append(r * 16 + 15)
        for c in range(14, -1, -1): cells.append(15 * 16 + c)
        for r in range(14, 0, -1): cells.append(r * 16)
        return cells

    # Shell k: cells in band r∈{k, 15-k} ∪ c∈{k, 15-k}, within bbox [k, 15-k]²
    lo = shell; hi = 15 - shell
    if hi <= lo:
        # Center cells (2×2 or fewer)
        return [r * 16 + c for r in range(lo, hi + 1) for c in range(lo, hi + 1)]
    cells = []
    # Top row of ring: (lo, lo..hi)
    for c in range(lo, hi + 1): cells.append(lo * 16 + c)
    # Right col: (lo+1..hi, hi)
    for r in range(lo + 1, hi + 1): cells.append(r * 16 + hi)
    # Bottom row: (hi, hi-1..lo)
    for c in range(hi - 1, lo - 1, -1): cells.append(hi * 16 + c)
    # Left col: (hi-1..lo+1, lo)
    for r in range(hi - 1, lo, -1): cells.append(r * 16 + lo)
    return cells


def outward_neighbor(pos, shell):
    """For a shell-k cell, return the position of its outward neighbor
    (in shell k-1) and the (out_side, their_side) tuple."""
    r, c = divmod(pos, 16)
    lo = shell; hi = 15 - shell
    if r == lo:
        return ((lo - 1) * 16 + c, 0, 2)  # outward N, neighbor's S faces us
    if r == hi:
        return ((hi + 1) * 16 + c, 2, 0)  # outward S, neighbor's N
    if c == lo:
        return (r * 16 + (lo - 1), 3, 1)  # outward W
    if c == hi:
        return (r * 16 + (hi + 1), 1, 3)  # outward E
    return None  # not on a ring boundary


def solve_shell(shell, frame_placement, pieces, interior_pids, used_pids):
    """Solve shell k given all previous shells fixed in frame_placement."""
    cells_ring = shell_cells_ring(shell)
    available_pids = [p for p in interior_pids if p not in used_pids]
    print(f"\n=== Shell {shell}: {len(cells_ring)} cells, {len(available_pids)} pieces available ===")

    # Enumerate placements
    placements = []
    for pid in available_pids:
        for pos in cells_ring:
            for k in range(4):
                rotated = rotate(pieces[pid], k)
                if 0 in rotated: continue  # no border-color in interior
                placements.append((pid, pos, k, rotated))
    n_x = len(placements)
    print(f"  Placements: {n_x}")
    if n_x == 0:
        print(f"  No placements; shell {shell} empty")
        return frame_placement, 0

    cell_to_p = collections.defaultdict(list)
    piece_to_p = collections.defaultdict(list)
    for idx, (pid, pos, k, _) in enumerate(placements):
        cell_to_p[pos].append(idx)
        piece_to_p[pid].append(idx)

    # Ring edges within shell k
    ring = []
    for i in range(len(cells_ring)):
        p1 = cells_ring[i]; p2 = cells_ring[(i + 1) % len(cells_ring)]
        r1, c1 = divmod(p1, 16); r2, c2 = divmod(p2, 16)
        if abs(r1 - r2) + abs(c1 - c2) != 1: continue
        if r1 == r2:
            if c1 < c2: ring.append((p1, p2, "horizontal"))
            else: ring.append((p2, p1, "horizontal"))
        else:
            if r1 < r2: ring.append((p1, p2, "vertical"))
            else: ring.append((p2, p1, "vertical"))

    # Shell-k-to-shell-(k-1) edges: each shell-k cell has an outward neighbor in shell k-1
    to_outer = []
    for p in cells_ring:
        outer = outward_neighbor(p, shell)
        if outer:
            to_outer.append((p,) + outer)

    n_y_ring = len(ring)
    n_y_outer = len(to_outer)
    n_y = n_y_ring + n_y_outer

    def y_ring(e): return n_x + e
    def y_outer(e): return n_x + n_y_ring + e
    n_vars = n_x + n_y

    # Objective: max Σ y
    c_obj = np.zeros(n_vars)
    for e in range(n_y_ring): c_obj[y_ring(e)] = -1.0
    for e in range(n_y_outer): c_obj[y_outer(e)] = -1.0

    eq_data, eq_row, eq_col = [], [], []
    b_eq_arr = []
    ub_data, ub_row, ub_col = [], [], []
    b_ub_arr = []

    # Cell coverage
    for i, cell in enumerate(cells_ring):
        for px in cell_to_p[cell]:
            eq_data.append(1.0); eq_row.append(i); eq_col.append(px)
        b_eq_arr.append(1.0)
    # Piece coverage (≤ 1, not =)
    rcount = 0
    for pid in available_pids:
        if not piece_to_p[pid]: continue
        for px in piece_to_p[pid]:
            ub_data.append(1.0); ub_row.append(rcount); ub_col.append(px)
        b_ub_arr.append(1.0); rcount += 1

    # Ring edges
    for e_idx, (pos1, pos2, dir_) in enumerate(ring):
        if dir_ == "horizontal": s1, s2 = 1, 3
        else: s1, s2 = 2, 0
        c_left = set()
        c_right = set()
        for px in cell_to_p[pos1]:
            c = placements[px][3][s1]
            if c != 0: c_left.add(c)
        for px in cell_to_p[pos2]:
            c = placements[px][3][s2]
            if c != 0: c_right.add(c)
        shared = c_left & c_right
        matchable_p1 = [px for px in cell_to_p[pos1] if placements[px][3][s1] in shared]
        matchable_p2 = [px for px in cell_to_p[pos2] if placements[px][3][s2] in shared]
        ub_data.append(1.0); ub_row.append(rcount); ub_col.append(y_ring(e_idx))
        for px in matchable_p1:
            ub_data.append(-1.0); ub_row.append(rcount); ub_col.append(px)
        b_ub_arr.append(0.0); rcount += 1
        ub_data.append(1.0); ub_row.append(rcount); ub_col.append(y_ring(e_idx))
        for px in matchable_p2:
            ub_data.append(-1.0); ub_row.append(rcount); ub_col.append(px)
        b_ub_arr.append(0.0); rcount += 1

    # Outer edges
    for e_idx, (pos_inner, pos_outer, out_side, their_side) in enumerate(to_outer):
        if pos_outer not in frame_placement:
            # Outer cell not placed (impossible for shell ≥ 1)
            continue
        outer_pid, outer_rot = frame_placement[pos_outer]
        outer_rotated = rotate(pieces[outer_pid], outer_rot)
        target_color = outer_rotated[their_side]
        if target_color == 0: continue
        matchable = [px for px in cell_to_p[pos_inner]
                     if placements[px][3][out_side] == target_color]
        ub_data.append(1.0); ub_row.append(rcount); ub_col.append(y_outer(e_idx))
        for px in matchable:
            ub_data.append(-1.0); ub_row.append(rcount); ub_col.append(px)
        b_ub_arr.append(0.0); rcount += 1

    A_eq = coo_matrix((eq_data, (eq_row, eq_col)),
                      shape=(len(b_eq_arr), n_vars)).tocsr()
    A_ub = coo_matrix((ub_data, (ub_row, ub_col)),
                      shape=(rcount, n_vars)).tocsr()
    b_eq_a = np.array(b_eq_arr)
    b_ub_a = np.array(b_ub_arr)

    bounds = [(0.0, 1.0)] * n_vars
    integrality = np.zeros(n_vars)
    for i in range(n_x):
        integrality[i] = 1

    t0 = time.time()
    res = linprog(c_obj, A_ub=A_ub, b_ub=b_ub_a, A_eq=A_eq, b_eq=b_eq_a,
                  bounds=bounds, method="highs", integrality=integrality,
                  options={"time_limit": 300})
    elapsed = time.time() - t0
    print(f"  MIP time: {elapsed:.2f}s")

    if not res.success:
        print(f"  Shell {shell} MIP failed: {res.message}")
        return frame_placement, 0

    score = -res.fun
    matched_ring = sum(res.x[y_ring(e)] for e in range(n_y_ring))
    matched_outer = sum(res.x[y_outer(e)] for e in range(n_y_outer))
    print(f"  Matched: {int(matched_ring)} ring + {int(matched_outer)} outer = {int(score)} / {n_y}")

    chosen = {}
    for idx in range(n_x):
        if res.x[idx] > 0.5:
            pid, pos, k, _ = placements[idx]
            chosen[pos] = (pid, k)
    new_placement = {**frame_placement, **chosen}
    return new_placement, int(score)


def score_full_board(placement, pieces):
    grid = [(0, 0, 0, 0)] * 256
    for pos, (pid, rot) in placement.items():
        grid[pos] = rotate(pieces[pid], rot)
    m = 0
    for r in range(16):
        for c in range(15):
            if grid[r*16+c][1] == grid[r*16+c+1][3]: m += 1
    for r in range(15):
        for c in range(16):
            if grid[r*16+c][2] == grid[(r+1)*16+c][0]: m += 1
    return m


def main():
    pieces = load_pieces()
    n_pieces = len(pieces)

    # Load shell-0 from previous run
    with open("output/vol-74/shell0_solution.json") as f:
        shell0 = json.load(f)
    placement = {item["pos"]: (item["piece_id"], item["rotation"])
                 for item in shell0["placement"]}

    interior_pids = [i for i in range(n_pieces) if piece_kind(pieces[i]) == "interior"]
    print(f"Starting CAS with shell-0 (60/60 matched)")

    cum_score = 60
    for shell in range(1, 8):
        used = set(p for p, _ in placement.values())
        placement, shell_score = solve_shell(shell, placement, pieces, interior_pids, used)
        cum_score += shell_score
        print(f"  Cumulative MIP-objective: {cum_score}")

    # Final total board score
    total = score_full_board(placement, pieces)
    print(f"\n========================================")
    print(f"CAS FULL BOARD SCORE: {total} / 480")
    print(f"========================================")

    # Save
    out = {
        "matched": total,
        "placement": [{"pos": pos, "piece_id": pid, "rotation": rot}
                      for pos, (pid, rot) in sorted(placement.items())],
        "method": "Concentric Annular Solving (CAS)",
    }
    Path("output/vol-74").mkdir(parents=True, exist_ok=True)
    with open("output/vol-74/cas_full_solution.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved to output/vol-74/cas_full_solution.json")


if __name__ == "__main__":
    main()
