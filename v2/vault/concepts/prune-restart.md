# Prune-restart (McGavin in-place)

**Status**: `built` (vol-23 driver + engine batch hints)
**Originally aged**: since vol-14, 8 volumes deferred
**Built**: 2026-05-13 vol-23

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

## Build plan (DONE)

Took ~1 hour, not 1-2 days. Two pieces:

1. **Engine change**: `SolveOpts.batch_hint_application: bool` (new field). When true, `apply_symmetry_and_hints` pins all hints before any propagation, then propagates once at the end. Solves the order-sensitivity bug where mid-application propagation removes a row that a later hint needs.
   - File: `crates/solver-trait/src/lib.rs` (new field).
   - File: `crates/solver-engine/src/lib.rs` (apply_symmetry_and_hints batched branch).

2. **Driver binary**: `crates/bench-audit/src/bin/prune_restart.rs`. Multi-round loop: run CP, capture partial, pin all placements, re-run CP.

## First empirical result (CPU-contended smoke test, 30s/round, canonical 5 hints)

- Round 1 (joe_depth150_bp_par + v17a schedule): depth 27, score 23, 32 cells placed.
- **Round 2 (batch hints + gacolor_ac3_par, pinning the 32 cells)**: **depth 150, score 289, 182 cells placed** in 30s. Δ +266.
- Round 3 (pinning 182 cells): gacolor wipeout — color-pool inconsistency at 70%+ pinned.

Vol-23 conclusion: prune-restart concept VALIDATED. Round 2 lift of +266 is genuine; the engine pruned much harder from the richer initial state.

Next steps:
- Run from a high-bound basin start (e.g. [[basin-440-469]]).
- Round-3 wipeout handling: drop gacolor for round 3+, use bare propagation.

## Vol-23 cold-start full result (5min/round, 6 rounds, seed=1)

| Round | Pinned | Depth | Score | Time |
|---|---|---|---|---|
| 1 | 5 (canonical) | 27 | 23/480 | 5 min |
| 2 | 32 | **152** | **297/480** | 5 min |
| 3 | 184 | 72 | **412/480** (full board!) | 0.2s |
| 4 | 256 (stagnates) | 6 | 412 | stop |

The cold-start CP-only chain reaches a **full 412/480 board** in ~10 min. Bound of the final board is 441 (gap +29), Hamming distance 247 from our 457 — a completely new basin, but with a LOWER ceiling than our 457 basin (441 vs 461).

Caveats:
1. Round 3 fills 72 cells in 0.2s via `FirstSolution` mode — first valid completion, not best. Cold-start CP doesn't optimize score; it satisfies constraints.
2. The 412 score is below our 457 because the random valid completion isn't optimal.

Future use:
- Round 2 produces a deep partial (depth 152, score 297) suitable for ALNS-fill.
- ALNS-from-prune-restart-round-2 should be tested vs vanilla cold-start ALNS.

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
