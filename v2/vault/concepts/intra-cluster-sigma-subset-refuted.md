---
name: intra-cluster-sigma-subset-refuted
description: "Vol-118 — even intra-Cluster-A σ-cycle subset application with δ=+1 target (459→460) cannot escape via ALNS. Tested 3-cycle decomposition between bseed1_459 and bseed9_460: cycles sized 21, 14, 4 (total 39 cells). Individual cycles drop score by 9-11. Pairs reach 442-454. Even from a 451 partial (after applying 2 of 3 cycles), 15 ALNS configs (5 seeds × 3 ops) recover to 459 max. The bseed9 460 is an outlier; not reliably reproducible from cycle-subset application + ALNS."
metadata:
  type: project
---

# Intra-cluster σ-subset bridge — REFUTED (vol-118)

**Status**: `refuted` 2026-05-16.

## Hypothesis

Vol-118 T1 found intra-Cluster-A σ-cycles are small (max 9-25 cells)
and σ-boundary ratios are low (2-3.5 per cell). Hypothesis: applying
INTRA-cluster σ-cycle subsets to a 459 source toward a 460 target
should yield lift due to smaller boundary.

## Test

Source: bseed1_score459 (Cluster A).
Target: bseed9_score460 (Cluster A satellite at score 460).

σ-decomposition: 3 cycles, sizes [21, 14, 4]. Total Hamming = 39.
σ-boundary at half: 26 edges.

### Individual cycle application

| cycle # | size | score after application |
|--------:|-----:|------------------------:|
| 0       |   21 |                     448 |
| 1       |   14 |                     450 |
| 2       |    4 |                     448 |

Even the size-4 cycle drops score 459 → 448 (−11). The indecomposability
extends to the smallest cycle in the decomposition.

### Pairwise cycle combinations

| cycles | size | score |
|--------|-----:|------:|
| 0+1    |   35 |   454 |
| 0+2    |   25 |   451 |
| 1+2    |   18 |   442 |

Best pair: 0+1 → 454 (still −5 below source).

### Full triple (all 3 cycles)

Gives bseed9_460 exactly (Δ=+1).

### ALNS recovery from partials

For cycles_00+02 partial at score 451 (closest to target 460):
- 5 seeds × 3 ops = 15 trials × 30s ALNS each.
- Score range across trials: 456-459.
- **MAX = 459. None reach 460.**

## Implication

ALNS cannot LIFT score above 459, even when starting from a partial
that's "1 cycle away" from a known 460 board. The 460 basin
(bseed9_score460) is structurally isolated in a way ALNS-from-partial
cannot reach.

**The 460 outlier was a one-off serendipitous ALNS run** (winning5 ops,
60s budget, unspecified seed) that happened to find a Cluster-A
satellite at score 460. We cannot replicate it via subset application.

This confirms intra-cluster indecomposability with a clean negative
result.

## Comparison to inter-cluster (vol-117 T4)

Vol-117 T4 showed inter-cluster (cross-Cluster A → McGavin) greedy
min-boundary subsets + ALNS → ≤ 448.

Vol-118 (this concept) shows intra-cluster σ-subset + ALNS → ≤ 459.

Both bounded. The within-cluster bound is the source-basin score (459).
The cross-cluster bound is lower (~448) because the recovery basin
under partial application is different (deeper in score).

## Linked

- [[459-level-set-two-cluster-confirmed]] — defines cluster structure.
- [[min-boundary-subset-bridge-refuted]] — parallel cross-cluster refutation.
- [[multiple-459-basins-rigid]] — broader rigidity context.
- [[../sessions/vol-118]].
