---
title: 459 Indecomposability Synthesis — vols 117-118
date: 2026-05-16
status: synthesis
---

# 459 Indecomposability Synthesis

A unified mathematical characterization of the 459 ceiling on
canonical 5-clue Selby-Riordan Eternity II.

> **Status (2026-05-20, vol-188):** the 459 ceiling described here was
> broken to **463/480** at vol-129 (PALIMPSEST consensus-trap attack on
> a new corner-perm). The σ-cycle indecomposability theorem of this
> paper still holds — it's been strengthened to **4 basin pairs** by
> vol-188. What changed: the 459 → 463 lift came from discovering a
> *new basin in a different corner-perm*, not from breaking the
> σ-cycle obstruction described here. See [[SYNTHESIS_VOL_188]] for
> the current state and [[v188-translation-sigma-indecomposability]]
> for the strengthened theorem.

## The 459 problem

Across multiple algorithmic methods, our reachable score is bounded
above by 459/480 on the matched-edges convention (4/5 hint), 457 on
strict-canonical (5/5), and 469 only via McGavin's specific algorithm
on McGavin's corner permutation (3,2,0,1).

This synthesis explains WHY 459 is a barrier through three layers:

1. **Empirical**: 8 documented refutations.
2. **Structural**: σ-cycle indecomposability.
3. **Quantitative**: boundary-cardinality bound.

## Layer 1: Empirical refutations

Methods that have FAILED to exceed 459 from a known 459 basin:

| method                                | result | source |
|---------------------------------------|--------|--------|
| Direct ALNS                           | ≤ 451  | vol-22 |
| Pipeline (bound-ascent + Hungarian + ALNS) | ≤ 459 | vol-110 |
| σ-subset enumeration (2^n, cluster A) | ≤ 459 | vol-110 |
| σ-cycle apply + ALNS                  | ≤ 459 | vol-110 |
| basin-mix MIP (4 basins)              | ≤ 459 | vol-112 |
| single-piece-swap MCMC (T=2-50)       | ≤ 459 | vol-114 |
| σ-cycle Metropolis                    | ≤ 459 | vol-114 |
| greedy min-boundary σ-subset + ALNS   | ≤ 448 | vol-117 T4 |

The 459 ceiling is robust to all explored algorithm families.

## Layer 2: Structural — two-cluster decomposition

Vol-118 T1's rigidity matrix on 7 boards reveals binary structure:

- **Cluster A** (6 basins, 5 distinct): pairwise Hamming 34-44,
  σ-cycles 2-25 cells each, total cycle cells 34-44.
  *Connected* under small-σ-cycle ALNS moves.
- **Cluster B** (1 basin): Hamming 251-253 to Cluster A, σ-cycles
  with giant 94-190 cell components.
  *Disconnected* from Cluster A under all measured operators.

McGavin-469 is in a THIRD "cluster" (giant 154-cycle to local-459).

Conjecture C1 (clustered rigid set, vol-110): **CONFIRMED at 2-cluster
granularity** with quantitative metric (Hamming + cycle structure).

## Layer 3: Quantitative — boundary-cardinality bound

For σ-cycle subset application (vol-117 T3/T4):

$$\Delta(S) \approx -B(S) \cdot p$$

where $B(S)$ is the grid-graph boundary of subset $S$ and $p \approx 1$
empirically.

For the 154-cycle 459→McGavin-469:
- Min contiguous boundary: ~190 at k=113.
- Min greedy boundary: ~64 at k=42 (35-45% better than contiguous).
- Isoperimetric optimum: ~23 (compact subset).

σ-cycle subsets are ~2.5× the isoperimetric optimum, confirming
*geometric spaghetti-ness*. The boundary bound makes any partial-σ
application net-negative.

## Synthesis

Combining all three layers:

**The 459 ceiling is a fixed point of the equivalence class
{σ-cycle subset application, ALNS local search, MCMC, MIP at halo-1
and halo-2}**.

Specifically:
- **Halo-1 MIP** (vol-99/110): proves local rigidity at the 459 basins.
- **Halo-2 per-comp MIP** (vol-93/111): extends rigidity (partial).
- **σ-cycle indecomposability** (vol-65/99): geometric mechanism.
- **Boundary bound** (vol-117 T3/T4): quantitative mechanism.

## What's left

To exceed 459 from current corpus, we need an operator OUTSIDE the
above equivalence class. Candidates:

1. **RL self-play**: trains a *policy* that selects moves based on
   learned features, potentially discovering operators not in our
   manually-coded library. Multi-week scope.

2. **Cutting-plane LP/MIP**: tightens the LP/MIP relaxation with
   problem-specific valid inequalities (e.g., σ-cycle conservation,
   parity, color-multiset). Multi-week. Would lower the basin-local
   LP UB from ~478 toward 459.

3. **Hint-aware schedule + better pipeline**: re-calibrate the
   Blackwood schedule to account for canonical hint contributions.
   Vol-117 T1 showed v17a wedges at depth 35. A recalibrated schedule
   might enable 460+ on the strict-canonical convention. Vol-118+
   candidate.

4. **Genuinely new basin discovery**: vol-118 corner-perm sweep
   tests if our pipeline can find basins on different corner perms.
   Initial 7/24 results show 376-396 scores — well below 459. Full
   sweep pending.

## Score conventions clarified

| convention | record | how reached |
|------------|-------:|-------------|
| Matched-edges (4/5 hint canonical) | **459** | our pipeline |
| Strict-canonical (5/5 hint) | **457** | blackwood_mrv |
| 1-clue (Blackwood's puzzle, only 1 hint) | 470 | Blackwood algorithm |
| McGavin (5-clue corner perm 3,2,0,1) | 469 | McGavin algorithm |
| Unconstrained (0/5 hint) | 469 (corpus max) | many algorithms |

## Linked

- [[concepts/multiple-459-basins-rigid]]
- [[concepts/sigma-cycle-boundary-growth]]
- [[concepts/min-boundary-subset-bridge-refuted]]
- [[concepts/459-level-set-two-cluster-confirmed]]
- [[concepts/basin-mix-mip-refuted]]
- [[concepts/high-t-mcmc-refuted]]
- [[concepts/pipeline-corner-perm-specificity]]
- [[MATH_NOTES_2026-05-16_459_LEVEL_SET]]
- [[MATH_NOTES_2026-05-16_SIGMA_SUBSET_THEOREM]]
