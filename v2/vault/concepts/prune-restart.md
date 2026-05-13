# Prune-restart (McGavin in-place)

**Status**: `unbuilt`
**Aged**: since vol-14 (8 volumes)
**Priority**: highest EV unbuilt item

## Definition

Run standard Blackwood CP until hitting a hard wall (e.g. depth ~150). Instead of backtracking past depth d:
1. Treat the current partial as locked-in pieces 0..d-1 with their domains.
2. Re-prune remaining cells from depth d onwards using the locked pieces as constraint sources (richer than starting AC-3).
3. Restart DFS from depth d under new pruning.
4. Iterate the prune-restart cycle.

The engine needs a `PruneAndRestart` policy that "forgets" backtracking history but keeps deeper constraint inferences. Memory of failures = no-good learning at the lock depth.

## Why it matters

- McGavin's 469 result is reached by exactly this algorithm.
- Joe's 2019 SAT solve used 11h on a domain pre-pruned by 2 weeks of Blackwood with this technique.
- **Vol-22 finding**: ALNS-saturation gap in fresh basins is 25-30 score points. Prune-restart's global enumeration should close this gap in minutes instead of hours.

## History of deferral

- vol-14 plan: T1.
- vol-15 plan: T1.
- vol-16 plan: deferred for cleanup.
- vol-17 plan: T6.
- vol-18 plan: not listed (chased cooperativity instead).
- vol-19, 20: not listed.
- vol-21 plan: T1.
- vol-22 plan: T6.
- vol-23 plan: T2.

**Pattern**: every vol-plan lists this; every vol does something else.

## Build plan

- File: `crates/solver-engine/src/lib.rs`
- Add `PruneRestart` variant of `EngineConfig::variable_order` OR a new top-level policy field.
- Reuse `EngineSolver::blackwood_raw_par`.
- Estimated 1-2 days.

## Linked sessions

- vol-14: deferred (chased frame-first which was null).
- vol-15: deferred (calibrated Blackwood schedule + BLACKWOOD_RAW shipped instead).
- vol-21: deferred (chased edge-relax which was a real finding but score still 457).
- vol-22: deferred (chased basin-escape recipe — real finding, score still 457).

## Linked concepts

- [[bound-ascent]] — the ALNS-saturation gap that prune-restart should close.
- [[basin-escape-recipe]] — produces high-ceiling basins where prune-restart could realize the ceiling.
- [[relaxed-bound]] — the metric that quantifies the gap prune-restart should close.

## Linked memory

- `project_e2_vol14_mcgavin_blackwood_gap_analysis` — original gap analysis.
