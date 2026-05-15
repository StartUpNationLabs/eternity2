#!/usr/bin/env python3
"""Vol-74 Shell-1 — extend frame to shell 1 (52 cells, frame-adjacent interior).

Given a frame solution from shell-0, place 52 interior pieces at
shell-1 cells with:
- Outward color of shell-1 piece matches inward color of adjacent frame piece.
- Match ring-internal edges of shell-1 to other shell-1 cells.
- Match edges TO shell-0 frame.
- Use any 52 interior pieces (196 available; 196 ≥ 52).

Maximize: # matched edges in shell-1 (internal ring + outward to shell-0).

Then continue inward.
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


def shell_cells(shell):
    """Cells at shell distance == shell."""
    return [pos for pos in range(256) if shell_distance(pos) == shell]


def shell1_ring_order():
    """Shell 1 cells in ring order: walk around the 14x14 interior perimeter.

    Shell 1 = cells with shell_distance == 1, i.e., r∈{1,14} or c∈{1,14},
    AND r in 1..14, c in 1..14. The 14x14 interior is rows 1..14, cols 1..14.
    Shell 1 cells: r==1 or r==14 or c==1 or c==14, within rows 1..14 cols 1..14.

    Count: row 1 has 14 cells; row 14 has 14 cells; col 1 has 12 (excl corners);
    col 14 has 12. Total = 14+14+12+12 = 52. ✓
    """
    cells = []
    # Row 1 (cols 1..14)
    for c in range(1, 15):
        cells.append(1 * 16 + c)
    # Right col (rows 2..14)
    for r in range(2, 15):
        cells.append(r * 16 + 14)
    # Row 14 (cols 13..1 reverse)
    for c in range(13, 0, -1):
        cells.append(14 * 16 + c)
    # Left col (rows 13..2 reverse)
    for r in range(13, 1, -1):
        cells.append(r * 16 + 1)
    return cells


def main():
    pieces = load_pieces()
    n_pieces = len(pieces)

    # Load shell-0 frame solution
    with open("output/vol-74/shell0_solution.json") as f:
        shell0_data = json.load(f)
    frame_placement = {item["pos"]: (item["piece_id"], item["rotation"])
                       for item in shell0_data["placement"]}

    print(f"Loaded frame (60/60 matched): {len(frame_placement)} pieces")

    # Shell-1 cells in ring order
    shell1 = shell1_ring_order()
    print(f"Shell-1 cells: {len(shell1)}")

    # Interior pieces available
    used_pids = set(p for p, _ in frame_placement.values())
    interior_pids = [i for i in range(n_pieces) if piece_kind(pieces[i]) == "interior"]
    print(f"Interior pieces total: {len(interior_pids)} (using 0 in frame)")

    # Enumerate shell-1 placements: (piece, cell, rotation)
    placements = []
    for pid in interior_pids:
        for pos in shell1:
            for k in range(4):
                rotated = rotate(pieces[pid], k)
                # Frame respect: interior cell, no border-color side facing any direction
                if 0 in rotated: continue
                placements.append((pid, pos, k, rotated))
    n_x = len(placements)
    print(f"Shell-1 placements: {n_x}")

    # Variables: x[placement_idx] + y[edge_idx for each shell-1-internal and shell-1-to-shell-0 edge]
    # Edges:
    # 1. Shell-1 ring edges: 52 edges (each consecutive pair in ring order is grid-adjacent)
    # 2. Shell-1-to-shell-0 edges: each shell-1 cell has 1 outward neighbor in shell-0.
    #    52 cells × 1 outward = 52 edges.

    shell1_ring = []
    for i in range(len(shell1)):
        p1 = shell1[i]; p2 = shell1[(i + 1) % len(shell1)]
        r1, c1 = divmod(p1, 16); r2, c2 = divmod(p2, 16)
        if abs(r1 - r2) + abs(c1 - c2) != 1: continue  # skip non-adjacent (shouldn't happen)
        if r1 == r2:
            if c1 < c2: shell1_ring.append((p1, p2, "horizontal"))
            else: shell1_ring.append((p2, p1, "horizontal"))
        else:
            if r1 < r2: shell1_ring.append((p1, p2, "vertical"))
            else: shell1_ring.append((p2, p1, "vertical"))

    # Shell-1 to shell-0: each shell-1 cell has outward neighbor in shell-0
    # The outward direction depends on shell-1 cell position:
    # - r==1: outward N (shell-0 at r=0, c same)
    # - r==14: outward S (shell-0 at r=15)
    # - c==1: outward W (shell-0 at c=0)
    # - c==14: outward E (shell-0 at c=15)
    s1_to_s0 = []
    for p in shell1:
        r, c = divmod(p, 16)
        if r == 1: outward_neighbor_pos = 0 * 16 + c; out_side = 0; their_side = 2
        elif r == 14: outward_neighbor_pos = 15 * 16 + c; out_side = 2; their_side = 0
        elif c == 1: outward_neighbor_pos = r * 16 + 0; out_side = 3; their_side = 1
        elif c == 14: outward_neighbor_pos = r * 16 + 15; out_side = 1; their_side = 3
        else: continue
        s1_to_s0.append((p, outward_neighbor_pos, out_side, their_side))

    print(f"Shell-1 ring edges: {len(shell1_ring)}")
    print(f"Shell-1-to-shell-0 edges: {len(s1_to_s0)}")

    n_y_ring = len(shell1_ring)
    n_y_to_s0 = len(s1_to_s0)
    n_y = n_y_ring + n_y_to_s0

    def y_ring_idx(e): return n_x + e
    def y_s0_idx(e): return n_x + n_y_ring + e
    n_vars = n_x + n_y

    print(f"Total vars: {n_vars}")

    # Indexes
    cell_to_p = collections.defaultdict(list)
    piece_to_p = collections.defaultdict(list)
    for idx, (pid, pos, k, _) in enumerate(placements):
        cell_to_p[pos].append(idx)
        piece_to_p[pid].append(idx)

    # Objective: max Σ y
    c_obj = np.zeros(n_vars)
    for e in range(n_y_ring): c_obj[y_ring_idx(e)] = -1.0
    for e in range(n_y_to_s0): c_obj[y_s0_idx(e)] = -1.0

    # Constraints
    eq_data, eq_row, eq_col = [], [], []
    b_eq_arr = []
    # Cell-coverage: Σ_{p,k} x[p, c, k] = 1 for each shell-1 cell
    for i, cell in enumerate(shell1):
        for px in cell_to_p[cell]:
            eq_data.append(1.0); eq_row.append(i); eq_col.append(px)
        b_eq_arr.append(1.0)
    # Piece-coverage: Σ x[p, *, *] ≤ 1 per piece (interior pieces only used at most once)
    # We have 196 interior pieces but only 52 cells; piece-coverage is ≤ 1 not = 1.
    # Use UB constraint: Σ x[p, *, *] ≤ 1 for each piece.
    ub_data, ub_row, ub_col = [], [], []
    b_ub_arr = []
    rcount = 0
    for pid in interior_pids:
        for px in piece_to_p[pid]:
            ub_data.append(1.0); ub_row.append(rcount); ub_col.append(px)
        b_ub_arr.append(1.0); rcount += 1

    # Ring edges constraint
    for e_idx, (pos1, pos2, dir_) in enumerate(shell1_ring):
        if dir_ == "horizontal": s1, s2 = 1, 3
        else: s1, s2 = 2, 0
        c_left = set()
        c_right = set()
        for px in cell_to_p[pos1]:
            edges = placements[px][3]
            if edges[s1] != 0: c_left.add(edges[s1])
        for px in cell_to_p[pos2]:
            edges = placements[px][3]
            if edges[s2] != 0: c_right.add(edges[s2])
        shared = c_left & c_right
        matchable_p1 = [px for px in cell_to_p[pos1] if placements[px][3][s1] in shared]
        matchable_p2 = [px for px in cell_to_p[pos2] if placements[px][3][s2] in shared]
        ub_data.append(1.0); ub_row.append(rcount); ub_col.append(y_ring_idx(e_idx))
        for px in matchable_p1:
            ub_data.append(-1.0); ub_row.append(rcount); ub_col.append(px)
        b_ub_arr.append(0.0); rcount += 1
        ub_data.append(1.0); ub_row.append(rcount); ub_col.append(y_ring_idx(e_idx))
        for px in matchable_p2:
            ub_data.append(-1.0); ub_row.append(rcount); ub_col.append(px)
        b_ub_arr.append(0.0); rcount += 1

    # Shell-1 to shell-0 edges
    # Each shell-1 cell's outward-side color must match the shell-0 neighbor's inward-side color
    # (which is fixed from frame_placement).
    for e_idx, (pos_s1, pos_s0, out_side, their_side) in enumerate(s1_to_s0):
        s0_pid, s0_rot = frame_placement[pos_s0]
        s0_rotated = rotate(pieces[s0_pid], s0_rot)
        target_color = s0_rotated[their_side]  # the color frame piece shows toward shell-1
        if target_color == 0:
            # Shouldn't happen — frame piece's inward side shouldn't be border
            print(f"WARNING: target_color=0 at edge {e_idx}")
            continue
        # y[e] - Σ x[shell-1 placements at pos_s1 with outward color == target_color] ≤ 0
        matchable = [px for px in cell_to_p[pos_s1]
                     if placements[px][3][out_side] == target_color]
        ub_data.append(1.0); ub_row.append(rcount); ub_col.append(y_s0_idx(e_idx))
        for px in matchable:
            ub_data.append(-1.0); ub_row.append(rcount); ub_col.append(px)
        b_ub_arr.append(0.0); rcount += 1

    A_eq = coo_matrix((eq_data, (eq_row, eq_col)),
                      shape=(len(b_eq_arr), n_vars)).tocsr()
    A_ub = coo_matrix((ub_data, (ub_row, ub_col)),
                      shape=(rcount, n_vars)).tocsr()
    b_eq = np.array(b_eq_arr)
    b_ub = np.array(b_ub_arr)
    bounds = [(0.0, 1.0)] * n_vars

    # Integer x
    integrality = np.zeros(n_vars)
    for i in range(n_x):
        integrality[i] = 1

    print(f"\nSolving shell-1 MIP...")
    t0 = time.time()
    res = linprog(c_obj, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds, method="highs", integrality=integrality)
    print(f"Time: {time.time()-t0:.2f}s")
    print(f"Status: {res.message}")
    if not res.success:
        print("MIP failed.")
        return

    score = -res.fun
    print(f"\n=== Shell-1 MIP score: {score:.2f} / {n_y_ring + n_y_to_s0} edges ===")
    print(f"  Ring (internal shell-1): {n_y_ring} edges; matched: {sum(res.x[y_ring_idx(e)] for e in range(n_y_ring)):.0f}")
    print(f"  Shell-1→shell-0: {n_y_to_s0} edges; matched: {sum(res.x[y_s0_idx(e)] for e in range(n_y_to_s0)):.0f}")

    # Decode placements
    chosen = {}
    for idx in range(n_x):
        if res.x[idx] > 0.5:
            pid, pos, k, _ = placements[idx]
            chosen[pos] = (pid, k)
    # Combine with frame
    full = {**frame_placement, **chosen}
    out = {
        "matched_shell0_shell1": int(score) + 60,  # 60 from frame
        "placement": [{"pos": pos, "piece_id": pid, "rotation": rot}
                      for pos, (pid, rot) in sorted(full.items())],
    }
    Path("output/vol-74").mkdir(parents=True, exist_ok=True)
    with open("output/vol-74/shell01_solution.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"Saved shell-0+1 solution to output/vol-74/shell01_solution.json")


if __name__ == "__main__":
    main()
