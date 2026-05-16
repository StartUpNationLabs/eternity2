---
name: strict-canonical-pipeline-honest-446
description: "Vol-118 — HONEST strict-canonical pipeline ceiling after vol-118 bf-bucket bug fix: max 446, median 443.5 across 8 trials (vs pre-fix claimed 452, median 449). The pre-fix 452 was a real LEGAL_COMPLETE board, but the path to it relied on the buggy partial having 8 illegal edge-piece anchors that gave ALNS denser initial seeding. With the bug fixed, the same pipeline reaches 446 max. `basic` preset beats `winning5` 8/8 in paired comparisons."
metadata:
  type: project
---

# Strict-canonical pipeline — honest 446 ceiling (vol-118)

**Status**: `built` — measured 2026-05-16.

## Method

Pipeline: par-8 bf_bw_schedule_hinted (v17a, 60s) → bound-ascent (1000
iters, seed=42, accept-all) → Hungarian (edge_target_match) → ALNS
(60s, 4 seeds × 2 ops).

## Pre-fix vs post-fix comparison

| seed | basic-pre | basic-post | winning5-pre | winning5-post |
|-----:|----------:|-----------:|-------------:|--------------:|
|    1 |       449 |        446 |          449 |           443 |
|   42 |       449 |        445 |          449 |           443 |
|  100 |       449 |        444 |      **452** |           442 |
|  200 |       — |         443 |            — |           441 |

- Pre-fix max: 452 (seed=100 winning5)
- **Post-fix max: 446** (seed=1 basic)
- Pre-fix median: 449
- Post-fix median: 443.5

**6-point loss from the fix.** Cause: the buggy partial had 8 illegal
edge-piece anchors at interior cells (positions 208-228, rows 13-14)
which gave ALNS a denser initial skeleton. With illegal placements
removed (by the fix), ALNS starts with 8 fewer anchored cells.

The pre-fix 452 board was itself LEGAL_COMPLETE (no border
violations remained after ALNS finished placing) — but it was
REACHED via a contaminated starting condition.

## `basic` vs `winning5`

In all 4 paired post-fix comparisons:

| seed | basic | winning5 | winner |
|-----:|------:|---------:|--------|
|    1 |   446 |      443 | basic +3 |
|   42 |   445 |      443 | basic +2 |
|  100 |   444 |      442 | basic +2 |
|  200 |   443 |      441 | basic +2 |

**`basic` wins 4/4. winning5 is uniformly weaker.** Confirms memory
`project_e2_459_sota_cross_machine`: "minimal → basic is the right
escalation; mega/full are wrong" — and adds that winning5 (which is
basic + ConflictDriven{80}) is similarly too aggressive in this
strict-canonical regime.

## Implication

Honest strict-canonical hint-preserving pipeline ceiling = **446**.

Strict-canonical record (per memory blackwood_mrv): 457.
**Gap: 11 points**, larger than thought.

The vol-118 T5 conflict-prop fix unblocked the schedule path from
wedging, and the vol-118 T5b parallel diversification provided
significant lift over single-thread (which was capped much lower).
But the structural 459-level-set rigidity remains: even par-pipeline
at depth 232 + Hungarian + ALNS reaches local basins with UB ≈ 455
that ALNS recovers to ~446.

To beat 457 strict-canonical: need either a different basin (par-bf
seed-sweep with UB filter — vol-118 T6 was working on this when
killed for the bug fix) OR a fundamentally different algorithmic
approach.

## Verification

All 8 post-fix boards passed verify_board: LEGAL_COMPLETE, 256/256
unique pieces, 0 border violations, 5/5 canonical hints OK.

## Linked

- [[bf-candidate-bucket-bug]] — the bug fixed before this measurement.
- [[hint-pin-conflict-propagation-fix]] — vol-118 T5 fix that
  unblocked the schedule path.
- [[parallel-hint-preserving-bf]] — the parallel variant.
- [[strict-canonical-452-basin-rigid]] — earlier (pre-fix) UB analysis.
- [[../sessions/vol-118]].
