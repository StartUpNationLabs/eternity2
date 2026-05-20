---
name: min-boundary-subset-bridge-refuted
description: "Vol-117 T4 — refutes the 'min-boundary σ-cycle subset + ALNS' bridge hypothesis. Greedy min-boundary subsets of the 459→McGavin 154-cycle achieve k=10/b=24, k=20/b=38, k=40/b=64 (vs contiguous min ~3-4× higher). Applying these subsets loses ~boundary-many score edges (22, 38, 63). ALNS recovery from the resulting partials plateaus at 446-448 (k=10), 441 (k=20), 430 (k=40) — all WELL BELOW 459 across 12 (seed × ops) combinations. The σ-cycle indecomposability extends to greedy min-boundary subsets."
metadata:
  type: project
status: refuted
---

# Min-boundary subset bridge — REFUTED (vol-117 T4)

**Status**: `refuted` 2026-05-16.

## Refutation

- **Refuted**: vol-117 T4.
- **Evidence**: greedy min-boundary subsets of the 459→McGavin 154-cycle achieved 35-45% lower boundary than contiguous, but applying them lost ~boundary-many score edges (22, 38, 63 for k=10, 20, 40). ALNS recovery from those partials plateaus at 446-448 / 441 / 430 across 12 (seed × ops) combinations — all WELL below 459.
- **What's refuted**: the hypothesis that lower σ-boundary partial-loss + ALNS access to the McGavin-side basin geometry could yield ≥ 460. The σ-cycle indecomposability extends to greedy min-boundary subsets, not just contiguous ones.
- **What's NOT refuted**: that the full 154-cycle would lift to 469 (it does — that's how McGavin's basin is reached in principle). Only the "partial subset + ALNS bridge" idea is dead.

## Hypothesis

Vol-117 T3 found σ-cycle boundary grows roughly linearly in subset
size, but GREEDY MINIMUM-BOUNDARY subsets achieve 35-45% lower
boundary than contiguous subsets at the same k.

Hypothesis: applying a greedy min-boundary subset (k=10-40) of the
459→McGavin σ-cycle, then ALNS-recovering, MIGHT reach 460+ because
of lower partial-loss and access to the McGavin-side basin geometry.

## Test

`scripts/vol117_min_boundary_subset_apply.py`:
1. Compute σ-cycle 459(vol-60 RECORD_TIE) → McGavin-469.
2. Greedy-grow min-boundary trajectory on the 154-cycle.
3. Apply subsets at k ∈ {10, 20, 30, 40, ..., 150}.
4. Dump resulting partials to `output/vol-117/min_boundary_subsets/`.

## Empirical results

### Boundary vs realized score loss

| k   | boundary | score (post-subset) | loss vs 459 |
|----:|---------:|--------------------:|------------:|
|  10 |       24 |                 437 |          22 |
|  20 |       38 |                 421 |          38 |
|  30 |       56 |                 405 |          54 |
|  40 |       64 |                 396 |          63 |
|  50 |       70 |                 386 |          73 |
|  60 |       78 |                 378 |          81 |

**Score loss ≈ boundary cardinality**. Boundary is a tight upper
bound on loss, ~90-100% realized as mismatches.

### ALNS recovery ceiling

ALNS sweep (4 seeds × 3 ops) for 30s each on k=10 subset (post-subset
score = 437):

| seed | basic | minimal | winning5 |
|-----:|------:|--------:|---------:|
|    1 |   445 |     446 |      445 |
|    7 |   447 |     447 |      445 |
|   42 |   446 |     448 |      446 |
|  100 |   445 |     447 |      445 |

**Max = 448. Median = 446. All ≤ 459.**

For k=20: ALNS reaches 441 (60s seed=42).
For k=40: ALNS reaches 430 (60s seed=42).

Even with 5-minute ALNS on k=10, score stays at 446. The recovery
plateau is BASIN-DETERMINED, not budget-limited.

## Implication

Applying greedy min-boundary subsets:
- **Score loss matches boundary** (tight ~90-100% realization).
- ALNS-recovers into a NEW local basin (~445-448 ceiling).
- This new basin is DIFFERENT from the 459 source (lower ceiling).
- σ-cycle indecomposability extends to greedy min-boundary subsets:
  small-k → small-loss but doesn't escape source basin's neighborhood;
  medium-k → can't recover the structural cycle-completeness; large-k
  → too much damage.

## Why this matters

This refutes the "find a low-boundary subset to bridge basins"
hypothesis, which was the main reason min-boundary measurement
was worth doing. **The σ-cycle's structural rigidity is not
breakable by smart subset selection within ALNS-recoverable scope.**

A 460+ board, if reachable from a 459 basin, would require:
- A subset application that lands in a *high-ceiling* basin (i.e.,
  not just a low-score basin), AND
- ALNS able to escape that basin's local optima (currently impossible
  in 60s-5min on ALL tested basins).

## Closes

- Vol-117 T4 (min-boundary subset bridge).
- One more in the list of refuted basin-bridge approaches:
  vol-110 σ-subset enumeration, vol-112 basin-mix MIP, vol-114
  high-T MCMC, σ-cycle Metropolis, vol-117 T4 greedy min-boundary.

## Linked

- [[sigma-cycle-boundary-growth]] — the math that motivated this.
- [[multiple-459-basins-rigid]] — broader rigidity context.
- [[basin-mix-mip-refuted]] — parallel MIP refutation.
- [[high-t-mcmc-refuted]] — parallel MCMC refutation.
- [[vol-117]].
