# vol-33 — code-quality refactor (vol-25 deferred items, shipped)

**Date**: 2026-05-14
**Theme**: ship the vol-25 refactor items deferred 8 volumes. Pure
code cleanup; no algorithms, no record chase.

## Raw

This volume is the "vol-25 cleanup" the user asked for at vol-32 close.
Plan was [VOL-33](../plans/VOL-33.md).

## What was attempted (all shipped)

All 5 binding items, sequential commits:

- **T1** `extract-eternity2-time-crate` (commit `bbe6ef5`).
- **T2** `extract-eternity2-export-crate` (commit `52f790a`).
- **T3** `split-solver-engine-lib-into-modules`, in 3 sub-commits:
  - T3a paths.rs (`e7541f1`)
  - T3b schedule_builders.rs (`e886e66`)
  - T3c config.rs + profiles.rs (`a5387ee`)
- **T4** `extract-eternity2-puzzle-io-crate` (commit `0de50d3`).
- **T5** `consolidate-bin-harness` — partial: harness shipped + 2
  example migrations (commit `1b3bb2b`).

## What was measured / kept

| Refactor | Lines moved | Sites touched |
|---|---:|---:|
| time crate | 60 (dup → 1) | solver-engine, solver-naive |
| export crate | 230 (3 dups → 1) | bench-audit, benchmark, ~50 bins via re-export |
| paths.rs | 461 | solver-engine internal |
| schedule_builders.rs | 531 | solver-engine internal |
| config.rs + profiles.rs | 780 | solver-engine internal |
| puzzle-io crate | 131 (dup → 1) | benchmark, 72 bins via re-export |
| bench-audit harness | +267 in lib, −22% to −39% per migrated bin | 2 demo bins, 70 to go |

**solver-engine/src/lib.rs**: 5355 → 3705 lines (−31%).

Pre-existing tests + workspace build still pass at every step.

## What was refuted

Nothing — refactor volume, no hypotheses tested.

## Concepts touched

- [[code-debt]] — items measured at vol-25, finally executed.

## Open at close

- T5 has 70+ remaining bins that mechanically migrate to the new
  `bench_audit::harness::*` helpers. Each is independent and
  ~10-15 min of grunt work. Carries to BACKLOG as
  `bin-harness-mass-migration`, status `partial`.

## Linked memory

- New: [[../../../.claude/.../memory/project_e2_vol33_refactor_shipped]] —
  the 8 vols-deferred refactor items are now `built` (T1-T4, T5 partial).
- Existing: [[../../../.claude/.../memory/project_e2_vol16_cleanup_anchor]] —
  vol-25 measurement remains the canonical assessment of code debt.
