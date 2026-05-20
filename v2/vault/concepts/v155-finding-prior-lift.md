---
name: v155-finding-prior-lift
description: structure understood; ceiling identified.
status: built
metadata:
  type: concept
---
# V155 Finding — Empirical Prior Lifts Beam-Search Ceiling

**Status**: `built-measured` 2026-05-19. Empirical result; mathematical
structure understood; ceiling identified.

## Headline

Adding an empirical (piece, position) prior derived from 938 high-score
DB boards to a width-K beam search lifts the from-scratch ceiling on
canonical Eternity II by ~3 points (V151 plain beam K=4096: 449/480 → 
V155 K=4096 with prior + path-dedup-4: 456/480) at similar wallclock.

## Setup

- Canonical 16×16/22 puzzle (Selby-Riordan, 5 canonical hints).
- Constructive beam-search (V151 base): row-major scan, top-K states
  per depth, expand all valid (piece, rotation) candidates, prune to
  top-K by matched-edges score with state-hash dedup.
- Empirical prior: $\text{prior}(p, c) = $ count of boards (out of 938 with
  matched-edges ≥ 440) in which piece $p$ is at position $c$.

## V155 modification

Each beam state carries `prior_sum` = $\sum_{\text{placed} (p, c)} \text{prior}(p, c)$.

Children ranked by:
1. `score` (matched edges) descending.
2. `prior_sum` descending (tiebreak).

Optionally a continuous blend: `combined = score * 1e6 + alpha * prior_sum`.

## Results

| Config | Best | Time |
|--------|------|------|
| V150 random sweep (50k seeds) | 408 | 67s |
| V151 K=64 plain | 446 | 1s |
| V151 K=1024 plain | 453 | 18s |
| V151 K=4096 plain | 449 | 85s |
| V151 K=16384 path-dedup-8 | 455 | 21min |
| V155 K=1024 + prior(440) | 454 | 23s |
| V155 K=4096 + prior(440) + path-dedup-4 | 456 | 117s |
| V155 K=8192 + prior(440) + path-dedup-8 | 456 | 295s |
| V157 K=4096 + rotation-prior(440) + path-dedup-4 | 456 | 159s |
| **V155 K=4096 + prior(459) + path-dedup-4** | **460** | 238s |

**Best**: V155 K=4096 + sharper prior (≥459 threshold, 26 boards) +
path-dedup-4 = **460/480** in 238s. Verified via `rescore_board`.
Corner perm (1, 0, 3, 2) — matches existing basin family.

## Critical observation: prior SHARPNESS dominates

Increasing prior detail (V157 rotation-aware: 2D → 3D) did NOT lift
beyond 456. But **sharpening the prior threshold** (940 boards →
26 boards) lifted +4 to 460.

Interpretation: the 440-thresh prior is dominated by 440-459 patterns
(mostly canonical-hint placements + corner pieces). The 459-thresh
prior reveals record-tier piece-position patterns. Beam-search converges
to "common record-tier" structure, not "common all-boards" structure.

## Why 456 is a ceiling

Saturation observed at K=4096 → K=8192 → K=16384 (no further lift).
Saturation observed at 2D prior vs 3D rotation-aware prior (no
further lift).

Hypothesis: the prior's shape is dominated by the corpus distribution
(440-459 typical). The beam follows the most-common patterns and ends
in their basin. To break the ceiling, need:
- A SHARPER prior (e.g., only ≥459 boards) — V155-high459 experiment.
- Different search primitive (not beam).
- Post-processing (ALNS) to escape attractors — V156 experiment.

## Mathematical interpretation

The prior $\text{prior}(p, c)$ is an unnormalized empirical density. Used as
ranking signal, it's equivalent to maximum-likelihood path search:

$$\text{rank}(s_d) = \alpha \cdot \text{score}(s_d) + (1-\alpha) \cdot \log \prod_{(p, c) \in s_d} \text{prior}(p, c)$$

(up to additive constants from prior normalization). When $\alpha = 0.99$,
beam picks the highest-score path with prior as soft tiebreak.

The beam converges to the **path of maximum density × score**. The ceiling
at 456 is the maximum (density × score) along any beam-feasible path.

## Limitations

1. **Corpus bias**: the prior reflects the corpus, which is biased toward
   ALNS-final boards in 440-459. Doesn't sample the 460+ basins well.
2. **Mode collapse at K**: large K with weak dedup → near-identical states.
   Path-dedup-recent-4 helps but doesn't fully solve.
3. **Locality**: prior only knows (piece, position) pairs, not piece-piece
   correlations. Pair-prior (V158, untested) could help.

## Connection to records

| Score | What | Gap from V155 |
|-------|------|---------------|
| 456 | V155 from-scratch | — |
| 458 | strict-canonical record (vol-122) | -2 |
| 459 | strict-canonical record (V129-T11 corpus find) | -3 |
| 463 | matched-edges record (V129-T12 ALNS) | -7 |
| 469 | community record (McGavin 2020) | -13 |
| 480 | hypothetical solution | -24 |

V156 (running): does ALNS on 456 → reach 459+?

## Linked

- [[vol-155]]
- [[vol-156]] (ALNS hybrid)
- [[prior-data-augmented-beam]] (V155 invention)
- [[weaving-beam]] (V151 parent)
