#!/usr/bin/env python3
"""Vol-76 — Enumerate distinct 60/60 frame solutions.

How many ways can the 60 frame pieces be arranged with all 60 ring
edges matching?

Method: solve frame MIP, save solution, add a "different solution"
cut, re-solve. Repeat until no more 60/60 solutions exist.

This bounds the size of the "frame space" for CAS-BACKTRACK.
"""

import collections
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix, vstack as sp_vstack


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


def cell_kind(pos):
    r, c = divmod(pos, 16)
    if r in (0, 15) and c in (0, 15): return "corner"
    if r in (0, 15) or c in (0, 15): return "edge"
    return "interior"


def piece_kind(edges):
    nb = sum(1 for c in edges if c == 0)
    return {0: "interior", 1: "edge", 2: "corner"}.get(nb)


def valid_rotations_for(piece_edges, pos):
    r, c = divmod(pos, 16)
    outward = []
    if r == 0: outward.append(0)
    if c == 15: outward.append(1)
    if r == 15: outward.append(2)
    if c == 0: outward.append(3)
    valid = []
    for k in range(4):
        rotated = rotate(piece_edges, k)
        ok = True
        for side in range(4):
            facing_frame = side in outward
            if facing_frame and rotated[side] != 0:
                ok = False; break
            if not facing_frame and rotated[side] == 0:
                ok = False; break
        if ok:
            valid.append(k)
    return valid


def frame_cells():
    cells = []
    for c in range(16): cells.append(c)
    for r in range(1, 16): cells.append(r * 16 + 15)
    for c in range(14, -1, -1): cells.append(15 * 16 + c)
    for r in range(14, 0, -1): cells.append(r * 16)
    return cells


def build_mip_matrices(placements, frame_pos_list, frame_pieces, non_border_colors, ring_edges, cell_to_p, piece_to_p):
    n_x = len(placements)
    n_y = len(ring_edges)
    # z[e, c]
    z_idx = {}
    for e in range(n_y):
        for c in non_border_colors:
            z_idx[(e, c)] = n_x + len(z_idx)
    n_z = len(z_idx)
    y_start = n_x + n_z
    def y_idx(e): return y_start + e
    n_vars = n_x + n_z + n_y

    c_obj = np.zeros(n_vars)
    for e in range(n_y):
        c_obj[y_idx(e)] = -1.0

    eq_data, eq_row, eq_col = [], [], []
    b_eq_arr = []
    ub_data, ub_row, ub_col = [], [], []
    b_ub_arr = []
    rcount_eq = 0
    rcount_ub = 0

    for cell in frame_pos_list:
        for px in cell_to_p[cell]:
            eq_data.append(1.0); eq_row.append(rcount_eq); eq_col.append(px)
        b_eq_arr.append(1.0); rcount_eq += 1
    for pid in frame_pieces:
        if not piece_to_p[pid]: continue
        for px in piece_to_p[pid]:
            eq_data.append(1.0); eq_row.append(rcount_eq); eq_col.append(px)
        b_eq_arr.append(1.0); rcount_eq += 1

    for e_idx, (pos1, pos2, s1, s2) in enumerate(ring_edges):
        c_left = collections.defaultdict(list)
        c_right = collections.defaultdict(list)
        for px in cell_to_p[pos1]:
            col_l = placements[px][3][s1]
            if col_l != 0: c_left[col_l].append(px)
        for px in cell_to_p[pos2]:
            col_r = placements[px][3][s2]
            if col_r != 0: c_right[col_r].append(px)
        for c in non_border_colors:
            ub_data.append(1.0); ub_row.append(rcount_ub); ub_col.append(z_idx[(e_idx, c)])
            for px in c_left.get(c, []):
                ub_data.append(-1.0); ub_row.append(rcount_ub); ub_col.append(px)
            b_ub_arr.append(0.0); rcount_ub += 1
            ub_data.append(1.0); ub_row.append(rcount_ub); ub_col.append(z_idx[(e_idx, c)])
            for px in c_right.get(c, []):
                ub_data.append(-1.0); ub_row.append(rcount_ub); ub_col.append(px)
            b_ub_arr.append(0.0); rcount_ub += 1
        eq_data.append(1.0); eq_row.append(rcount_eq); eq_col.append(y_idx(e_idx))
        for c in non_border_colors:
            eq_data.append(-1.0); eq_row.append(rcount_eq); eq_col.append(z_idx[(e_idx, c)])
        b_eq_arr.append(0.0); rcount_eq += 1

    return c_obj, eq_data, eq_row, eq_col, b_eq_arr, rcount_eq, ub_data, ub_row, ub_col, b_ub_arr, rcount_ub, n_vars, n_x


