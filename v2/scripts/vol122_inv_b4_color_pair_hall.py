#!/usr/bin/env python3
"""Vol-122 INVENTION B4 — color-pair supply Hall-condition check.

Goal: tighten vol-44's color-UB = 480 by adding piece-uniqueness.

Setup:
- 16x16 board has 480 internal adjacencies (240 horizontal + 240 vertical).
- 4 corner pieces (2 BORDER edges each), 56 edge pieces (1 BORDER edge),
  196 interior pieces (0 BORDER edges).
- Each piece has 4 edges. Total piece edges = 1024.
- BORDER-facing edges (color=0): 4*2 + 56*1 + 196*0 = 64.
- Color k > 0 instances (across all piece-rotations): let N_k be this.

For a matched internal adjacency of color k:
- One piece contributes color-k edge facing right (or down).
- The adjacent piece contributes color-k edge facing left (or up).
- BOTH pieces must be used (piece-uniqueness).

Per-color UB (vol-44 style): floor(N_k / 2).
Per-color sum UB: sum_k floor(N_k / 2) = 480 (vol-44).

Hall refinement:
- The interior-facing-edge supply per cell-class is bounded.
- 4 corners: 2 interior-facing edges each = 8.
- 56 edge pieces: 3 interior-facing edges each = 168.
- 196 interior pieces: 4 interior-facing edges each = 784.
- Total interior-facing supply = 960. ✓ (matches 2*480)

Per-color-pair (k, l) where l = k (matched):
- Slots on board = number of internal adjacencies where BOTH edges = color k.
- Demand per color k = #(adjacencies of color k in the maximum-matched board).
- For UB calc: assume all adjacencies of color k are matched → demand = M_k.
- Sum_k M_k = 480 if all matched.
- We need 2*M_k color-k instances. Supply = N_k. So 2*M_k <= N_k → M_k <= floor(N_k/2).

That's just vol-44.

REFINEMENT 1 — PIECE-USE FRACTIONAL CONSTRAINT:
- Each piece used at most once. Each piece contributes to potential matches
  at exactly 2 adjacent cells (depending on placement).
- If piece p contributes color k on side s, then placing p uses up that
  color-k-on-side-s instance.
- Side-bipartite Hall: for each color k, count instances per side
  (top/right/bottom/left). At a horizontal adjacency, we need a right-edge
  color k facing a left-edge color k. So supply_h(k) = min(#right-k, #left-k).
- Sum of horizontal matches of color k ≤ supply_h(k).
- Similarly supply_v(k) = min(#top-k, #bottom-k).
- Total matches of color k = matches_h(k) + matches_v(k)
  ≤ supply_h(k) + supply_v(k).

If sum_k [supply_h(k) + supply_v(k)] < 480, we have a tighter UB.

This is INVENTION B4. Let's compute.
"""

from __future__ import annotations
import sys
from collections import Counter
from pathlib import Path

def parse_color(s):
    v = int(s.strip(), 2); return 0 if v == 65535 else v

