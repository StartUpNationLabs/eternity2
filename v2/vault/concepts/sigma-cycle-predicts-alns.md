---
name: sigma-cycle-predicts-alns
description: "Vol-107 T2 finding (N=6, hypothesis WEAKENED) — initial N=4 suggested max-σ-cycle to 459 predicts ALNS-liftability, but extension to N=6 shows mixed signal. offset=50 has smallest max-cyc (23) but LOW ALNS lift (444); offset=100 has largest max-cyc (71) and LOW lift (446) — consistent. But the relationship isn't monotonic. May still hold within sub-clusters; further work needed."
metadata:
  type: project
status: partial
---

# σ-cycle predicts ALNS-liftability (vol-107 T2)

**Status**: `partial` — hypothesis weakened after N=6 extension.
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

## Extended data (N=6, vol-107 T2 follow-up)

After the initial N=4 finding, ran bf_bw on 5 more seed_offsets (50,
200, 500, 2000, 5000) at 4t × 2min each, then ALNS 60s seed=42 on 3
of them (the others' ALNS not yet measured).

| offset | bf_score | max_cyc | ALNS @ 60s |
|-------:|---------:|--------:|-----------:|
|      0 |      431 |      29 |       (450) |
|     50 |      436 |  **23** |    **444** |  ← smallest max-cyc, LOWER lift!
|    100 |      442 |      71 |        446 |
|    200 |      442 |      44 |        448 |
|    500 |      433 |      31 |   (n/a)    |
|   1000 |      439 |      31 |        447 |
|   2000 |      443 |      29 |        450 |
|   5000 |      439 |      30 |   (n/a)    |
|  10000 |     (n/a)|      33 |   (n/a)    |

**HYPOTHESIS WEAKENED**. offset=50 has the smallest max-cycle (23,
smallest in the dataset) but its ALNS lift (444) is BELOW the
mean. If max-cycle truly predicted liftability, this should be
the BEST partial, not the worst-tested.

**Partial reconciliation**:
- The offset=100 outlier (max-cyc 71, lift 446) is still real —
  one giant cycle does seem to be a meaningful drag.
- But max-cyc < 30 doesn't guarantee good lift either.

The hypothesis is probably TOO SIMPLE. A more honest framing:
- max-cycle > 50 is a NEGATIVE signal (one giant cycle is hard).
- max-cycle < 30 is INFORMATIVE BUT INSUFFICIENT (other basin
  features matter too).

## What might be a better predictor

- **Number of cycles** (more independent cycles = easier
  independent ALNS rep
airs). offset=50 has 37 cycles (highest);
  offset=2000 has 25 (lowest). Doesn't clearly correlate either.
- **Cycle size DISTRIBUTION** (entropy / Gini). A flat
  distribution may be more ALNS-friendly than one with extremes.
- **Cell-pos-set OVERLAP** of σ-cycles with known
  ALNS-destroy-op kernels (e.g., WorstBand{4}, ConflictDriven{30}).

Vol-108 candidate: build a richer basin-feature extractor and
correlate against ALNS-lift across N≥16 partials. Until then,
this hypothesis is at best "partially supported".

## Linked

- [[vol-106|vol-106 T13.c (origin)]]
- [[vol-107|vol-107 T2 (this measurement)]]
- [[blackwood-fast]] — pipeline producing the partials.
- [[sigma-cycle-topology-3-basins]] (vol-65) — σ-cycle theory.
- [[basin-escape-recipe]] (vol-22) — predecessor of structural-
  basin-aware ALNS.
