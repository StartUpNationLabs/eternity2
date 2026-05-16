---
name: strict-canonical-alns-is-bottleneck
description: "Vol-118 T10 — skipping bound-ascent (direct bf → Hungarian → ALNS) yields HIGHER UB (461 vs 458) but SAME ALNS ceiling (446). The pipeline-composition variants tested don't break 446 → the ALNS step itself is the binding constraint for strict-canonical work. Larger UB gives ALNS more theoretical room but ALNS cannot realize it at 60s budget."
metadata:
  type: project
---

# Strict-canonical: ALNS is the bottleneck (vol-118 T10)

**Status**: `built` — measured 2026-05-16.

## Test

T10 ran the pipeline WITHOUT the bound-ascent step:
`par-8 bf 60s → Hungarian directly → ALNS sweep`

Compare to T6 (post-fix) which ran the same with bound-ascent in
between: `par-8 bf → bound-ascent → Hungarian → ALNS`.

## Results

| pipeline                              | UB  | ALNS max (60s, basic) |
|---------------------------------------|----:|----------------------:|
| with bound-ascent (T6 post-fix)       | 458 | 446                   |
| without bound-ascent (T10)            | 461 | 446                   |

**Δ UB: +3. Δ realized ALNS score: 0.**

The bound-ascent's homogenization hypothesis was PARTIALLY correct:
skipping it preserves more diversity → higher local UB. But ALNS
doesn't realize the higher headroom at 60s budget.

## Implication

The pipeline composition variants tested cannot break 446 strict-
canonical. The ALNS step itself is the binding constraint. To
break 446:

1. **Longer ALNS budget** (30min instead of 60s) — does the basin
   ceiling change? Memory `project_e2_459_sota_cross_machine` says
   30min basic ALNS reached 459 (from 454) — so budget matters.
2. **Novel destroy operators** beyond minimal/basic/winning5.
3. **MaxSAT local repair** on the defect cluster (vol-58 explored).
4. **Cooperative ALNS** sharing best-bound across workers (untested
   in this codebase).

The "pipeline composition" axis is now exhausted at 60s ALNS.

## Linked

- [[strict-canonical-pipeline-honest-446]] — the 446 ceiling measurement.
- [[hint-pin-conflict-propagation-fix]] — unblocked the pipeline.
- [[../sessions/vol-118]].
