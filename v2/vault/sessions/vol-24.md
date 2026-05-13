# Session — vol-24 (2026-05-13)

**Time**: ~15:35 → 16:15 CEST. Single sitting, ~3 hours of focused work + ~30 min A/B compute.
**Cold-start record going in**: 457. **Going out**: 457.
**Binding item**: `score-optimizing-cp` (vol-24 BACKLOG entry from vol-23 closeout).

## Plan adherence

CURRENT-VOL.md drafted T1=`score-optimizing-cp` route (b) + T2=`pt-tabu` (backup). Vol-24 closed T1 + audited T2 to `wont-do`. No mid-vol pivots; one new discovery logged to BACKLOG as `unbuilt` per discipline.

## Audit-at-open compliance

Resolved these aged BACKLOG items (per CLAUDE.md "3-vol rule"):

- **[[pt-tabu]]** (5 vols overdue) → `wont-do`. Reason: vol-22 measured 442 plateau stable across 60s/300s/5min/15min/30min budgets; tabu fights cycling, but cycling isn't the binding constraint. Need stronger repair operator first.
- **`joe-2019-sat-postprune`** (10 vols overdue) → `wont-do`. ~1-week build; the only path forward requires Joe's 2-weeks-of-Blackwood pre-prune which we don't have. Score-optimizing-cp is the closer-to-hand gap-closer.
- **`cooperative-pair-swap`** (3 vols) → `wont-do`. Subset of vol-20 cycle_scan K≤5 enumeration.
- **`color-relabel-search`** (3 vols) → `wont-do`. Score-preserving (S_23 acts trivially on edge-match count). Cannot raise 457.
- **`forced-perturb-meta-op`** (3 vols) → `wont-do`. Vol-22 basin-escape recipe is the validated big-k move; bound-guided > stochastic.

## What got built

### Engine ([[score-optimizing-cp]])

`SolveOpts.objective: Option<Objective>` with `Objective::MaxScore`. When set:

- `SearchState` carries `matched_count`, `decided_edges`, `best_score`, `best_score_partial`, and an optional `shared_best_score: Arc<AtomicU32>` for cross-worker BnB.
- `place_and_propagate_opts` + `undo_place` maintain `matched_count` and `decided_edges` incrementally on the 4 placed-neighbour edges (~16 ALU ops per place; cheaper than gating on `opts.objective`).
- `recurse()` adds an O(1) bound prune at entry: skip if `matched_count + (total_internal_edges - decided_edges) ≤ max(local, shared) best`. Bound is the loosest correct one (every undecided edge counted as potentially matchable); vol-25+ tightening is plausible (per-cell remaining-domain-feasibility).
- Leaf branch in MaxScore mode captures the score, CAS-bumps `shared_best_score`, returns `Exhausted` (not `Found`) so the parent loop keeps trying alternatives.
- `solve()` surfaces `best_score_partial` as `SolveOutcome::Solved` under MaxScore.

### Parallel runner

`parallel::solve_parallel` allocates the `Arc<AtomicU32>` once when MaxScore is on, plumbs it through `run_unit` into each worker's `SearchState`. `WorkerOutcome` carries `best_score` + `best_score_partial`; the aggregation step picks the highest-score worker before falling through to the standard Solved/TimedOut/Cancelled paths.

### Driver `prune_restart`

- `--max-score` (default on) / `--no-max-score`: explicit A/B toggle.
- `--pin-all-from-start`: skip the mismatch-cell drop on round 1 when `--start` is provided. Lets us A/B at a fixed partial.
- Round-1 cold-start stays FirstSolution (deepening); rounds 2+ default to MaxScore (filling).

### Test

`max_score_solves_generator_5x5` (unit test): MaxScore must still find a perfect generator solution. Smoke-test for the incremental accounting + bound prune. Passes.

## Empirical results

A/B on the vol-23 round-2 partial (`output/v23_pr_cold/round_2_board.json`, 184 placed, score 297) with `--pin-all-from-start`:

