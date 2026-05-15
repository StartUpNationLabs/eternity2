#!/usr/bin/env python3
"""Vol-74 Shell-0 — CORRECT MIP with per-color z variables.

For each ring edge e and each color c:
  z[e, c] ≤ Σ x[p1 with color c at side s1]
  z[e, c] ≤ Σ x[p2 with color c at side s2]

y[e] = Σ_c z[e, c]

This enforces matched color across the edge correctly.
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


def main():
    pieces = load_pieces()
    n_pieces = len(pieces)
    frame_pos_list = frame_cells()

    frame_pieces = [i for i in range(n_pieces) if piece_kind(pieces[i]) in ("corner", "edge")]

    # Enumerate placements
    placements = []
    for pid in frame_pieces:
        pk = piece_kind(pieces[pid])
        for pos in frame_pos_list:
            ck = cell_kind(pos)
            if pk != ck: continue
            for k in valid_rotations_for(pieces[pid], pos):
                placements.append((pid, pos, k, rotate(pieces[pid], k)))
    n_x = len(placements)
    print(f"Placements: {n_x}")

    cell_to_p = collections.defaultdict(list)
    piece_to_p = collections.defaultdict(list)
    for idx, (pid, pos, k, _) in enumerate(placements):
        cell_to_p[pos].append(idx)
        piece_to_p[pid].append(idx)

    # Ring edges
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
    print(f"Ring edges: {len(ring_edges)}")

    # Collect non-border colors
    non_border_colors = set()
    for p in pieces:
        for c in p:
            if c != 0: non_border_colors.add(c)
    non_border_colors = sorted(non_border_colors)
    print(f"Non-border colors: {len(non_border_colors)}")

    # Variables: x + z[e, c] + y[e]
    n_y = len(ring_edges)
    # z[e, c] indexing
    z_idx = {}
    for e in range(n_y):
        for c in non_border_colors:
            z_idx[(e, c)] = n_x + len(z_idx)
    n_z = len(z_idx)
    # y[e] indexing
    y_start = n_x + n_z
    def y_idx(e): return y_start + e
    n_vars = n_x + n_z + n_y
    print(f"Total vars: {n_vars} (x={n_x}, z={n_z}, y={n_y})")

    # Objective: max Σ y
    c_obj = np.zeros(n_vars)
    for e in range(n_y):
        c_obj[y_idx(e)] = -1.0

    # Constraints
    eq_data, eq_row, eq_col = [], [], []
    b_eq_arr = []
    ub_data, ub_row, ub_col = [], [], []
    b_ub_arr = []
    rcount_eq = 0
    rcount_ub = 0

    # Cell coverage
    for cell in frame_pos_list:
        for px in cell_to_p[cell]:
            eq_data.append(1.0); eq_row.append(rcount_eq); eq_col.append(px)
        b_eq_arr.append(1.0); rcount_eq += 1
    # Piece coverage
    for pid in frame_pieces:
        if not piece_to_p[pid]: continue
        for px in piece_to_p[pid]:
            eq_data.append(1.0); eq_row.append(rcount_eq); eq_col.append(px)
        b_eq_arr.append(1.0); rcount_eq += 1

    # For each edge e and each color c:
    # z[e, c] ≤ Σ x[p1 with color c at side s1]
    # z[e, c] ≤ Σ x[p2 with color c at side s2]
    for e_idx, (pos1, pos2, s1, s2) in enumerate(ring_edges):
        # Group placements by outgoing color
        c_left = collections.defaultdict(list)
        c_right = collections.defaultdict(list)
        for px in cell_to_p[pos1]:
            col_left = placements[px][3][s1]
            if col_left != 0: c_left[col_left].append(px)
        for px in cell_to_p[pos2]:
            col_right = placements[px][3][s2]
            if col_right != 0: c_right[col_right].append(px)
        for c in non_border_colors:
            # z[e, c] - Σ x[p1, c] ≤ 0
            ub_data.append(1.0); ub_row.append(rcount_ub); ub_col.append(z_idx[(e_idx, c)])
            for px in c_left.get(c, []):
                ub_data.append(-1.0); ub_row.append(rcount_ub); ub_col.append(px)
            b_ub_arr.append(0.0); rcount_ub += 1
            # z[e, c] - Σ x[p2, c] ≤ 0
            ub_data.append(1.0); ub_row.append(rcount_ub); ub_col.append(z_idx[(e_idx, c)])
            for px in c_right.get(c, []):
                ub_data.append(-1.0); ub_row.append(rcount_ub); ub_col.append(px)
            b_ub_arr.append(0.0); rcount_ub += 1
        # y[e] - Σ_c z[e, c] = 0  (use equality for tightness, or ≤ for flexibility)
        # Use ≤ so the LP can choose smaller y if needed; for maximization with all z ≥ 0 free,
        # the LP will push y up to its max ≤ Σ z.
        # Actually, we want y[e] = Σ_c z[e, c]. Use equality.
        eq_data.append(1.0); eq_row.append(rcount_eq); eq_col.append(y_idx(e_idx))
        for c in non_border_colors:
            eq_data.append(-1.0); eq_row.append(rcount_eq); eq_col.append(z_idx[(e_idx, c)])
        b_eq_arr.append(0.0); rcount_eq += 1

    A_eq = coo_matrix((eq_data, (eq_row, eq_col)),
                      shape=(rcount_eq, n_vars)).tocsr()
    A_ub = coo_matrix((ub_data, (ub_row, ub_col)),
                      shape=(rcount_ub, n_vars)).tocsr()
    b_eq = np.array(b_eq_arr)
    b_ub = np.array(b_ub_arr)

    bounds = [(0.0, 1.0)] * n_vars
    integrality = np.zeros(n_vars)
    for i in range(n_x):
        integrality[i] = 1

    print(f"\nSolving MIP...")
    t0 = time.time()
    res = linprog(c_obj, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds, method="highs", integrality=integrality,
                  options={"time_limit": 600})
    elapsed = time.time() - t0
    print(f"Time: {elapsed:.2f}s")
    print(f"Status: {res.message}")
    if not res.success:
        return

    score = -res.fun
    print(f"\nShell-0 MIP score (corrected): {score:.2f} / 60")

    chosen = {}
    for idx in range(n_x):
        if res.x[idx] > 0.5:
            pid, pos, k, _ = placements[idx]
            chosen[pos] = (pid, k)
    out = {
        "matched_shell0": int(score),
        "placement": [{"pos": pos, "piece_id": pid, "rotation": rot}
                      for pos, (pid, rot) in sorted(chosen.items())],
    }
    Path("output/vol-74").mkdir(parents=True, exist_ok=True)
    with open("output/vol-74/shell0_solution_fixed.json", "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
