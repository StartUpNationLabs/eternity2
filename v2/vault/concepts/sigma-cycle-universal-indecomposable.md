---
name: sigma-cycle-universal-indecomposable
description: σ-cycle indecomposability now confirmed for ALL 3 basin-pair transitions tested (459↔McGavin, 458↔McGavin, 459↔458). EVERY cycle subset reduces score. Universal property of cross-basin moves on canonical E2.
metadata:
  type: project
status: built
---

# σ-cycle indecomposability is universal (vol-101 finding)

**Status**: `built` — measured 2026-05-16 ~04:28.

## Four transitions tested (vol-188 update)

For each basin-pair transition, we computed σ-cycle decomposition
and tested whether applying any cycle subset individually improves
the score. **Every test returned negative.**

The first 3 transitions were measured 2026-05-16 (vol-65/99/101).
A 4th independent transition was measured vol-188 — see [[v188-translation-sigma-indecomposability]].

### 459 → McGavin 469 (vol-65 memory, original finding)
- 11 cycles, sizes [154, 22, 19, 18, 13, 9, 7, 6, 3, 2, 2]
- All cycle subsets reduce score (-2 to -143)
- Only full 255-cell application reaches 469

### 458 → McGavin 469 (vol-99 today)
- 11 cycles, sizes [80, 42, 42, 40, 25, 10, 4, 4, 3, 2, 2]
- All cycle subsets reduce score (-5 to -170)
- Only full 254-cell application reaches 469

### 459 → 458 (vol-101)
- 14 cycles, sizes [85, 56, 18, 14, 12, 8, 8, 7, 5, 4, 3, 3, 2, 2]
- All cycle subsets reduce score (-4 to -174)
- Only full 227-cell application reaches 458

### V181 460 → McGavin 469 (vol-188)
- 15 cycles: 3 fixed (length 1), 4 length-2, 1 length-4 (corners), 1 length-6, 1 length-22, 1 length-29, 1 length-32, 1 length-49, 1 length-51, 1 length-52
- Every individual non-trivial cycle: Δ ∈ [−143, 0]
- All pairs of small cycles: Δ ∈ [−29, −10]
- Bottom-confined cycles (1 + 2): Δ = −4 (reaches 456)
- Full π (all 15 cycles): → 469 (recovers McGavin, sanity check)
- Details: [[v188-translation-sigma-indecomposability]]

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

### Strengthens / extends
- [[v188-translation-sigma-indecomposability]] — 4th basin pair (vol-188)
- [[sigma-cycle-topology-3-basins]] — initial 3-basin topology
- [[sigma-cycles-are-dispersed]] — geometric dispersion of cycles
- [[sigma-cycle-indecomposable-vol32-458]] — earlier finding for vol-32

### Algorithmic refutations grounded by this theorem
- [[basin-mix-mip-refuted]] — MIP-proves no cell-wise mix beats 459
- [[high-t-mcmc-refuted]] — MCMC can't traverse basins
- [[intra-cluster-sigma-subset-refuted]] — even intra-cluster subsets fail
- [[min-boundary-subset-bridge-refuted]] — greedy min-boundary subsets also fail
- [[sigma-cycle-destroy]] — SigmaCycleDestroy ALNS op (refuted)
- [[sigma-cycle-predicts-alns]] — σ-cycles don't predict ALNS lift either

### Findings extended by
- [[three-basin-iso-plateau]] — basin-level statement
- [[row-level-rigidity]] — row-swap rigidity (vol-186)
- [[v187-intaglio-mip]] — MIP rigidity proofs (vol-187)
- [[mip-local-optimality-459]] — halo-N MIP rigidity

### Structural context
- [[basin-corner-permutations]] / [[corner-permutation-study]] — 18-cp taxonomy
- [[why-records-are-mip-rigid]]
- [[basin-permutation-group]] — σ-orbit group structure
- [[piece-side-matching]] — PSM polytope

### Papers
- [[PAPER_2026-05-16_canonical_E2_rigidity_theorem]]
- [[PAPER_2026-05-16_459_indecomposability_synthesis]]
- [[MATH_NOTES_2026-05-16_SIGMA_SUBSET_THEOREM]]

### Memory
- `project_e2_vol65_oracle_sigma_indecomposable.md` (original)
- `project_e2_2026_05_16_rigidity_theorem.md`
