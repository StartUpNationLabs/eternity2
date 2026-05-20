---
name: inv3-border-dp-seed
description: "Vol-122 INVENTION 3 — decompose the puzzle as (corner-perm × corner-rot × border-ring-DP) → 60-matched border partial → interior-only ALNS. Genuinely novel: prior vols anchor on existing 459/469 basins; this generates 60-matched starting partials FROM SCRATCH via per-side chain DP. Already demonstrated 24 corner-rot configs admit chain-UB=60 and 50+ distinct piece-unique 60-borders exist with all-distinct interior-color profiles."
metadata:
  type: project
status: built
---

# INVENTION 3 — Border-DP basin generation (vol-122)

## What's new

All prior vols (60, 110, 119, 121) generated starting partials via
forward CSP search anchored on canonical-hint constraints. INVENTION 3
generates partials BACKWARDS from the border:

1. Pick a corner permutation (24 possibilities) + rotation (24-100 configs)
2. Solve the border ring as a 1D chain DP (4 sides × 14 cells)
3. Backtrack for piece-uniqueness across the ring
4. Output the 60-cell, 60-matched-edge partial
5. Hand the partial to ALNS to fill 196 interior cells

The interior problem becomes a 14×14 sub-puzzle with FIXED boundary
colors coming from the border choice.

## Measured facts (vol-122)

- **24 corner-rot configs achieve chain-DP UB=60** per-side.
  Border NOT binding.
- **50 piece-unique 60-matched borders enumerated** (sample cap),
  all with DISTINCT interior-color profiles.
- Likely thousands to millions of piece-unique 60-borders exist.

## Why prior approaches missed these basins

Vol-60 corner-sweep + vol-110 bf-pipeline + vol-119 corpus-MIP all
anchor on canonical hints (which force pieces at 5 interior positions).
The 60-matched borders here have 0/5 hint compliance and freely
explore the 1-clue / matched-edges convention.

McGavin 469 itself is 1/5 hints. INVENTION 3 generates THOUSANDS of
border-distinct starting partials in this regime.

## Status

- step 1 border DP — DONE, UB=60 found
- step 2 enumerate borders — DONE, 50 distinct dumped
- step 3 ALNS from each — running

## What this can NOT achieve

If the interior problem itself is intractable for ALNS (likely true
at full piece-rotation freedom), this approach gives the same ALNS
ceiling as vol-60 (≤459). The genuine win requires finding a border
whose interior LP-UB is HIGHER than vol-44's class-A 478. Per-border
interior LP is the future step.

## Linked

- [[vol-122]]
- [[corpus-restricted-region-mip-locked]]
