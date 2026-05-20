# Vol-61 — faithful SOTA pipeline replay (calibration vol)

**Theme**: Replicate the cross-machine 459 SOTA pipeline as-shipped
to validate our toolchain. **NOT** an invented algorithm — this vol
is grandfathered as calibration per the vols-61-70 directive.
**Date**: 2026-05-15 (closed 18:47 CEST).
**Standing record at open / close**: 459/480.

## What was attempted

Stage-by-stage replay of the SOTA pipeline as described in the
cross-machine notes:

1. **Stage 1**: `vanilla_path --path-mode border-first --threads 9
   --budget-ms 1800000` (30 min × 9 threads).
2. **Stage 2**: `alns_only --ops minimal --seed 1 --t 1.0
   --alns-budget-ms 300000` (5 min).
3. **Stage 3**: `alns_only --ops basic --t 1.0 --alns-budget-ms
   1800000` × 8 seeds (incl. seed=42) in parallel (30 min × 8
   workers).

Source's reported milestones: stage 1 ≈ 403, stage 2 ≈ 452, stage 3
seed=42 → 459.

## What was measured / kept

| stage | what | score | source's reference | match? |
|---|---|---|---|---|
| 1 | vanilla_path border-first 9-thread 30min | (not parsed) | ~403 | likely ✓ |
| 2 | alns_only minimal 5min seed=1 | **453** | ~452 | ✓ matched |
| 3 | alns_only basic 30min × 8 seeds | max **458** | seed=42 ⇒ 459 | partial |

### Stage 3 seed × score distribution

| seed | score |
|---|---|
| 17 | **458** |
| 200 | **458** |
| 100 | 457 |
| 1 | 456 |
| 3 | 455 |
| 42 | 455 |
| 2 | 454 |
| 4 | 454 |

**Mean 455.6, min 454, max 458.** Source's note: seed=42 → 459, seed=4
→ 458. Our seed=42 → 455 (NOT 459). Our seed=4 → 454.

The variance band (454-458) matches the source's "rare event" framing.
The empirical 459-break rate at 8 seeds × 30min was 0/8.

## What was refuted

- **No specific seed is universal**: seed=42 reached 459 on the source
  machine but only 455 on ours. The basin geometry is sensitive to
  numerical micro-differences (different OS, libc, libm, RNG seed
  threading order across 9-thread stage 1). [Hypothesis only — not
  proven.]
- **8 seeds × 30 min is not sufficient to reliably reproduce 459**.
  Need either ≥ 24 seeds or ≥ 2h per seed.

## What was kept (the actual deliverables)

- Two more 458 records: `output/vol-61/faithful_sota_20260515T174124/
  stage3_seed{17,200}.json`. Both verified via `rescore_board`
  (256/256 placed, 458/480 matched).
- These 458s feed the vol-62 MIP-bound test (see Concepts touched).

## Concepts touched

- [[mip-local-optimality-459]] (amended): vol-61's
  seed17 and seed200 458 records ALSO joint-MIP-locally-optimal at
  halo-1. The conjecture now holds across 4 boards / 2 score bands.

## Open at close

- Could re-run stage 3 with 24 seeds (3× compute) or 90 min per seed
  (3× compute) — would expect ~1-2 459 boards based on the variance.
- Vol-62 is the priority — vol-62 has the sound MIP-bound result;
  vol-61 calibration confirms the pipeline works.
- Vol-63 (Temporal-Rewind-Search) will use vol-61's 453 stage 2 partial
  as a non-record starting point.

## Linked memory

- `project_e2_459_sota_cross_machine` — the source SOTA notes
- `feedback_vols_61_to_70_invented_algos` — directive (vol-61
  grandfathered)
