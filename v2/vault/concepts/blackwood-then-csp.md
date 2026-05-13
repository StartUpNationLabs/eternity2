---
tags: [concept, pipeline, composition]
status: built-not-evaluated
origin-vol: 17
---

# Blackwood-then-CSP (Variant K pipeline)

**Status**: `built` shape (vol-17 Variant K); full evaluation deferred
**Origin**: vol-17 closeout proposal (memory `project_e2_vol17_blackwood_then_csp`)
**Files**: `crates/bench-audit/src/bin/run_e2_blackwood_then_csp.rs` (vol-17 shipped Variant A)

## Motivation

Vol-15: Blackwood gives +260-270 ALNS lift when its seeds are used post-hoc as ALNS starting points. But vol-15's full Blackwood run plateaus around depth 80-87 due to the schedule wall ([[blackwood-layered-depth-wall]]).

**Idea**: run Blackwood ONLY as a SEED GENERATOR (target depth ~85, the natural break-statistic peak), then convert its placements to canonical hints and run standard CP+ALNS to fill the rest.

## Variant A (sequential, vol-17 shipped)

1. Run `BLACKWOOD_RAW` (or `calibrated_v17b`) for fixed budget (e.g. 60s).
2. Capture the best partial (~85 cells, schedule-rich).
3. Convert to `Hints` payload.
4. Feed `joe_depth150_bp_par` + canonical 5 hints + Blackwood hints to fill.
5. Run ALNS-PT on the filled board.

## Three implementation variants (vol-17 proposal)

- **A (sequential)**: as above. ~1 day. Shipped.
- **B (overlapping)**: Blackwood runs continuously while CP+ALNS uses snapshots. Requires inter-process state sharing.
- **C (in-engine)**: Blackwood schedule fires only at scan-order depth ≤ 85; standard propagators above. Single-engine, no IPC.

## Status

Variant A binary exists; **full evaluation deferred** past vol-23 (prune-restart took priority — see [[prune-restart]] history of deferral).

The vol-23 result on prune-restart (Round 2 lift +266 score) suggests Variant A would similarly lift, since both pipelines exploit "richer initial state → harder pruning thereafter".

## Linked concepts

- [[blackwood-algorithm]] — front half of the pipeline
- [[blackwood-schedule-calibration]] — what fed the seed
- [[alns]] — back half
- [[prune-restart]] — parallel approach to the same insight

## Linked memory

- `project_e2_vol17_blackwood_then_csp`
- `project_e2_vol15_blackwood_results`
