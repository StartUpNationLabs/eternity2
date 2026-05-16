---
name: 459-level-set-two-cluster-confirmed
description: "Vol-118 — pairwise rigidity matrix on 7-board 459 corpus confirms TWO-CLUSTER structure with quantitative precision. Cluster A (6 basins: vol-110 bseed1/6/11/orig/NEW + v17_alns winning5): pairwise Hamming 34-44, max σ-cycle 9-25. Cluster B (1 basin: vol-60 RECORD_TIE_459): Hamming 251-253 to Cluster A members, max σ-cycle 94-190. Cluster A members all reachable via 'small-cycle' σ-permutations. Cluster B isolated by 'giant-cycle' transitions."
metadata:
  type: project
---

# Two-cluster structure of the 459-level set (vol-118)

**Status**: `built` — formal confirmation with rigidity matrix.

## Method

`scripts/vol118_rigidity_matrix.py` computes for each pair of boards
$(b_i, b_j)$:
- **Hamming distance**: # positions where the piece-id differs.
- **σ-cycle stats**: count, max size, total cells in cycles.
- **Min boundary at k = ⌈N/2⌉**: rigidity proxy for the giant cycle.

Run on 7 boards: 5 from vol-110 basins (bseed1, bseed6, bseed11,
orig, NEW_459_from_off100), 1 from v17_alns winning5, 1 from vol-60
RECORD_TIE_459.

## Empirical results

### Cluster A (intra-cluster, "small-cycle")

Members: bseed1, bseed6, bseed11, orig/NEW_459_from_off100, winning5_sa42.

Pairwise:
- **Hamming**: 34-44 (out of 256 cells).
- **σ-cycles**: 2-7 cycles per pair.
- **Max cycle size**: 9-25 cells.
- **Total cycle cells**: 34-44.

orig and NEW_459_from_off100 are IDENTICAL (Hamming=0, no cycles).
So Cluster A has **5 distinct basins**.

### Cluster B (inter-cluster, "giant-cycle")

Member: RECORD_TIE_459_p06_corner_1_0_2_3_seed2 (vol-60).

vs each Cluster A member:
- **Hamming**: 251-253 (boards differ in nearly EVERY cell).
- **σ-cycles**: 6-11 cycles.
- **Max cycle size**: 94-190.
- **Total cycle cells**: 251-253.
- **Min boundary at k=N/2**: 138-182.

## Implications

1. **Within Cluster A**: the small-cycle σ-distances enable ALNS to
   navigate between cluster members (visit multiple basins). But
   vol-110 confirmed ALNS within Cluster A stays ≤ 459.

2. **Between A and B**: the giant cycles (max 190 cells) with high
   boundary (138-182) are INDECOMPOSABLE per vol-117 T3/T4. So
   ALNS or σ-cycle subset application cannot cross A↔B.

3. **Most of the 459-level set is Cluster A** (5 vs 1 in our sample,
   though sampling is biased — Cluster A is found by our pipeline).
   Cluster B is harder to reach by our algorithms.

4. **vol-110/112 found ALNS PT visits multiple Cluster A basins**.
   So the 459-level set ≠ {single point}; it's a *connected component*
   in Cluster A under small-σ-cycle moves, plus Cluster B as
   a disconnected (under our moves) island.

## Geometric distinction

For Cluster A pairs: σ-cycles total 34-44 cells (~15% of board).
For Cluster B pairs: σ-cycles total 251-253 cells (~99% of board).

This is a *binary* signature — there's no intermediate band of
basins at 40% Hamming or 70% Hamming. Either two boards are
near-identical (small Hamming) or near-disjoint (Hamming ≈ 253).

This is consistent with the σ-cycle ALGEBRA: σ-cycles compose by
piece-conservation, so adding a "small" σ-cycle to a "large" σ-cycle
produces another large σ-cycle. There's no smooth Hamming
interpolation.

## Open questions

- **How many basins are in Cluster A?** Our sample has 5. The
  pipeline lottery (vol-110) found 5 + 1 dupe in 11 trials. So
  Cluster A might be 10-20 basins.

- **Is Cluster B singleton, or are there other "Cluster B-like" basins?**
  Vol-60 found RECORD_TIE_459 through a different pipeline (p06
  corner setup, seed=2). We'd need to enumerate more corner perms.

- **Does Cluster A or B contain the "most McGavin-like" 459?** The
  σ-cycle 459→McGavin-469 is 154-cycle (giant). Both Cluster A and
  B are giant-cycle distant from McGavin.

## Linked

- [[multiple-459-basins-rigid]] — broader rigidity context.
- [[sigma-cycle-boundary-growth]] — quantitative cycle structure.
- [[../MATH_NOTES_2026-05-16_459_LEVEL_SET]] — conjecture C1 supported.
- [[../sessions/vol-118]].
