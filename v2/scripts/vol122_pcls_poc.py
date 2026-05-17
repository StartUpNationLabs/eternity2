#!/usr/bin/env python3
"""Vol-122 J4 — Per-Color Lagrangian Schedule (PCLS) PoC v2.

LEAN VERSION: edge-LP only (no per-cell-piece-rot variables).

State:
 - For each interior adjacency a (480 in total), z_{a,k} = LP indicator that
   the adjacency carries color k.
 - For each color k, supply_k = # piece-edges of color k available
   (after subtracting border-cell consumption).
 - Constraints:
   - z_{a,k} <= 1
   - sum_k z_{a,k} <= 1 for each a
   - sum_a z_{a,k} <= floor(supply_k / 2)  (vol-44 per-color bound)
   - PCLS addition: PIECE-USE balance. For each piece p, sum of edges-it-
     contributes-to-color-k z_{(.,k)} for incidences of p is bounded above
     by 4 (its 4 edges). This is the per-piece linking term — Lagrangian-
     relaxable.

LP solves fast since variables = 480 * 23 ~ 11k. Constraints similar order.

OUTPUT: writes a JSON dump with per-color shadow prices and a ranking of
adjacencies by LP-relaxed contribution. The output is INFORMATIONAL — it
tells us which COLORS are binding, not what to lock. The full PCLS would
then use this to choose a piece-supply direction.

This v2 is a sanity check on the LP feasibility direction. The full
schedule loop is a follow-up step once this LP is fast.
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from collections import defaultdict
from time import time

import pulp


def parse_color(s):
    v = int(s.strip(), 2)
    return 0 if v == 65535 else v


def load_puzzle(csv_path):
    pieces = []
    with open(csv_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    for line in lines[1:]:
        cols = line.split(',')
        if len(cols) >= 4:
            try:
                pieces.append((parse_color(cols[0]), parse_color(cols[1]),
                               parse_color(cols[2]), parse_color(cols[3])))
            except ValueError:
                pass
    return pieces


def rotate(edges, rot):
    return tuple(edges[(i - rot) % 4] for i in range(4))


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} BORDER_PARTIAL_JSON OUT_JSON")
        sys.exit(1)
    border_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])

    puzzle_csv = Path("../data/puzzles/size_16_official_eternity.csv")
    pieces = load_puzzle(puzzle_csv)
    side = 16

    with open(border_path) as f:
        border = json.load(f)
    placed = {}
    for entry in border.get("placement", []):
        if entry is None:
            continue
        placed[entry["pos"]] = (entry["piece_id"], entry["rotation"])
    print(f"border partial: {len(placed)} placed cells")

    # Compute supply_k: total color-k instances across ALL pieces, all rotations
    # but the piece can only be used once. So per piece, count = # rotations
    # where it presents color k on some side. Better: # piece-rotations where
    # the piece has color k on side 0..3. Each piece can be in 1 rotation
    # (chosen), but the supply for matching purposes is just: for each piece,
    # count #edges of color k. Total = sum_p count_k(p).
    # CORRECTED supply: free interior pieces contribute ALL their non-0 edges;
    # placed border pieces contribute their INTERIOR-FACING edges only (i.e.,
    # the edges that face into the 14x14 interior).
    used_pids = {pid for (pid, _r) in placed.values()}
    color_supply = defaultdict(int)
    # Free interior pieces
    for pid, edges in enumerate(pieces):
        if pid in used_pids:
            continue
        for e in edges:
            if e != 0:
                color_supply[e] += 1
    # Placed border pieces: their interior-facing edges contribute too
    for pos, (pid, rot) in placed.items():
        r, c = pos // side, pos % side
        re = rotate(pieces[pid], rot)
        # Which sides face interior?
        # If r==0 → bottom-side (index 2) faces interior
        # If r==side-1 → top-side (index 0) faces interior
        # If c==0 → right-side (index 1) faces interior
        # If c==side-1 → left-side (index 3) faces interior
        # Corner cells face interior on 2 sides; we need both.
        # For a typical edge (not corner) cell: 1 interior-facing side + 2 sides
        # facing adjacent border pieces (already 60 matched assumes those are
        # color-matched). For corners: 2 interior-facing sides.
        # NOTE: the "side faces interior" rule needs cell position; for the
        # general top-row edge cell at (0, c) with 1 < c < side-1, the sides
        # are: top(0)=BORDER, right(1)=interior-or-next-border, bottom(2)=interior,
        # left(3)=prev-border-or-interior. Actually: right/left face the
        # neighbor on the SAME ROW, which IS another border cell. So:
        # top-row non-corner: only side 2 (bottom) faces interior.
        # Corner (0,0): sides 1 (right) face next-top-border + side 2 (bottom) face interior.
        # So corners have 1 interior-facing side too (only the diagonal one
        # faces interior). Wait no. Corner (0,0):
        # - top  (0): BORDER (color 0)
        # - right(1): next-top-border at (0,1) — also border cell
        # - bottom(2): row-1 cell at (1,0) — also border cell (col 0)
        # - left (3): BORDER (color 0)
        # So corners face NO interior! Their 2 non-border sides face adjacent
        # border cells.
        # So only edge cells (non-corner border) face the interior at 1 side.
        # That's 56 cells × 1 side = 56 interior-border adjacencies.
        is_corner = (r in (0, side-1)) and (c in (0, side-1))
        if is_corner:
            continue
        if r == 0:
            interior_facing_side = 2  # bottom
        elif r == side - 1:
            interior_facing_side = 0  # top
        elif c == 0:
            interior_facing_side = 1  # right
        elif c == side - 1:
            interior_facing_side = 3  # left
        else:
            continue
        e = re[interior_facing_side]
        if e != 0:
            color_supply[e] += 1
    print(f"interior-piece colors (max color = {max(color_supply)}):")
    for k in sorted(color_supply):
        print(f"  color {k:2d}: supply {color_supply[k]:3d}, ub_matches floor({color_supply[k]}/2) = {color_supply[k] // 2}")
    print(f"  SUM UB = {sum(s // 2 for s in color_supply.values())}")

    # Build LP
    # adjacencies = all interior-interior + interior-border (but not border-border)
    adjacencies = []
    for r in range(side):
        for c in range(side - 1):
            p1, p2 = r * side + c, r * side + c + 1
            if p1 in placed and p2 in placed:
                continue  # border-border, already settled
            adjacencies.append((p1, 1, p2, 3))
    for r in range(side - 1):
        for c in range(side):
            p1, p2 = r * side + c, (r + 1) * side + c
            if p1 in placed and p2 in placed:
                continue
            adjacencies.append((p1, 2, p2, 0))
    print(f"adjacencies (non-border-border): {len(adjacencies)}")

    prob = pulp.LpProblem("pcls_v2", pulp.LpMaximize)
    z = {}  # (adj_idx, color) -> var
    for a_idx, (p1, s1, p2, s2) in enumerate(adjacencies):
        feasible_colors = set()
        if p1 in placed:
            pid1, rot1 = placed[p1]
            re1 = rotate(pieces[pid1], rot1)
            feasible_colors.add(re1[s1])
        else:
            feasible_colors = set(color_supply)  # any interior color possible
        if p2 in placed:
            pid2, rot2 = placed[p2]
            re2 = rotate(pieces[pid2], rot2)
            feasible_colors &= {re2[s2]}
        feasible_colors.discard(0)
        for k in feasible_colors:
            z[(a_idx, k)] = pulp.LpVariable(f"z_{a_idx}_{k}", lowBound=0, upBound=1)

    print(f"z-vars: {len(z)}")

    # One color per adjacency
    for a_idx in range(len(adjacencies)):
        terms = [z[(a_idx, k)] for k in color_supply if (a_idx, k) in z]
        if terms:
            prob += pulp.lpSum(terms) <= 1, f"adj_{a_idx}"

    # Color supply: each adjacency consumes 2 color-k edges
    color_cons = {}
    for k in color_supply:
        terms = [z[(a_idx, k)] for a_idx in range(len(adjacencies)) if (a_idx, k) in z]
        if terms:
            color_cons[k] = prob.addConstraint(
                pulp.lpSum(terms) * 2 <= color_supply[k], name=f"color_{k}"
            )

    # Objective
    prob += pulp.lpSum(z.values())

    print("solving LP...")
    t0 = time()
    prob.solve(pulp.HiGHS(msg=False))
    elapsed = time() - t0
    status = pulp.LpStatus[prob.status]
    obj = pulp.value(prob.objective)
    print(f"LP status={status}, obj={obj:.4f}, elapsed={elapsed:.1f}s")

    if status != "Optimal":
        print("not optimal; exiting")
        return

    # Compute color usage and binding status
    print("\nPer-color usage:")
    duals = {}
    binding_cols = []
    for k in sorted(color_supply):
        used = sum(pulp.value(z[(a_idx, k)]) or 0
                   for a_idx in range(len(adjacencies)) if (a_idx, k) in z)
        is_binding = abs(used * 2 - color_supply[k]) < 0.5
        if is_binding:
            binding_cols.append(k)
        cap = color_supply[k] // 2
        duals[k] = used  # not actual dual, just the LP value
        print(f"  color {k:2d}: ub_matches={cap}  used={used:6.2f}  {'BINDING' if is_binding else ''}")
    print(f"  binding colors: {binding_cols}")

    # Dump
    out = {
        "source": "vol122_pcls_v2",
        "border_input": str(border_path),
        "lp_obj": obj,
        "lp_elapsed_s": elapsed,
        "n_zvars": len(z),
        "n_adjacencies": len(adjacencies),
        "duals": duals,
        "color_supply": dict(color_supply),
        "color_ub_matches": {k: v // 2 for k, v in color_supply.items()},
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
