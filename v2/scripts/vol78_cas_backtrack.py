#!/usr/bin/env python3
"""Vol-78 — CAS-BACKTRACK: depth-limited tree search.

When a shell fails to complete fully, backtrack and try a different
solution for that shell (using cutting-plane forbidden-solution
constraints).

Implementation: builds on vol-74's solve_shell_fixed but adds the
forbidden-solutions list (cuts).

Reuses cutting-plane infrastructure from vol-76 frame enumerator.
"""

import collections
import csv
import glob
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix

sys.path.insert(0, 'scripts')
from vol74_cas_full_fixed import (
    load_pieces, rotate, piece_kind, shell_distance, shell_cells_ring,
    outward_neighbor, score_full_board
)


def solve_shell_with_cuts(shell, frame_placement, pieces, interior_pids, used_pids,
                          forbidden_sigs, time_limit=120):
    """Same as vol-74 solve_shell_fixed but with cutting-plane cuts.

    forbidden_sigs: list of frozensets of placement-index tuples to forbid.
    """
    cells_ring = shell_cells_ring(shell)
    available_pids = [p for p in interior_pids if p not in used_pids]

    placements = []
    for pid in available_pids:
        for pos in cells_ring:
            for k in range(4):
                rotated = rotate(pieces[pid], k)
                if 0 in rotated: continue
                placements.append((pid, pos, k, rotated))
    n_x = len(placements)
    if n_x == 0:
        return frame_placement, 0, None

    cell_to_p = collections.defaultdict(list)
    piece_to_p = collections.defaultdict(list)
    for idx, (pid, pos, k, _) in enumerate(placements):
        cell_to_p[pos].append(idx)
        piece_to_p[pid].append(idx)

    ring = []
    for i in range(len(cells_ring)):
        p1 = cells_ring[i]; p2 = cells_ring[(i + 1) % len(cells_ring)]
        r1, c1 = divmod(p1, 16); r2, c2 = divmod(p2, 16)
        if abs(r1 - r2) + abs(c1 - c2) != 1: continue
        if r1 == r2:
            if c1 < c2: ring.append((p1, p2, 1, 3))
            else: ring.append((p2, p1, 1, 3))
        else:
            if r1 < r2: ring.append((p1, p2, 2, 0))
            else: ring.append((p2, p1, 2, 0))

    to_outer = []
    for p in cells_ring:
        outer = outward_neighbor(p, shell)
        if outer: to_outer.append((p,) + outer)

    n_y_ring = len(ring)
    n_y_outer = len(to_outer)
    n_y = n_y_ring + n_y_outer

    non_border_colors = set()
    for p in pieces:
        for c in p:
            if c != 0: non_border_colors.add(c)
    non_border_colors = sorted(non_border_colors)

    z_idx = {}
    for e in range(n_y):
        for c in non_border_colors:
            z_idx[(e, c)] = n_x + len(z_idx)
    n_z = len(z_idx)
    y_start = n_x + n_z
    def y_ring_v(e): return y_start + e
    def y_outer_v(e): return y_start + n_y_ring + e
    n_vars = n_x + n_z + n_y

    c_obj = np.zeros(n_vars)
    for e in range(n_y_ring): c_obj[y_ring_v(e)] = -1.0
    for e in range(n_y_outer): c_obj[y_outer_v(e)] = -1.0

    eq_data, eq_row, eq_col = [], [], []
    b_eq_arr = []
    ub_data, ub_row, ub_col = [], [], []
    b_ub_arr = []
    rcount_eq = 0
    rcount_ub = 0

    for cell in cells_ring:
        for px in cell_to_p[cell]:
            eq_data.append(1.0); eq_row.append(rcount_eq); eq_col.append(px)
        b_eq_arr.append(1.0); rcount_eq += 1

    for pid in available_pids:
        if not piece_to_p[pid]: continue
        for px in piece_to_p[pid]:
            ub_data.append(1.0); ub_row.append(rcount_ub); ub_col.append(px)
        b_ub_arr.append(1.0); rcount_ub += 1

    for e_idx, (pos1, pos2, s1, s2) in enumerate(ring):
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
        eq_data.append(1.0); eq_row.append(rcount_eq); eq_col.append(y_ring_v(e_idx))
        for c in non_border_colors:
            eq_data.append(-1.0); eq_row.append(rcount_eq); eq_col.append(z_idx[(e_idx, c)])
        b_eq_arr.append(0.0); rcount_eq += 1

    for e_idx, (pos_inner, pos_outer, out_side, their_side) in enumerate(to_outer):
        if pos_outer not in frame_placement: continue
        outer_pid, outer_rot = frame_placement[pos_outer]
        outer_rotated = rotate(pieces[outer_pid], outer_rot)
        target_color = outer_rotated[their_side]
        if target_color == 0: continue
        matchable = [px for px in cell_to_p[pos_inner]
                     if placements[px][3][out_side] == target_color]
        ub_data.append(1.0); ub_row.append(rcount_ub); ub_col.append(y_outer_v(e_idx))
        for px in matchable:
            ub_data.append(-1.0); ub_row.append(rcount_ub); ub_col.append(px)
        b_ub_arr.append(0.0); rcount_ub += 1

    # Cutting plane constraints (forbidden solutions)
    for forbidden in forbidden_sigs:
        # Σ x[i] for i in forbidden ≤ |forbidden| - 1
        for vi in forbidden:
            ub_data.append(1.0); ub_row.append(rcount_ub); ub_col.append(vi)
        b_ub_arr.append(len(forbidden) - 1); rcount_ub += 1

    A_eq = coo_matrix((eq_data, (eq_row, eq_col)),
                      shape=(rcount_eq, n_vars)).tocsr()
    A_ub = coo_matrix((ub_data, (ub_row, ub_col)),
                      shape=(rcount_ub, n_vars)).tocsr()
    b_eq_a = np.array(b_eq_arr)
    b_ub_a = np.array(b_ub_arr)

    bounds = [(0.0, 1.0)] * n_vars
    integrality = np.zeros(n_vars)
    for i in range(n_x):
        integrality[i] = 1

    res = linprog(c_obj, A_ub=A_ub, b_ub=b_ub_a, A_eq=A_eq, b_eq=b_eq_a,
                  bounds=bounds, method="highs", integrality=integrality,
                  options={"time_limit": time_limit})
    if not res.success:
        return frame_placement, 0, None

    score = -res.fun

    chosen = {}
    chosen_indices = []
    for idx in range(n_x):
        if res.x[idx] > 0.5:
            pid, pos, k, _ = placements[idx]
            chosen[pos] = (pid, k)
            chosen_indices.append(idx)
    return {**frame_placement, **chosen}, int(score), frozenset(chosen_indices)


