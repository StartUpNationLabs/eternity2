---
name: y-linearisation-cell-fractional-gap
description: The canonical-E2 border LP optimum has UB ≈ 478 but the integer
status: built
metadata:
  type: concept
---
# y-linearisation cell-fractional gap

**Status**: `built` (math + worked example) — vol-54 (2026-05-15).
**Origin**: Vol-54 reconciliation of vol-50 (anatomy) vs vol-53 (refutation).

## The phenomenon

The canonical-E2 border LP optimum has UB ≈ 478 but the integer
optimum is ≤ 458. Vol-44 measured this on multiple basins (~20-point
gap uniformly). The mechanism for the gap is:

**Even with piece-uniqueness (`Σ_c x[p, c] = 1` per piece) and cell-
coverage (`Σ_p x[p, c] = 1` per cell) satisfied as equalities, the LP
relaxation can choose CELL-FRACTIONAL assignments to maximise the
edge-matching y-objective. Integer x cannot reproduce these.**

## Minimal worked example

2 cells `c1, c2` adjacent in a row, 2 pieces:
- P1 sides (N, E, S, W) = (1, 1, 1, 1)
- P2 sides             = (2, 2, 2, 2)

**Integer best = 0** (any integer assignment gives edge colour mismatch).

**LP best = 1** at t = x[P1, c1] = 0.5 (each piece evenly split across cells):
- y[1] = min(x[P1, c1], x[P1, c2]) = min(0.5, 0.5) = 0.5
- y[2] = min(x[P2, c1], x[P2, c2]) = min(0.5, 0.5) = 0.5
- Σ y = 1.0, hits the per-edge cap.

**Gap = 1.0** on a 1-edge problem.

Verified analytically (`/tmp/vol54_t2.py`) and with HiGHS LP solver
(`/tmp/vol54_t2_verify.py`).

## Why the assignment polytope being TU doesn't help

The Birkhoff-von Neumann theorem says the assignment polytope (one
piece per cell, one cell per piece) is totally unimodular: for any
linear objective on x, the LP optimum is at an integer vertex.

But the y-objective is **min-of-sums of x**, not linear. The y-LP
relaxes y via:
```
y[c, c', k] ≤ Σ_{(p, r): east-side colour k} x[p, c, r]
y[c, c', k] ≤ Σ_{(p, r): west-side colour k} x[p, c', r]
```

`min(a, b)` is concave in x. The y-LP can therefore prefer x at a
non-extreme point of the assignment polytope. TU helps for linear
objectives on x; it does NOT help when y depends on x via min.

## Why per-piece column-generation alone doesn't close it

Vol-52's design (per-piece column-gen) replaces `Σ_{c, r} x[p, c, r] = 1`
with `Σ_z z[p, z] = 1` where z's are convex combinations of integer
placements (cell, rotation) for piece p.

This restricts the **rotation-level fractionality**: for a given cell
c, x[p, c] = Σ_{r: (c,r) is a placement} (some z[p, *]) is constrained.

But it doesn't restrict the **cell-level fractionality**: x[p, c] can
still be 0.5 if half the z-mass for piece p lives in placements at c1
and the other half at c2.

In the worked example, P1 has 4 rotations all identical (sides all =
1). So the convex hull per piece has 1 vertex per cell × 4 rotations
≈ 4 vertices, all giving the same edge-colour profile. Column-gen
doesn't add any tightening here; the cell-fractional t = 0.5 remains.

## How the gap actually closes

To close: enforce **x ∈ {0, 1}** at the cell level. Standard MIP
techniques:

1. **Branch-and-bound on x[p, c]** — branches `x[p, c] = 0` or
   `x[p, c] = 1`, eliminating fractional cell assignments. With
   column-gen on rotations, this is **branch-and-price-and-cut**.

2. **y-tightening cuts** — e.g., for each edge `(c, c')` and integer
   "fault" subsets, derive a cut on y that's tight only at integer x.

3. **Set-partitioning master LP** — enumerate compatible
   piece-rotation-cell triples in groups (e.g., row by row) and use
   each as a column. Larger columns, fewer rows, but combinatorial
   blow-up.

(2) is the cheap option: ~1-2 weeks of careful work, vs (1) at 3-4
weeks. (3) is the most powerful but most engineering-heavy.

## Practical consequence

Vol-44's border-MIP approach (~1h per basin, integer feasibility via
HiGHS) already does (1) and confirms vol-32 458 board's local
optimality. The LP-478 vs integer-458 gap is **information about LP
looseness**, not a record-breaking lever.

The cell-fractional gap is intrinsic to the LP relaxation of any
assignment-with-edge-matching problem. It does NOT reflect a
suboptimality in our search algorithms.

## Linked

- [[lp-integer-gap-anatomy]] — vol-50 anatomy (numerics intact, interpretation amended)
- [[lifted-lp-column-gen-per-piece]] — vol-52 per-piece design (insufficient for this gap)
- [[per-piece-column-gen-6x6-worked]] — vol-53 refutation, made precise by vol-54
- [[lp-ub-478-basins]] — vol-44 basin LP UB landscape
- [[border-enum-lp-ub]] — vol-44 LP formulation

## Linked memory

- (none new; existing E2-state and LP-anatomy memories remain accurate)