def load_puzzle(csv_path):
    pieces = {}
    with open(csv_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    pid = 0
    for line in lines[1:]:
        cols = line.split(',')
        if len(cols) >= 4:
            try:
                pieces[pid] = (parse_color(cols[0]), parse_color(cols[1]),
                               parse_color(cols[2]), parse_color(cols[3]))
                pid += 1
            except ValueError:
                pass
    return pieces

def rotate(edges, rot):
    t, r, b, l = edges
    return [(t,r,b,l),(l,t,r,b),(b,l,t,r),(r,b,l,t)][rot]

def main():
    pieces = load_puzzle(Path("../data/puzzles/size_16_official_eternity.csv"))
    print(f"# Pieces loaded: {len(pieces)}", file=sys.stderr)

    # Count, for each color k > 0, the instances on each side (T,R,B,L)
    # across all (piece, rotation) options. But each piece is used at most
    # ONCE, so we can choose ONE rotation per piece. The supply per side
    # depends on rotation choice — this is where Hall enters.
    #
    # For a STATIC UB, we use the rotation-FREE count: count edges of
    # color k regardless of side. Then per-side supply = total_color_k / 4
    # on average IF rotations are free.
    #
    # Tighter: per-piece, after a rotation choice, that piece's edges land
    # on specific sides. We want to MAXIMIZE supply_h(k) + supply_v(k)
    # summed over k. This is itself an OPTIMIZATION problem (pick a
    # rotation for each piece).

    # Step 1: count total color instances (rotation-blind)
    color_total = Counter()
    for pid, e in pieces.items():
        for c in e:
            if c > 0:
                color_total[c] += 1
    print(f"\n# Total color instances (rotation-blind):")
    for k in sorted(color_total):
        print(f"  color {k}: {color_total[k]} instances")
    total_nonborder = sum(color_total.values())
    print(f"  TOTAL: {total_nonborder} non-BORDER edges")
    print(f"  (Verify: 1024 - 64 BORDER = 960 = 2*480 ✓: {total_nonborder == 960})")

    # Vol-44 baseline
    ub_vol44 = sum(c // 2 for c in color_total.values())
    print(f"\n# Vol-44 color-UB = sum floor(N_k/2) = {ub_vol44}")

    # Step 2: per-side counts at FIXED canonical rotation (rotation 0).
    # This shows the "natural" distribution.
    by_side = [Counter(), Counter(), Counter(), Counter()]  # T, R, B, L
    for pid, e in pieces.items():
        t, r, b, l = e
        if t > 0: by_side[0][t] += 1
        if r > 0: by_side[1][r] += 1
        if b > 0: by_side[2][b] += 1
        if l > 0: by_side[3][l] += 1

    print(f"\n# Per-side counts at canonical rotation (rot=0):")
    print(f"  {'color':>5} {'T':>4} {'R':>4} {'B':>4} {'L':>4} {'TOT':>4}")
    for k in sorted(color_total):
        print(f"  {k:>5} {by_side[0][k]:>4} {by_side[1][k]:>4} "
              f"{by_side[2][k]:>4} {by_side[3][k]:>4} "
              f"{by_side[0][k]+by_side[1][k]+by_side[2][k]+by_side[3][k]:>4}")

    # Per-side static UB (rotation 0):
    # horizontal matches of color k <= min(R-facing color k, L-facing color k)
    # vertical matches of color k <= min(B-facing color k, T-facing color k)
    print(f"\n# Per-color static-rotation UB (rot=0 only):")
    print(f"  {'color':>5} {'h_ub':>5} {'v_ub':>5} {'sum':>5} {'vol44':>6}")
    total_static = 0
    for k in sorted(color_total):
        h = min(by_side[1][k], by_side[3][k])
        v = min(by_side[2][k], by_side[0][k])
        s = h + v
        total_static += s
        print(f"  {k:>5} {h:>5} {v:>5} {s:>5} {color_total[k]//2:>6}")
    print(f"  TOTAL static-rotation UB = {total_static}")
    print(f"  Vol-44 (rotation-free) UB = {ub_vol44}")
    print(f"  Static < vol44 means rotations are FORCED to be different per piece.")
    print(f"  (Note: pieces CAN rotate freely; this is just rotation=0 supply.)")

    # Step 3: ROTATION-FREE per-side supply.
    # For each piece, we can pick rotation to maximize match potential.
    # Across all rotations, each piece's color k edges can land on any side.
    # Treating each rotation as a "rotation choice", the supply of color k
    # on side s is: for each piece, max over rotation of "is color k on side s".
    #
    # But each piece picks ONE rotation. So supply per side is an optimization:
    # maximize total matchable edges subject to one-rotation-per-piece.

    # Simpler upper bound: for each color k and side s, count distinct pieces
    # that have color k somewhere (i.e. can rotate to put color k on side s).
    # This gives an UPPER bound on per-side supply.

    pieces_with_color = {k: [pid for pid, e in pieces.items() if k in e] for k in color_total}
    print(f"\n# Pieces having color k SOMEWHERE (upper bound on per-side supply):")
    print(f"  {'color':>5} {'#pieces':>8} {'has-color/N_k':>14}")
    for k in sorted(color_total):
        pcount = len(pieces_with_color[k])
        print(f"  {k:>5} {pcount:>8} {pcount}/{color_total[k]}")

    # Step 4: TIGHT per-side per-color supply via LP (or by-hand argument).
    #
    # Define x_p_r ∈ {0,1}: piece p uses rotation r.
    # Constraint: sum_r x_p_r = 1 for each p.
    # Supply of color k on side s = sum over (p, r) such that piece p in
    # rotation r has color k on side s, of x_p_r.
    #
    # Max color-k matches = min(supply_h(k), supply_v(k)) for h/v split:
    #   horizontal matches need R-side and L-side: min(sup_R(k), sup_L(k))
    #   vertical matches need B-side and T-side: min(sup_B(k), sup_T(k))
    #
    # Goal: maximize sum_k [min(sup_R, sup_L)_k + min(sup_B, sup_T)_k]
    # subject to one-rotation-per-piece.
    #
    # This is a CONCAVE objective (min of linear in x). Tractable via LP
    # with auxiliary variables: y_k_h <= sup_R(k), y_k_h <= sup_L(k),
    # max sum (y_k_h + y_k_v).

    print(f"\n# Step 4: setting up LP for tight per-side per-color supply...")
    try:
        import pulp
    except ImportError:
        print("pulp not available; skipping LP step", file=sys.stderr)
        return

    prob = pulp.LpProblem("color_pair_hall", pulp.LpMaximize)

    # Rotation choice vars
    x = {}
    for pid in pieces:
        for r in range(4):
            x[(pid, r)] = pulp.LpVariable(f"x_{pid}_{r}", cat="Binary")
        prob += pulp.lpSum(x[(pid, r)] for r in range(4)) == 1, f"one_rot_{pid}"

    # Per-color, per-side supply
    # sup[(k, side)] is a LINEAR expression in x.
    # Goal vars y_k_h, y_k_v (continuous, since they're bounded by mins)
    y_h = {}
    y_v = {}
    for k in color_total:
        y_h[k] = pulp.LpVariable(f"yh_{k}", lowBound=0)
        y_v[k] = pulp.LpVariable(f"yv_{k}", lowBound=0)

    # Build per-side supply expressions
    # side index: 0=T, 1=R, 2=B, 3=L
    for k in color_total:
        sup_T = pulp.lpSum(x[(pid, r)] for pid in pieces for r in range(4)
                           if rotate(pieces[pid], r)[0] == k)
        sup_R = pulp.lpSum(x[(pid, r)] for pid in pieces for r in range(4)
                           if rotate(pieces[pid], r)[1] == k)
        sup_B = pulp.lpSum(x[(pid, r)] for pid in pieces for r in range(4)
                           if rotate(pieces[pid], r)[2] == k)
        sup_L = pulp.lpSum(x[(pid, r)] for pid in pieces for r in range(4)
                           if rotate(pieces[pid], r)[3] == k)
        # y_h <= min(sup_R, sup_L)
        prob += y_h[k] <= sup_R, f"yh_R_{k}"
        prob += y_h[k] <= sup_L, f"yh_L_{k}"
        # y_v <= min(sup_B, sup_T)
        prob += y_v[k] <= sup_B, f"yv_B_{k}"
        prob += y_v[k] <= sup_T, f"yv_T_{k}"

    # Objective
    prob += pulp.lpSum(y_h[k] + y_v[k] for k in color_total)

    # ADDITIONAL geometric cap: total horizontal matches ≤ 240 (there are
    # only 240 horizontal adjacencies on a 16×16). Similarly vertical ≤ 240.
    prob += pulp.lpSum(y_h[k] for k in color_total) <= 240, "geom_h"
    prob += pulp.lpSum(y_v[k] for k in color_total) <= 240, "geom_v"

    print(f"# LP: {len(x)} x-vars, {len(y_h)+len(y_v)} y-vars, "
          f"{len(prob.constraints)} constraints",
          file=sys.stderr)

    solver = pulp.PULP_CBC_CMD(timeLimit=180, msg=False)
    prob.solve(solver)

    status = pulp.LpStatus[prob.status]
    obj = pulp.value(prob.objective)
    print(f"\n# LP status: {status}, objective (UB on matched-edges) = {obj}")
    print(f"# Vol-44 baseline: {ub_vol44}")
    if obj is not None and obj < ub_vol44:
        print(f"# *** TIGHTENED: {ub_vol44} → {obj:.2f} ({ub_vol44 - obj:.2f} edges) ***")
    elif obj is not None and obj < 480:
        print(f"# *** TIGHTENED below 480: {obj:.2f} (vol-44 was {ub_vol44}, this is per-side Hall) ***")
    else:
        print(f"# Not tightened (LP says supply is sufficient).")

    print(f"\n# Per-color (h_ub, v_ub) at LP optimum:")
    print(f"  {'color':>5} {'y_h':>6} {'y_v':>6} {'sum':>6} {'vol44_max':>9}")
    for k in sorted(color_total):
        h = pulp.value(y_h[k]) or 0
        v = pulp.value(y_v[k]) or 0
        print(f"  {k:>5} {h:>6.2f} {v:>6.2f} {h+v:>6.2f} {color_total[k]//2:>9}")

if __name__ == "__main__":
    main()
