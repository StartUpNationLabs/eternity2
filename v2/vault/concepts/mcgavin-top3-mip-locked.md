---
name: mcgavin-top3-mip-locked
description: "Vol-121 T5 — McGavin 469's top-3 rows (42-cell joint region) PROVEN MIP-LOCALLY-OPTIMAL under full piece freedom. HiGHS MIP closed in 818s, Δ=0 with optimality certificate. To break McGavin via top-3-rows rearrangement is provably IMPOSSIBLE within full puzzle's piece set. The 10 II-mismatches in McGavin's top rows are joint-locally rigid."
metadata:
  type: project
---

# McGavin top-3 rows MIP-locked (vol-121 T5)

`repair_region` ran HiGHS MIP on McGavin 469's top-3 interior rows
(y ∈ {1,2,3}, x ∈ {1..14}), 42 cells, freed with full piece freedom
across all 196 interior pieces × 4 rotations.

**Result: Δ=0 in 818s, 110 B&B nodes, optimality proven.**

Sub-region BestSol=93, LP-relaxation BestBound=93.83. CBC closed the
gap and proved no integer assignment ≥ 94 exists.

## What this proves

The 10 II-mismatch edges in McGavin's top rows (vol-82 measurement)
CANNOT be fixed by any joint permutation of pieces in those top-3
rows. To improve McGavin's score by even +1 via top-row rearrangement
is **provably impossible** within the 42-cell joint region.

## What this does NOT prove

- McGavin may still be improvable by a region SPANNING rows 1-5+
  (top-5-rows MIP still in progress at 0% B&B).
- McGavin may admit an "exotic" big-region rearrangement (vol-44/95
  ruled out halo ≤ 4 per-component; joint halo-5+ untested).

## Strengthens vol-44 / vol-83 / vol-95 / vol-100 line

Vol-83 (37 cells, McGavin halo-1, 895s, Δ=0).
Vol-92 (McGavin halo-2 per-component, Δ=0).
Vol-94 (McGavin halo-3 per-component, Δ=0).
Vol-96 (McGavin halo-4 comp 0 = 57 cells, Δ=0).

This (vol-121 T5): McGavin top-3 rows joint 42-cell, Δ=0, optimality
**proven** (gap=0). Adds to the rigidity proof line.

## Linked

- [[corpus-restricted-region-mip-locked]]
- [[honest-status-vol121]]
- [[../sessions/vol-121]]
