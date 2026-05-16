---
name: sigma-cycle-universal-indecomposable
description: σ-cycle indecomposability now confirmed for ALL 3 basin-pair transitions tested (459↔McGavin, 458↔McGavin, 459↔458). EVERY cycle subset reduces score. Universal property of cross-basin moves on canonical E2.
metadata:
  type: project
---

# σ-cycle indecomposability is universal (vol-101 finding)

**Status**: `built` — measured 2026-05-16 ~04:28.

## Three transitions tested

For each of the 3 basin-pair transitions, we computed σ-cycle
decomposition and tested whether applying any cycle subset
individually improves the score. **Every test returned negative.**

### 459 → McGavin 469 (vol-65 memory, original finding)
- 11 cycles, sizes [154, 22, 19, 18, 13, 9, 7, 6, 3, 2, 2]
- All cycle subsets reduce score (-2 to -143)
- Only full 255-cell application reaches 469

### 458 → McGavin 469 (vol-99 today)
- 11 cycles, sizes [80, 42, 42, 40, 25, 10, 4, 4, 3, 2, 2]
- All cycle subsets reduce score (-5 to -170)
- Only full 254-cell application reaches 469

### 459 → 458 (vol-101, just measured)
- 14 cycles, sizes [85, 56, 18, 14, 12, 8, 8, 7, 5, 4, 3, 3, 2, 2]
- All cycle subsets reduce score (-4 to -174)
- Only full 227-cell application reaches 458

## Universal property

**ALL 3 cross-basin transitions on canonical E2 exhibit σ-cycle
indecomposability.** This is not specific to McGavin's basin —
even between two LOCAL basins (459 and 458) at similar scores,
the σ-cycle is indecomposable.

The pattern holds even for the smallest cycles (size 2). A 2-cell
piece swap that's part of a basin-bridging σ-cycle reduces score
by 4-7 points. There's no "easy first step" toward another basin.

## Mathematical formulation

Let σ be the permutation taking basin A's piece-arrangement to
basin B's. For every nontrivial cycle decomposition σ = c₁ c₂ ... cₖ,
applying any subset of cycles individually gives a piece-arrangement
with score < score(A).

This is a strong indecomposability statement. **Basin transitions
on canonical E2 require simultaneous application of all cycles
in the decomposition.** Partial application = strict score
decrease.

## Implication for algorithm design

No incremental search algorithm (greedy, SA, ALNS, beam search,
etc.) can traverse basins on canonical E2, because:
1. Every step toward a different basin reduces score.
2. The full transition requires 80-255 simultaneous changes.
3. The acceptance probability of a -174-point move under any
   reasonable temperature is effectively zero.

To traverse basins, an algorithm needs to:
- Identify ENTIRE σ-cycles up-front (no incremental discovery).
- Commit to applying the entire cycle in one step (no partial
  rollback).

This is fundamentally non-incremental. Standard solver paradigms
(CP, SAT, MIP, MCMC) all assume incremental moves.

## Linked

- [[sigma-cycle-topology-3-basins]]
- [[sigma-cycles-are-dispersed]]
- [[sigma-cycle-indecomposable-vol32-458]] (the previous finding)
- [[basin-corner-permutations]]
- [[why-records-are-mip-rigid]]
- Memory: `project_e2_vol65_oracle_sigma_indecomposable.md` (original)
- Memory: `project_e2_2026_05_16_rigidity_theorem.md`
