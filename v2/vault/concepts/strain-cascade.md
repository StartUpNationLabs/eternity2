---
tags: [concept, structural, hypothesis]
status: built-hypothesis
origin-vol: 4
---

# Strain cascade hypothesis

**Status**: `built` (vol-4 observation + falsification framework); not directly tested
**Origin**: vol-4
**Files**: `scripts/strain_diagnostic.sh` (queued)

## Hypothesis

The asymmetric placement of the 5th canonical hint at **cell (7,8)** plus the 180-symmetric corner hints creates a directional "strain field" that warps the search backwards toward the south-central region. The universal-mismatch hotspot (rows 10-13, cols 4-13, vol-4) is the projection of this strain onto the score landscape.

## Evidence (vol-4)

- 29 plateau boards across 6 solver families.
- Top-6 universal-mismatch edges: prevalence 47-63% across boards.
- All hotspot in **rows 10-13, cols 4-13** (south-central).
- Distance from the (7,8) hint to hotspot center ≈ Manhattan 6.

## Falsification design (NIGHT5_ABSTRACT)

`strain_diagnostic.sh`: remove the (7,8) hint, re-run the solver portfolio, check if the hotspot persists.
- If hotspot moves: confirms strain-cascade is hint-asymmetry-driven.
- If hotspot stays: refutes; hotspot is generator-structural.

**Status**: queued at vol-4 close, never executed (vol-5+ pivoted to GA + border diversity).

## How vol-14 amended this

[[mismatch-geometry]] observation: the hard region depends on **scan order**, not just hint placement:
- Top-down → south-central.
- Bottom-up → top region (matches community 469).
- Spiral → corners.

→ Strain cascade is partially confounded with scan order. The (7,8) hint matters, but so does which cells the algorithm reaches first. A clean falsification needs to vary scan order *and* hint placement orthogonally.

## Implication

This hypothesis is unfalsified-but-mature. The vol-17 [[mismatch-geometry]] top-row finding fits both readings. To resolve: run strain-diagnostic across scan orders.

## Linked concepts

- [[mismatch-geometry]] — what the strain field produces
- [[scan-order]] — the orthogonal axis discovered later

## Linked memory

- NIGHT5_ABSTRACT (preprint draft)
- `project_e2_vol14_mismatch_geometry_universal`