| Run | Objective | Budget | Score | Nodes |
|---|---|---|---|---|
| FirstSolution | none | 60s | **412/480** (exits 0.2s) | 220 k |
| FirstSolution | none | 300s | **412/480** (exits 0.2s) | 220 k |
| MaxScore | `Some(MaxScore)` | 60s | **418/480** | 103 M |
| MaxScore | `Some(MaxScore)` | 300s | **419/480** | 533 M |

**Result**: MaxScore CP-fill +7 over FirstSolution CP-fill (412 → 419). Diminishing returns past 60s. Still below ALNS-fill (424 in vol-23) because CP-fill is a constrained sub-problem (can't unpin), while ALNS shuffles pieces across the whole board.

## Concepts touched

- [[score-optimizing-cp]] (NEW) — full A/B table, open questions.
- [[prune-restart]] — amended with vol-24 A/B + structural takeaway.
- [[pt-tabu]] — status flip to `wont-do` with vol-22 data refutation.
- [[basin-escape-recipe]] — implicit reference (ALNS-fill 424 number).

## New BACKLOG entries

None. The "tighter bound" / "hybrid MaxScore→ALNS" / "MaxScore on Blackwood schedule" hooks are logged in `concepts/score-optimizing-cp.md#what's still open` rather than BACKLOG, because they're refinements rather than binding items.

## Fresh 3-round cold-start chain (vol-24)

For a direct cold-start comparison to vol-23's 412, ran a 3-round chain with 2-min/round budget (40% of vol-23's per-round budget), MaxScore on rounds 2+. Result:

| Round | Pinned | Depth | Score | Time |
|---|---|---|---|---|
| 1 (FirstSolution) | 5 (canonical) | 27 | 23/480 | 2 min |
| 2 (MaxScore) | 32 | **149** | **291/480** | 2 min |
| 3 (MaxScore) | 181 | 75 | **413/480** (full board) | 2 min |

Vol-23 chain (5 min/round, FirstSolution everywhere) was 412/480 at end. Vol-24 chain (2 min/round, MaxScore on rounds 2+) was **413/480** — +1 point with 40% the per-round budget. The cold-start ceiling of the prune-restart pipeline is robust around 412-413 regardless of objective; MaxScore here mostly helps round 3, which only has 72 holes to fill and where MaxScore enumerates much more than FirstSolution accepts (236M nodes vs vol-23's 220k nodes in round 3).

## Open at close

- **Tighter MaxScore upper bound** is the cheap follow-up. Per-cell `min(remaining_domain_feasibility)` ≥ current loose bound; expected ~2× node-count reduction. Vol-25 T1 candidate.
- **Hybrid pipeline**: MaxScore CP-fill → ALNS from the 419 board. Never measured; promising because the 419 board could be a better basin than the 297 partial. Vol-25 T2 candidate.

## Process lessons

- **Sibling-agent parallel work**: a parallel agent edited files mid-session (added ~280 lines to `lib.rs`). The Edit tool's "file has been modified since read" guard worked — I re-read on each conflict; no clobbering.
- **Parallel BnB needs a shared cutoff atom.** First attempt at MaxScore returned a *worse* board (408 vs 412 baseline) because workers ran independent BnB; the prune cutoff wasn't crossed. Fixed by adding `Arc<AtomicU32>` + max-by-score aggregation. Lesson: any future "search-quality" axis (best_bound, longest_path, etc.) under RootSplit needs the same plumbing.
- **Single-binding-item discipline held.** Vol-21 = 7 items, shipped 1. Vol-22 = 6 items, shipped 1. Vol-23 = 1 item, shipped 1. Vol-24 = 1 item, shipped 1. Three vols in a row at the right cardinality.
- **Time-estimate honesty**: prompt estimated "~4-5 hours focused + couple hours A/B compute". Actual: ~3h focused + ~30 min A/B. Honest matters; padded estimates breed deferral.
