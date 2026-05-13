# Session — vol-23 (2026-05-13)

**Time**: ~14:25 → 15:25 CEST (~1h focused work, after vault refactor at vol-22 close).
**Cold-start record going in**: 457. **Going out**: 457.

## Plan adherence (the audit-at-open we promised)

Vol-22 closeout drafted CURRENT-VOL.md with three items; user narrowed at vol-23 open to **T1 only** to fight the deferral pattern.

- **T1 — `mcgavin-prune-restart`**: aged 8 vols. **PICKED. BUILT.** No more deferral.
- T2 — `pt-tabu-zobrist`: aged 5 vols. Stayed in BACKLOG (intentional narrowing per user).
- T3 — Read overnight results: superseded — user killed the background runs mid-session to free CPU; conclusions logged inline.

This is the first volume in 9 (vol-14 → vol-22) where prune-restart was on the plan AND got built.

## What got built

- Engine change: `SolveOpts.batch_hint_application: bool` in `crates/solver-trait/src/lib.rs`. When true, `apply_symmetry_and_hints` pins all hints' domains before any propagation, then runs one batched propagation pass. Solves the order-sensitivity bug where mid-application propagation removes a row a later hint needs.
- Driver: `crates/bench-audit/src/bin/prune_restart.rs`. Multi-round loop with `--drop-k` halo control; engine selection by hint count (cold-start → joe_depth150_bp_par+v17a schedule, mid-pin → gacolor_ac3_par, heavy-pin → border_first_lcv_par to avoid gacolor false-positive wipeouts).
- 4 callsites updated for the new `SolveOpts` field (wasm, server, verhaard_e2, prune_restart itself).

## Empirical results

### Cold-start prune-restart, seed=1, 5min/round, 6 rounds

| Round | Pinned | Depth | Score | Time |
|---|---|---|---|---|
| 1 | 5 (canonical) | 27 | 23/480 | 5 min |
| 2 | 32 | **152** | **297/480** | 5 min |
| 3 | 184 | 72 | 412/480 (full board) | 0.2s |
| 4 | 256 | 6 | 412 (stagnate) | stop |

Concept VALIDATED: round 1→2 lifts depth 27→152 / score 23→297 (Δ +274). The pruned/restarted CP propagates much harder from the depth-27 prefix than from canonical 5 hints alone.

### ALNS-fill from round-2 partial (5 min)

- Started: 297/480, 184 placed, 72 unplaced.
- Finished: **424/480**, bound 437.

This UNDERPERFORMS vanilla cold-start ALNS (vol-22 batch median 430-450, best 451 at seed 112).

### Why prune-restart-as-cold-start-seeder UNDERPERFORMS

CP runs in `FirstSolution` mode: it takes the FIRST valid completion of the 72 free cells, not the best. The 184 pinned cells came from CP's own exploration (which doesn't optimize score), so they're a *feasible* prefix, not a *good* prefix. ALNS then can't undo the pinned cells.

The structural insight: **prune-restart is a CP DEEPENER, not a score MAXIMIZER**. It excels at "how deep a consistent placement can CP construct" — the McGavin/Joe use case for an unsolved puzzle is finding 480-level solutions, where consistency = correctness. For optimization on partial boards (our use case at 457), CP without score in the objective produces feasible-not-optimal prefixes.

This is a non-trivial conclusion: it tells us where prune-restart DOESN'T pay off, sharpening BACKLOG priorities.

## Concepts touched

- [[prune-restart]] — status flipped from `unbuilt` (8 vols aged) to `built` with empirical caveats.
- [[basin-440-469]] — attempted on it, refuted (CP filler produces 391-412 score, worse than the 440 start).
- [[basin-escape-recipe]] — vol-22 batch result documented (16 seeds, best 451 still < 457).

## New BACKLOG entries

- `score-optimizing-cp` (vol-23) — the gap prune-restart didn't close. Routes via MaxSAT (blocked on kissat-rc2) or branch-and-bound CP with edge-match objective.

## Killed background runs (CPU freed at user request, 14:50 CEST)

- PID 66809: 8h alns_pt on 440/469 basin. 47 min in, no improvement logged. Pattern from vol-22 (442 plateau across 5-30 min PT) held.
- PID 66953: 100-seed batch basin recipe. 16 seeds completed: scores 428-451, bounds 450-465. Best score 451 (seed 112). Predictably below 457.

Both logged in [[basin-440-469]] and [[basin-escape-recipe]].

## What we owe to vol-24

Per audit-at-open: items aged 3+ volumes that must resolve.

- [[pt-tabu]] — 5 vols overdue. Defer-or-resolve at vol-24 open.
- `kissat-rc2-maxsat` — 1 vol old, but blocks `score-optimizing-cp` (the prune-restart gap-closer). Pick if route to better cold-start record.
- `cooperative-pair-swap`, `color-relabel-search`, `forced-perturb-meta-op` — all 2 vols old; mark `wont-do` if not picked by vol-25.

## Process lessons (for the vault discipline)

- **Narrowing CURRENT-VOL to 1 item worked.** Vol-21 plan was 7 items, vol-22 plan was 6 items; both delivered 1. Vol-23 plan was 1 item, delivered 1. Single-binding-item is the right cardinality when one item is meaningfully sized (1-2 days).
- **Stop background experiments when CPU is contended.** The 8h PT and 100-seed batch each ran 47 min and produced no actionable signal worth the contention slowdown of T1's smoke tests. Schedule heavy compute for genuinely uncontended windows.
- **Negative results count.** Prune-restart-as-cold-start-seeder didn't beat 457 — but the WHY (FirstSolution vs score-optimizing) is a clean conclusion that re-shapes the BACKLOG.
