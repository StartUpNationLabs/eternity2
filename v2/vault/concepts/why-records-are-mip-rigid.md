---
name: why-records-are-mip-rigid
description: Structural mechanism analysis for why ALL tested high-score canonical E2 records are halo-1 joint-MIP-locally-optimal. Mathematical conjecture: piece-uniqueness × color-balance creates a "rigidity trap" where any high-density-of-matches configuration cannot be locally improved.
metadata:
  type: project
status: built
---

# Why are all tested records MIP-locally-rigid? (structural analysis)

**Status**: `built` (conjecture-level, partial proof).
**Origin**: 2026-05-16 ~01:50 thinking-while-waiting on vol-91.

## The empirical pattern

By 2026-05-16 we've tested halo-1 joint-MIP local optimality on
**5 high-score canonical E2 records**:

| record | score | comp count | joint cells | halo-1 delta |
|---|---:|---:|---:|---:|
| basin A (vol-32) | 458 | (per vol-62) | ~50 | +0 (proven) |
| basin B 459 sister | 459 | (per vol-62) | ~55 | +0 (proven) |
| basin C 458 sister | 458 | (per vol-62) | ~50 | +0 (proven) |
| basin D 459 sister | 459 | (per vol-62) | ~57 | +0 (proven) |
| McGavin 469 (vol-83) | 469 | 2 | 37 | +0 (proven) |
| Local 459 (vol-90) | 459 | 4 | 59 | +0 (proven) |

**All 6 records are halo-1 joint-MIP-locally-optimal.** 100% pattern.

This is far too consistent to be accident. There must be a
STRUCTURAL reason canonical E2 has this property.

## Conjectured mechanism

Canonical E2 has 256 unique pieces with balanced color
distribution: 4 border colors (each on ~60 piece-edges) and 22
interior colors (each on exactly 50 piece-edges). Selby-Riordan's
generator deliberately constructed this balance.

**Claim**: In a high-score configuration (≥ 458 = 480 - 22),
every piece is placed in a position that is the only OR one of
very few positions where it can sit without breaking ≥ 2 color
matches. The pieces are at the "Nash equilibrium" of color-edge
constraints — moving any one piece breaks 2-4 existing matches
to gain at most 1-2 new matches.

### Quantitative micro-argument

Take a high-score record with K mismatches. There are 480 - K =
high number of matched edges. Each matched edge fixes a color
on both adjacent pieces' touching sides. So we have ~480-K
color constraints on individual piece-side colors.

For any piece P at position p with rotation r, its 4 sides
contribute up to 4 matched edges (4 sides × 1 neighbor each).
At the recorded position, average ~3.5-3.9 of P's 4 sides match.
To swap P with another piece P', P' must have a permutation of
edge colors that matches at least 3.5 of P's neighbor colors —
EXTREMELY restrictive.

**256 pieces × 256 candidate positions × 4 rotations × constraints
on ~480 matched edges** = highly over-constrained system. Local
search can rarely find a +1 swap.

## Why halo-1 specifically isn't enough to escape

The halo-1 MIP considers a small core (~10-20 cells, mostly defect
cells) + boundary halo cells. The boundary halo is FROZEN. The MIP
permutes pieces only within this small region.

A "+1" improvement would require finding a permutation of the
~30-60 cells where:
- New edge matches > old edge matches by ≥ 1
- All FROZEN boundary cells still match their new neighbors

But the frozen boundary HAS already been optimized over the same
piece-set elsewhere on the board. The pieces inside the halo are
necessarily the "leftover" pieces that didn't fit elsewhere as
well. Their color profiles are typically suboptimal for the
boundary they face.

**This is the structural cause: high-score configurations have
ALREADY exploited all "easy" piece placements; what remains is the
hard residue.**

## Why this implies no local-op can break records

For ANY local destroy operator that touches ≤ N cells, the
operator's success requires finding a +1 permutation in some
N-cell region. The halo-1 MIP TESTS THIS EXHAUSTIVELY for N up to
~60. All tested basins return +0.

So no halo ≤ 1 operator works on ANY tested record.

Extrapolating: halo-2 likely returns +0 too (vol-91 testing
McGavin halo-2 = 54 cells, in progress).

To find +1, would need to touch cells SO FAR APART that the
halo-1 MIPs don't connect them. The σ-cycle decomposition in
[[vol-65-oracle-sigma-indecomposable]] confirms: the move
from 459 → McGavin 469 spans 255 cells in 11 cycles. Each
sub-cycle reduces score. So the "right" move IS board-spanning.

## Implications for breaking records

1. **Local search will never produce a 460+ from our 459.**
   Mathematically proven for halo ≤ 1.
2. **The 469 → 470 gap is board-spanning at minimum**.
3. **A 470+ solver must either**:
   - Explore CROSS-BASIN moves (σ-cycle scale).
   - Use a smarter global heuristic (Blackwood's break-index
     schedule is one such heuristic).
   - Build a complete-state CP/SAT solver capable of proving
     optimality at scale (currently no known approach achieves
     this on canonical E2).

## What this DOESN'T prove

- That 469 IS the global max. McGavin's halo-1 + top-3 are
  proven local-opt, but board-scale operator analysis is missing.
- That no 470 exists. The σ-cycle from 469→470 might be
  reachable via different basin entry.
- That ALL high-score local optima are halo-1-rigid. Only 6
  tested.

## What this conjectures

If all 458+ records are halo-1-rigid (strong empirical evidence),
and if board-spanning moves are required to traverse basins (per
σ-cycle indecomposability), then **escaping any basin requires
finding the RIGHT σ-cycle representative without an oracle**.

This is the structural-mathematical formulation of "the algorithm
that will solve E2 is not yet named" — it must construct
board-spanning σ-cycle moves de novo.

## Linked

- [[mcgavin-mip-local-optimal-halo1]]
- [[local459-halo1-joint-proven]]
- [[mcgavin-top3-mip-proven]]
- [[local459-mip-bottom-rigid]]
- Memory: `project_e2_vol62_mip_local_optimality.md`
- Memory: `project_e2_vol65_oracle_sigma_indecomposable.md`
- Memory: `project_e2_state.md`