def main():
    pieces = load_pieces()
    n_pieces = len(pieces)
    interior_pids = [i for i in range(n_pieces) if piece_kind(pieces[i]) == "interior"]

    # Load frame
    frame_file = sys.argv[1] if len(sys.argv) > 1 else "output/vol-74/shell0_solution_fixed.json"
    with open(frame_file) as f: shell0_data = json.load(f)
    placement_stack = [{item["pos"]: (item["piece_id"], item["rotation"])
                        for item in shell0_data["placement"]}]
    forbidden_per_shell = {i: [] for i in range(8)}
    max_attempts = 3

    print(f"CAS-BACKTRACK starting from {frame_file}")
    print(f"Max attempts per shell: {max_attempts}")

    shell = 1
    attempts = {i: 0 for i in range(8)}
    while shell < 8:
        current = placement_stack[-1]
        used = set(p for p, _ in current.values())
        new_placement, shell_score, signature = solve_shell_with_cuts(
            shell, current, pieces, interior_pids, used,
            forbidden_per_shell[shell], time_limit=60
        )
        max_possible_score = 2 * len(shell_cells_ring(shell))  # ring + outer
        print(f"  Shell {shell}: score {shell_score}/{max_possible_score} (attempt {attempts[shell]+1})")
        if shell_score == max_possible_score or attempts[shell] >= max_attempts:
            # Commit
            placement_stack.append(new_placement)
            shell += 1
            attempts[shell] = 0 if shell < 8 else 0
        else:
            # Backtrack: forbid this and try again
            forbidden_per_shell[shell].append(signature)
            attempts[shell] += 1
            print(f"    forbidding solution, retrying...")

    # Final score
    final = placement_stack[-1]
    total = score_full_board(final, pieces)
    print(f"\n=== CAS-BACKTRACK FINAL: {total} / 480 ===")

    out = {
        "matched": total,
        "placement": [{"pos": pos, "piece_id": pid, "rotation": rot}
                      for pos, (pid, rot) in sorted(final.items())],
        "method": "CAS-BACKTRACK"
    }
    Path("output/vol-78").mkdir(parents=True, exist_ok=True)
    with open("output/vol-78/cas_backtrack_solution.json", "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
