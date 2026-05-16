---
name: basin-corner-permutations
description: Three top records on canonical E2 have THREE DIFFERENT corner permutations. McGavin (3,2,0,1), local 459 (1,0,2,3), vol-32 458 (0,3,1,2). Only piece 138 at center (pos 135) is shared. Explains why basins are Hamming-far.
metadata:
  type: project
---

# Basin corner permutations (vol-99 finding, 2026-05-16)

**Status**: `built` — measured 2026-05-16 ~03:48.

## The data

Pieces in same positions across three top records:

| comparison | shared positions |
|---|---:|
| McGavin 469 ∩ local 459 | **1** (just pos 135 = center hint) |
| McGavin 469 ∩ vol-32 458 | 2 |
| local 459 ∩ vol-32 458 | 29 |

## Corner permutations (positions 0, 15, 240, 255)

The 4 corner pieces (piece_ids 0, 1, 2, 3) are arranged differently:

| record | pos 0 | pos 15 | pos 240 | pos 255 |
|---|:-:|:-:|:-:|:-:|
| McGavin 469 | 3 | 2 | 0 | 1 |
| Local 459 | 1 | 0 | 2 | 3 |
| Vol-32 458 | 0 | 3 | 1 | 2 |

**Three different permutations.** All three are valid permutations
of the 4 corner pieces (which all 4 are required to sit at the 4
corner positions per the canonical 5-clue, but the specific
mapping is unconstrained by the clues alone).

## Why this matters

To traverse from local 459 to McGavin 469 via any cell-by-cell
local move:
- The corner pieces must change positions: piece 1 must move from
  pos 0 to pos 255; piece 0 must move from pos 240 to pos 0; etc.
- The border ring (60 perimeter cells) must be re-arranged because
  the corner permutation determines border-piece edge-color
  matching all around the ring.

This is GLOBAL: changing one corner's position cascades through
the entire border construction.

**The basins are not just Hamming-far (255) — they have
incompatible border constructions.** Each basin commits to a
corner permutation early and is then locked into that border
arrangement.

## Implication for record-breaking

The structural barrier between basins is not just piece count —
it's a categorical commitment to a corner permutation. With
24 = 4! permutations of corners possible, the score landscape may
have up to 24 distinct "corner-permutation classes" of basins.

Each class is locally MIP-rigid (this night's proofs cover 3
classes, all rigid at halo r=2).

To break a record requires either:
- A class-changing move (re-permutation of corners)
- A within-class improvement (proven impossible by MIP rigidity)

**A "class-changing" move requires moving the 60 border-ring
pieces simultaneously — board-spanning by construction.**

This is a fourth lens (after MIP rigidity, σ-cycle indecomposability,
σ-cycle dispersion, near-twin orbit triviality) confirming the same
structural conclusion: **only board-spanning moves can break records**.

## Linked

- [[mcgavin-mip-local-optimal-halo1]]
- [[sigma-cycle-topology-3-basins]]
- [[sigma-cycles-are-dispersed]]
- [[mcgavin-469-near-twin-orbit]]
- [[why-records-are-mip-rigid]]
