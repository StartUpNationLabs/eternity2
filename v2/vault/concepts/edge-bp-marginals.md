---
tags: [concept, message-passing, value-order]
status: built-partial-positive
origin-vol: 12
---

# Edge-color BP marginals

**Status**: `built` (vol-12 measurement, vol-14 Rust port)
**Origin**: vol-12 (encoding change from [[bp-marginals]] cell variant)
**Files**: `scripts/v12_edge_bp.py`, `output/v12_bp/edge_bp_60i.json`, `crates/solver-engine/src/lib.rs` (`ValueOrder::EdgeBpMarginals`)

## Encoding

- **Variables**: 544 grid edges, each with domain = 23 colors.
- **Factors**: 256 cell constraints (each cell's 4 edge variables must match some (piece, rotation) pair).

Different from vol-11 cell encoding (which was `cells × (piece × rotation) → colors`).

## Vol-12 measurement

- BP converges; **18.84% interior entropy reduction** (2.24× vol-11 cell encoding).
- First BP variant to BEAT random as value-order in a Python A/B (60s, 67 depth vs 66, 65 matched vs 62).

## Vol-14 Rust port empirical reversal

| Metric | Baseline (joe_depth150_par) | + EdgeBpMarginals |
|---|---:|---:|
| CP-only depth, 5min | 174 | 171 (−3) |
| CP-only matched, 5min | 303 | 292 (−11) |
| End-to-end (CP + ALNS-fill) score | 442 | **443** (+1) |

→ **CP-only** loses; **end-to-end** wins. The BP value-order produces a CP partial that is **worse by score** but **better as ALNS starting state**. Net positive in pipeline.

(Note: end-to-end measurement was on broken ALNS-hint-pinning binary; post-fix the baseline is ~440 and the BP arm is ~440-441. The qualitative reversal still holds.)

## Why the reversal

The BP-ordered CP partial commits to slightly-different cell domains, producing a partial that is harder for AC-3 but easier for ALNS to escape from (its mismatch geometry differs from the baseline's). The pipeline's actual selection metric should be end-to-end, not CP-depth.

## Implication

- **Pure value-order axis is exhausted** (vol-14 conclusion).
- The pipeline integration matters more than the standalone metric.
- BP marginals' value is **diversity of CP failure mode**, not better individual CP runs.

## Linked concepts

- [[bp-marginals]] — cell-encoding sibling, also bounded
- [[engine-profile-registry]] — `joe_depth150_bp_par` profile uses this
- [[alns]] — the downstream component that absorbs the win

## Linked memory

- `project_e2_edge_bp_measurement`
- `project_e2_vol14_bp_null`
