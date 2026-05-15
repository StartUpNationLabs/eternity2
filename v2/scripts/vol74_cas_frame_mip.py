#!/usr/bin/env python3
"""Vol-74 Shell 0 — Solve the frame (shell 0) via MIP.

60 cells:
- 4 corner cells (pos 0, 15, 240, 255)
- 56 edge cells (top row excl corners, bottom row excl corners,
  left col excl corners, right col excl corners)

60 pieces:
- 4 corner pieces (have 2 border-color sides)
- 56 edge pieces (have 1 border-color side)

Each cell has limited piece-rotation candidates: corner-piece rotations
constrained to put 2 border sides outward; edge-piece rotations
constrained to put 1 border side outward.

MIP variables: x[piece, cell, rotation] for frame-respecting placements.
Constraints:
- Σ_(p, r) x[p, c, r] = 1 for each frame cell c.
- Σ_(c, r) x[p, c, r] = 1 for each frame piece p.
Edge variables y[edge] for matched frame edges.
- For each adjacent frame-cell pair, y ≤ sum of x's that match colors.

Objective: maximize Σ y.

Frame has 60 cells. Frame-internal edges: 16 (top row) + 16 (bottom)
+ 14 (left col interior) + 14 (right col interior) = 60 edges along
the frame ring. Each adjacent pair on the ring is an edge.

Wait — the frame's adjacencies are along the RING. Cells 0 and 1 are
adjacent (row 0). Cell 0 and 16 are NOT adjacent ON THE FRAME (they'd
be diagonal in the grid). Frame ring has 60 cells in a cycle.
Frame-internal edges = 60 (each ring-adjacent pair). Plus there are
frame-to-interior edges, but those involve shell 1 cells (not in
shell 0).

So shell 0 MIP optimizes 60 matched edges along the frame ring,
ignoring frame-to-interior matches (those are shell 0 → shell 1).

Compute shell 0 score. If ≈ 60/60, frame is perfectly matchable.
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
    """Return list of rotations k that respect the frame at pos."""
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
    """Return list of 60 frame cell positions in ring order."""
    cells = []
    # Top row left to right
    for c in range(16):
        cells.append(c)
    # Right col top+1 to bottom
    for r in range(1, 16):
        cells.append(r * 16 + 15)
    # Bottom row right-1 to left
    for c in range(14, -1, -1):
        cells.append(15 * 16 + c)
    # Left col bottom-1 to top+1
    for r in range(14, 0, -1):
        cells.append(r * 16)
    return cells


def main():
    pieces = load_pieces()
    n_pieces = len(pieces)
    frame_pos_list = frame_cells()
    print(f"Frame cells (ring): {len(frame_pos_list)}")

    # Frame pieces: those with kind == "corner" or "edge"
    frame_pieces = [i for i in range(n_pieces) if piece_kind(pieces[i]) in ("corner", "edge")]
    print(f"Frame pieces: {len(frame_pieces)} ({sum(1 for p in frame_pieces if piece_kind(pieces[p])=='corner')} corners + {sum(1 for p in frame_pieces if piece_kind(pieces[p])=='edge')} edges)")

    # Enumerate placements (piece, frame_cell, rotation)
    placements = []  # list of (piece, pos, rot, rotated_edges)
    for pid in frame_pieces:
        pk = piece_kind(pieces[pid])
        for pos in frame_pos_list:
            ck = cell_kind(pos)
            if pk != ck: continue
            for k in valid_rotations_for(pieces[pid], pos):
                placements.append((pid, pos, k, rotate(pieces[pid], k)))
    n_x = len(placements)
    print(f"Placements: {n_x}")

    # Index by cell, piece
    cell_to_p = collections.defaultdict(list)
    piece_to_p = collections.defaultdict(list)
    for idx, (pid, pos, k, _) in enumerate(placements):
        cell_to_p[pos].append(idx)
        piece_to_p[pid].append(idx)

    # Ring adjacencies: cell i ↔ cell (i+1) mod 60 in frame_pos_list
    # When ring-adjacent in the grid (which they ARE always for the frame ring)
    # The shared edge direction: depends on position.
    # Actually, frame cells in ring order are adjacent in the grid if-and-only-if
    # consecutive in the ring AND adjacent in the grid (since the ring goes around).
    # For our frame_cells: cell[i] and cell[i+1] are always grid-adjacent for
    # i in 0..59 except at the corners where we transition row→col.
    # Let me verify: at corner cells, the transition is row→col, which IS adjacent
    # in the grid (e.g., (0,15) → (1,15)). So all 60 consecutive ring pairs are
    # grid-adjacent.
    # Edge direction: if pos1's row == pos2's row, they're EW-adjacent. Else NS.
    ring_edges = []  # list of (pos1, pos2, dir) where dir=0 horizontal, 1 vertical
    for i in range(len(frame_pos_list)):
        p1 = frame_pos_list[i]
        p2 = frame_pos_list[(i + 1) % len(frame_pos_list)]
        r1, c1 = divmod(p1, 16); r2, c2 = divmod(p2, 16)
        if abs(r1 - r2) + abs(c1 - c2) != 1:
            print(f"WARNING: non-adjacent in ring at i={i}: {p1}({r1},{c1}) → {p2}({r2},{c2})")
            continue
        if r1 == r2:
            # Horizontal
            if c1 < c2:
                ring_edges.append((p1, p2, "horizontal"))
            else:
                ring_edges.append((p2, p1, "horizontal"))
        else:
            # Vertical
            if r1 < r2:
                ring_edges.append((p1, p2, "vertical"))
            else:
                ring_edges.append((p2, p1, "vertical"))
    print(f"Ring edges: {len(ring_edges)}")

    # MIP variables: x[idx] for each placement; y[edge_idx] for each ring edge
    n_y = len(ring_edges)
    # Variable indexing: x first, then y
    def y_idx(e): return n_x + e
    n_vars = n_x + n_y
    print(f"Total vars: {n_vars} (x={n_x}, y={n_y})")

    # Objective: max Σ y → min -Σ y
    c_obj = np.zeros(n_vars)
    for e in range(n_y):
        c_obj[y_idx(e)] = -1.0

    # Constraints
    rows_eq = []
    rows_ub = []

    # Cell-coverage equalities
    for cell in frame_pos_list:
        idxs = cell_to_p[cell]
        rows_eq.append((idxs, {}, 1.0))  # (vars, coefs={}, b)
    # Piece-coverage equalities
    for pid in frame_pieces:
        idxs = piece_to_p[pid]
        rows_eq.append((idxs, {}, 1.0))

    # Edge constraints: y[e] ≤ Σ matching-placements x's
    # For ring edge (p1, p2, dir):
    # - horizontal: p1's East color (side 1) must equal p2's West color (side 3)
    # - vertical: p1's South color (side 2) must equal p2's North color (side 0)
    for e_idx, (pos1, pos2, dir_) in enumerate(ring_edges):
        if dir_ == "horizontal":
            s1, s2 = 1, 3
        else:
            s1, s2 = 2, 0
        # For each pair of placements at pos1 and pos2 with matching colors,
        # y[e] is bounded above by the product (x[..] AND x[..]).
        # LP relaxation: y[e] ≤ Σ x[p1_idx where outgoing-color matches] + Σ x[p2_idx where outgoing-color matches]) / 2 ... hmm complicated.
        # Simplification: y[e] ≤ Σ_color [Σ x[p, pos1, k where outgoing color = c] AND Σ x[p, pos2, k where outgoing color = c]]
        # Use: y[e] ≤ Σ_color min(Σ_left_with_c, Σ_right_with_c)
        # Linear formulation:
        # y[e] ≤ Σ x[pos1, color c on side s1] for each color c
        # y[e] ≤ Σ x[pos2, color c on side s2] for each color c
        # (i.e., for each color, y[e] ≤ both sums)
        # Combine per color: introduce z[e, c] ≤ Σ_left, z[e, c] ≤ Σ_right, y[e] = Σ_c z[e, c]
        # That's larger. Simpler: just bound y by SUM over color-matched pairs.
        # For each color c, count placements:
        c_left = collections.defaultdict(list)  # color → list of placement indices
        c_right = collections.defaultdict(list)
        for px in cell_to_p[pos1]:
            pid, pos, k, edges = placements[px]
            c = edges[s1]
            if c != 0:  # skip border
                c_left[c].append(px)
        for px in cell_to_p[pos2]:
            pid, pos, k, edges = placements[px]
            c = edges[s2]
            if c != 0:
                c_right[c].append(px)
        # For each color c that appears in both, add constraint:
        # y[e] - Σ x[p1 with color c at s1] ≤ 0
        # y[e] - Σ x[p2 with color c at s2] ≤ 0
        # This gives y[e] ≤ min(c_left, c_right) for each c.
        # But we want y[e] ≤ Σ_c min(c_left, c_right). Bounded by max which is what?
        # Actually for our LP: y[e] = match probability. It's either 0 or 1.
        # Just take the simpler:
        # y[e] ≤ Σ_c (c_left[c] indicator AND c_right[c] indicator)
        # Linearize: y[e] - Σ (c_left ∩ c_right adjacencies) ≤ 0
        # Simpler approach: for each placement at pos1, look at its outgoing color.
        # If that color also has a placement at pos2, this is a "potential match".
        # y[e] ≤ Σ x[p1] over placements at pos1 whose color matches SOME placement at pos2.
        # OK simplest: y[e] ≤ Σ x[p1, pos1, k] for placements where rotated piece's s1 color appears as some pos2's s2.
        matchable_p1 = []
        for px in cell_to_p[pos1]:
            pid, pos, k, edges = placements[px]
            c = edges[s1]
            if c in c_right and c != 0:
                matchable_p1.append(px)
        matchable_p2 = []
        for px in cell_to_p[pos2]:
            pid, pos, k, edges = placements[px]
            c = edges[s2]
            if c in c_left and c != 0:
                matchable_p2.append(px)
        # y ≤ Σ x[matchable at p1]
        rows_ub.append((matchable_p1, {y_idx(e_idx): -1.0}, 0.0))
        # y ≤ Σ x[matchable at p2]
        rows_ub.append((matchable_p2, {y_idx(e_idx): -1.0}, 0.0))

    print(f"Constraints: {len(rows_eq)} eq + {len(rows_ub)} ub")

    # Build sparse matrices
    eq_data, eq_row, eq_col = [], [], []
    b_eq_arr = []
    for i, (idxs, coefs, b) in enumerate(rows_eq):
        for px in idxs:
            eq_data.append(1.0); eq_row.append(i); eq_col.append(px)
        for vi, val in coefs.items():
            eq_data.append(val); eq_row.append(i); eq_col.append(vi)
        b_eq_arr.append(b)
    A_eq = coo_matrix((eq_data, (eq_row, eq_col)), shape=(len(rows_eq), n_vars)).tocsr()
    b_eq_a = np.array(b_eq_arr)

    ub_data, ub_row, ub_col = [], [], []
    b_ub_arr = []
    for i, (idxs, coefs, b) in enumerate(rows_ub):
        for px in idxs:
            ub_data.append(1.0); ub_row.append(i); ub_col.append(px)
        # And the y variable
        for vi, val in coefs.items():
            # Negate the sign convention: rows_ub is "Σ x + (-y) ≤ 0" so we want -Σ x + y ≤ 0
            # Wait: rows_ub.append((matchable_p1, {y_idx(e_idx): -1.0}, 0.0))
            # means: Σ matchable_p1 contributes +1 each, plus y_idx contributes -1.0.
            # So constraint is: 1*Σ matchable - 1*y ≤ 0, i.e., y ≤ Σ matchable. WRONG direction.
            # Fix: row needs to be -Σ matchable + y ≤ 0.
            # Let me redo.
            pass
    # Actually, let me redo with sign convention clearer:
    # We want y[e] - Σ matchable_x_at_p1 ≤ 0
    # In LP: 1·y - Σ 1·x ≤ 0
    # Build accordingly
    ub_data, ub_row, ub_col = [], [], []
    b_ub_arr = []
    rcount = 0
    for e_idx, (pos1, pos2, dir_) in enumerate(ring_edges):
        if dir_ == "horizontal":
            s1, s2 = 1, 3
        else:
            s1, s2 = 2, 0
        c_left_colors = set()
        c_right_colors = set()
        for px in cell_to_p[pos1]:
            edges = placements[px][3]
            if edges[s1] != 0: c_left_colors.add(edges[s1])
        for px in cell_to_p[pos2]:
            edges = placements[px][3]
            if edges[s2] != 0: c_right_colors.add(edges[s2])
        shared_colors = c_left_colors & c_right_colors
        matchable_p1 = [px for px in cell_to_p[pos1] if placements[px][3][s1] in shared_colors]
        matchable_p2 = [px for px in cell_to_p[pos2] if placements[px][3][s2] in shared_colors]
        # y - Σ x_left ≤ 0
        ub_data.append(1.0); ub_row.append(rcount); ub_col.append(y_idx(e_idx))
        for px in matchable_p1:
            ub_data.append(-1.0); ub_row.append(rcount); ub_col.append(px)
        b_ub_arr.append(0.0); rcount += 1
        # y - Σ x_right ≤ 0
        ub_data.append(1.0); ub_row.append(rcount); ub_col.append(y_idx(e_idx))
        for px in matchable_p2:
            ub_data.append(-1.0); ub_row.append(rcount); ub_col.append(px)
        b_ub_arr.append(0.0); rcount += 1

    A_ub = coo_matrix((ub_data, (ub_row, ub_col)), shape=(rcount, n_vars)).tocsr()
    b_ub_a = np.array(b_ub_arr)

    bounds = [(0.0, 1.0)] * n_vars

    # Make r-variables integer (the x's)
    integrality = np.zeros(n_vars)
    for i in range(n_x):
        integrality[i] = 1

    print(f"\nSolving MIP (HiGHS via scipy)...")
    t0 = time.time()
    res = linprog(c_obj, A_ub=A_ub, b_ub=b_ub_a, A_eq=A_eq, b_eq=b_eq_a,
                  bounds=bounds, method="highs", integrality=integrality)
    elapsed = time.time() - t0
    print(f"Time: {elapsed:.2f}s")
    print(f"Status: {res.message}")
    if not res.success:
        print("MIP failed.")
        return

    score = -res.fun
    print(f"\n=== Shell-0 MIP score: {score:.2f} / 60 frame edges ===")

    # Decode the placement
    chosen = {}
    for idx in range(n_x):
        if res.x[idx] > 0.5:
            pid, pos, k, _ = placements[idx]
            chosen[pos] = (pid, k)
    # Save
    Path("output/vol-74").mkdir(parents=True, exist_ok=True)
    out = {
        "matched_shell0": int(score),
        "placement": [{"pos": pos, "piece_id": pid, "rotation": rot}
                      for pos, (pid, rot) in sorted(chosen.items())],
    }
    with open("output/vol-74/shell0_solution.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"Saved shell-0 solution to output/vol-74/shell0_solution.json")


if __name__ == "__main__":
    main()
