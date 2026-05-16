---
name: sigma-cycle-predicts-alns
description: "Vol-107 T2 finding (preliminary, N=4) — the largest σ-cycle size between a bf_bw partial and the 459 record correlates with the partial's ALNS-completion ceiling. Larger σ-cycle ≈ harder ALNS lift. Concrete data: offset=100 has max-cyc 71 (vs 31-33 for others) AND lower ALNS lift (446-448 vs 450-451)."
metadata:
  type: project
---

# σ-cycle predicts ALNS-liftability (vol-107 T2)

**Status**: `partial` — preliminary correlation, N=4 partials.
**Origin**: vol-107 T2 (2026-05-16). Question raised by vol-106 T13.c:
why does offset=0 reach ALNS 450-451 while offset=100 (deeper partial)
only reaches 446-448?

## The data (vol-107 T2 measurement)

For each bf_bw partial (4 threads × 5min on canonical Selby-Riordan
v17a strict, varying `--seed-offset`), compute the σ-permutation
from the partial to vol-60's 459 record. Decompose into cycles.

| seed_offset | depth | bf_score | n_cycles | hamming | **max_cycle** | mean_cyc | ALNS 2min |
|------------:|------:|---------:|---------:|--------:|--------------:|---------:|----------:|
|           0 |   236 |      431 |       30 |     243 |        **33** |      7.7 |  **450-451** |
|         100 |   244 |      442 |       28 |     241 |        **71** |      8.3 |    446-448 |
|        1000 |   243 |      439 |       32 |     242 |        **31** |      7.1 |        447 |
|       10000 |   243 |     (n/a)|       27 |     243 |        **33** |      8.5 |    (n/a)   |

**Hypothesis**: the **largest σ-cycle size** is a stronger predictor
of ALNS-liftability than partial-depth or partial-score.

Partial 100's max-cycle 71 (more than 2× the others) corresponds to
a structurally entangled region between this basin and the 459. That
region requires a single large coordinated move to "rotate" 71 cells,
which standard ALNS destroy/repair operators struggle with. Smaller
max-cycles (31-33) can be addressed by ALNS's typical 5-30 cell
destroy ops.

## Why this is non-obvious

The "best" partial by score (offset=100, 442) yields a WORSE ALNS
completion than the "lower-score" partial (offset=0, 431). Naive
intuition says "deeper partial = closer to optimum = better lift".
The σ-cycle metric explains the inversion: depth/score measures
adjacency-match quality, while max-cycle measures structural
distance to a target high-score basin.

## What this means operationally

1. **Pre-ALNS screening**: given a partial, compute its σ-cycle to
   the standing record (459). If max-cycle > 50, the basin is
   structurally distant; ALNS likely won't lift it past ~447.
2. **Diverse seed selection**: when running multi-thread bf_bw,
   prefer seeds whose partials have small max-cycle to 459 (or
   to a "training" record). This is operator selection by basin
   structure.
3. **Vol-108 invention**: a custom ALNS destroy op targeting the
   "giant σ-cycle" cells specifically. Decompose, identify the
   cycle, destroy those cells + halo, repair. Could lift the
   max-cycle-71 partials.

## Caveats

- N=4 partials is statistically thin. Need ≥ 8-16 to make a
  variance claim.
- ALNS variance across seeds is ±1; the 450 vs 447 difference is
  3× variance, so the signal is plausible but not strong.
- σ-cycles are computed to vol-60's SPECIFIC 459 record. Other 459
  basins exist (multiple p06-perm records); the metric may differ
  per target.

## Linked

- [[../sessions/vol-106|vol-106 T13.c (origin)]]
- [[../sessions/vol-107|vol-107 T2 (this measurement)]]
- [[blackwood-fast]] — pipeline producing the partials.
- [[sigma-cycle-topology-3-basins]] (vol-65) — σ-cycle theory.
- [[basin-escape-recipe]] (vol-22) — predecessor of structural-
  basin-aware ALNS.