def main():
    pieces = load_pieces()
    n_pieces = len(pieces)
    frame_pos_list = frame_cells()
    frame_pieces = [i for i in range(n_pieces) if piece_kind(pieces[i]) in ("corner", "edge")]

    placements = []
    for pid in frame_pieces:
        pk = piece_kind(pieces[pid])
        for pos in frame_pos_list:
            ck = cell_kind(pos)
            if pk != ck: continue
            for k in valid_rotations_for(pieces[pid], pos):
                placements.append((pid, pos, k, rotate(pieces[pid], k)))
    n_x = len(placements)
    cell_to_p = collections.defaultdict(list)
    piece_to_p = collections.defaultdict(list)
    for idx, (pid, pos, k, _) in enumerate(placements):
        cell_to_p[pos].append(idx)
        piece_to_p[pid].append(idx)

    ring_edges = []
    for i in range(len(frame_pos_list)):
        p1 = frame_pos_list[i]
        p2 = frame_pos_list[(i + 1) % len(frame_pos_list)]
        r1, c1 = divmod(p1, 16); r2, c2 = divmod(p2, 16)
        if abs(r1 - r2) + abs(c1 - c2) != 1: continue
        if r1 == r2:
            if c1 < c2: ring_edges.append((p1, p2, 1, 3))
            else: ring_edges.append((p2, p1, 1, 3))
        else:
            if r1 < r2: ring_edges.append((p1, p2, 2, 0))
            else: ring_edges.append((p2, p1, 2, 0))

    non_border_colors = set()
    for p in pieces:
        for c in p:
            if c != 0: non_border_colors.add(c)
    non_border_colors = sorted(non_border_colors)

    print(f"Frame placements: {n_x}")
    print(f"Ring edges: {len(ring_edges)}")
    print(f"Non-border colors: {len(non_border_colors)}")

    # Enumerate solutions
    n_solutions = 0
    cuts = []  # list of (var_indices_in_solution, max_overlap)
    solutions = []
    target = 60  # require 60/60

    # Build base MIP matrices once
    c_obj, eq_data, eq_row, eq_col, b_eq_arr, rcount_eq, ub_data, ub_row, ub_col, b_ub_arr, rcount_ub, n_vars, n_x = \
        build_mip_matrices(placements, frame_pos_list, frame_pieces, non_border_colors, ring_edges, cell_to_p, piece_to_p)

    integrality = np.zeros(n_vars)
    for i in range(n_x):
        integrality[i] = 1

    max_solutions = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    while n_solutions < max_solutions:
        # Build current matrices including cuts
        cur_eq_data = list(eq_data); cur_eq_row = list(eq_row); cur_eq_col = list(eq_col)
        cur_b_eq = list(b_eq_arr); cur_rcount_eq = rcount_eq
        cur_ub_data = list(ub_data); cur_ub_row = list(ub_row); cur_ub_col = list(ub_col)
        cur_b_ub = list(b_ub_arr); cur_rcount_ub = rcount_ub

        # Add objective floor: y_total >= target
        # Σ_e y[e] >= target  →  -Σ_e y[e] ≤ -target
        for e in range(len(ring_edges)):
            y_var = n_x + len(non_border_colors) * len(ring_edges) + e
            cur_ub_data.append(-1.0); cur_ub_row.append(cur_rcount_ub); cur_ub_col.append(y_var)
        cur_b_ub.append(-target)
        cur_rcount_ub += 1

        # Add cuts: Σ x[var_indices] ≤ n_x_in_solution - 1
        for cut_vars in cuts:
            for vi in cut_vars:
                cur_ub_data.append(1.0); cur_ub_row.append(cur_rcount_ub); cur_ub_col.append(vi)
            cur_b_ub.append(len(cut_vars) - 1); cur_rcount_ub += 1

        A_eq = coo_matrix((cur_eq_data, (cur_eq_row, cur_eq_col)),
                          shape=(cur_rcount_eq, n_vars)).tocsr()
        A_ub = coo_matrix((cur_ub_data, (cur_ub_row, cur_ub_col)),
                          shape=(cur_rcount_ub, n_vars)).tocsr()
        b_eq = np.array(cur_b_eq); b_ub = np.array(cur_b_ub)
        bounds = [(0.0, 1.0)] * n_vars

        t0 = time.time()
        res = linprog(c_obj, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                      bounds=bounds, method="highs", integrality=integrality,
                      options={"time_limit": 30})
        if not res.success:
            print(f"\nMIP failed at solution #{n_solutions+1} (likely no more solutions exist or time-out)")
            break
        score = -res.fun
        if score < target - 0.5:
            print(f"\nNo more 60/60 solutions (got {score:.1f})")
            break
        n_solutions += 1
        # Record this solution's x-vars
        sol_vars = [idx for idx in range(n_x) if res.x[idx] > 0.5]
        cuts.append(sol_vars)
        chosen = {}
        for idx in sol_vars:
            pid, pos, k, _ = placements[idx]
            chosen[pos] = (pid, k)
        solutions.append(chosen)
        print(f"  Solution {n_solutions}: score={score:.1f} ({time.time()-t0:.1f}s)")

    print(f"\nTotal distinct 60/60 frame solutions found: {n_solutions}")

    # Save all
    Path("output/vol-76").mkdir(parents=True, exist_ok=True)
    for i, sol in enumerate(solutions):
        out = {
            "matched_shell0": target,
            "frame_solution_id": i,
            "placement": [{"pos": pos, "piece_id": pid, "rotation": rot}
                          for pos, (pid, rot) in sorted(sol.items())],
        }
        with open(f"output/vol-76/frame_solution_{i}.json", "w") as f:
            json.dump(out, f)
    print(f"Saved {n_solutions} frames to output/vol-76/")


if __name__ == "__main__":
    main()
