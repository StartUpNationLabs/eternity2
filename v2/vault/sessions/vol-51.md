# Vol-51 — bound-trigger prune-restart + engine-perf review

**Theme**: Post-vol-50 pivot to search-side innovation, locked-in
B1 (bound-trigger prune-restart). Built; trigger works; recovery
path is broken. Pivoted to B3 (engine profiling) but found vol-25
already did the comprehensive profiling work.

**Status**: CLOSED 2026-05-15 — net negative on records, modest
infrastructure shipped, sharpened understanding of perf gap.

## What was shipped

### Engine — `relaxed_bound` extracted to bench-audit lib

`pub fn relaxed_bound(puzzle, board) -> u32` is now a public helper
in `crates/bench-audit/src/lib.rs`. Previously only inline in
`bin/edge_bound_ascent.rs`. Enables any future driver to compute
the vol-21 relaxed bound for inter-round diagnostics.

### Driver — `prune_restart --bound-trigger`

Two new flags:
- `--bound-trigger`: enables bound-stall escalation (default off).
- `--drop-k-bound-stall N`: drop_k when escalating (default 60).

Per-round bound now logged in summary.csv (new column).

Trigger semantics (after revision):
- When score is stagnant AND board is fully placed:
  - Drop `drop_k_bound_stall` cells (mismatch + halo).
  - Continue with the bigger drop instead of stopping.

## Findings

### F1. Bound-trigger CORRECTLY fires on stagnation

A/B 8r × 30s, canonical-E2 seed=1:
- Round 1-3 normal: depth 27→144→80, score 23→278→412.
- Round 4: full board, score=412 stagnant → trigger fires, escalates
  drop_k 30 → 60, drops 164 cells (105 mismatch + 59 halo).
- Round 5: CP-MaxScore from 92 pinned, refilled 140/256, score 188.

### F2. Recovery path is the bottleneck, not the trigger

Round 5 score (188) is much WORSE than the partial we left behind
(412). Two causes:
- Drop k=60 + halo expansion = 164 cells dropped (5.5× requested).
- CP-MaxScore on a 164-cell residual cannot refill in 30s; only
  140 cells re-placed.

Net: bound-trigger as designed does NOT lift score above non-trigger
baseline. The infrastructure is sound but the recovery operation
needs more work (e.g., LNS-style local re-search instead of whole-
board CP, or much larger per-round CP budget).

### F3. B3 engine-perf profiling is mostly done by vol-25

Vol-25 already shipped 7 fixes + identified 4 remaining backlog
items in [[engine-perf-hot-paths]]:
- joe_depth150_bp: 6.864k → 8.4k nps (+22.4%)
- BLACKWOOD_RAW: 347k → 440k nps (+27%)

The 4 remaining wins are engineering (each 30min-2h, 2-15% gain).
There is no further research-grade profiling work to do.

**Apples-to-apples vs community**: our vanilla_fast = 125M nps
single-thread / 577M aggregate × 8 cores (vol-32). McGavin's
295M nps is likely single-thread. We are actually faster aggregate.
The "4000× gap" in my vol-50 / vol-51 draft was comparing our heavy
propagator profile (joe_depth150_bp, 75k aggregate) to their
vanilla figure — **not a real gap**.

## Vol-51 disposition

- B1 infrastructure shipped (lib + bin flag).
- B1 empirical: trigger fires correctly; recovery is the bottleneck.
- B3 scoped to profiling: already done by vol-25.

Standing record: 458 (vol-32). Unchanged.

## Open frontiers for vol-52+

1. **LNS-style recovery for bound-trigger**: instead of dropping K
   cells and running whole-board CP-MaxScore, run CP only on the
   dropped subset (anchored constraints from the surrounding fixed
   cells). Smaller search space, faster re-fill. Estimated 1-2 days.

2. **Vol-25 backlog perf fixes**: incremental AC-3 count maintenance
   (~10-15% on joe), SIMD restore (2-4%), `restore_or_simd` etc.
   Pure engineering; collectively maybe +20% on joe. Useful but
   not record-breaking.

3. **McGavin-style search-tree memoization**: BACKLOG entry
   `no-good-CDCL` (deferred long); learning conflict clauses.
   Multi-week build, EV high.

4. **Vol-46's open frontier**: lifted-LP with column-generation
   per-piece subproblems. Vol-47 tried naive McCormick column-gen
   and it failed. Per-piece decomposition is structurally different
   — could be tractable. Multi-week build.

## Linked

- [[../plans/CURRENT-VOL|CURRENT-VOL]] (will be reset for vol-52)
- [[vol-50]] — predecessor
- [[../concepts/lp-integer-gap-anatomy]] — vol-50 math
- [[../concepts/engine-perf-hot-paths]] — vol-25's profiling work
- [[../concepts/relaxed-bound]] — vol-21 origin of bound
- [[../concepts/prune-restart]] — vol-23 origin of restart
