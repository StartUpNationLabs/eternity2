---
name: mcgavin-joint-halo2-mip-result
description: "Vol-121 T3 — McGavin 469's 15-cell II-mismatch region + halo-2 (53 cells joint) ran HiGHS MIP for 1800s. Δ=0 found. CBC's B&B didn't close the LP-INT gap to optimality within the time budget (final BestBound=120.93 vs BestSol=113, gap=7%). Two interpretations: (1) the LP relaxation has 7-edge looseness that integer cannot close (i.e. McGavin halo-2 joint truly locked at 113) — most likely given vol-44/95/100 lineage; (2) an integer improvement exists but B&B couldn't find it in 30min. No record produced."
metadata:
  type: project
---

# McGavin halo-2 joint MIP timeout (vol-121 T3)

`repair_region` ran HiGHS MIP on McGavin 469's joint mismatch region
+ halo-2 (53 cells), full piece freedom across all 196 interior
pieces × 4 rotations.

**Result: Δ=0 after 1800s timeout. 200+ B&B nodes, gap=7%.** CBC
did NOT prove optimality (gap not closed), but found NO integer
solution improving on McGavin's current 113 sub-region matched
edges.

## Interpretation

The LP-relaxation BestBound stayed at 120.93 throughout. CBC explored
200+ nodes without finding integer ≥ 114.

Two possibilities:
1. McGavin halo-2 joint is truly locked at 113 — LP gap is
   relaxation looseness. Consistent with vol-44 / vol-95 / vol-100.
2. An integer improvement exists but B&B couldn't find it in 30 min.

Given the vol-83/100 lineage and consistent Δ=0 across related MIPs
(top-2, top-3, joint 15-cell, halo-1 on bseed9, halo-1 on v121-458),
interpretation #1 is more likely.

## What this proves

EMPIRICALLY: 30min HiGHS budget at 53-cell joint region with full
piece freedom found no improvement. NOT proven globally optimal.

## Linked

- [[corpus-restricted-region-mip-locked]]
- [[mcgavin-top3-mip-locked]]
- [[honest-status-vol121]]
- [[../sessions/vol-121]]
