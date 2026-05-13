# Score-optimizing CP (MaxScore objective)

**Status**: `built` (vol-24 — engine + driver)
**Origin**: vol-23 finding (prune-restart-as-CP-filler underperforms because CP defaults to FirstSolution mode).
**Files**:
- `crates/solver-trait/src/lib.rs` — `Objective::MaxScore`, `SolveOpts.objective`
- `crates/solver-engine/src/lib.rs` — `SearchState.{matched_count, decided_edges, total_internal_edges, best_score, best_score_partial, shared_best_score}`; bound-prune in `recurse()`; leaf-capture branch; outcome surfacing in `run_impl`
- `crates/solver-engine/src/parallel.rs` — shared `Arc<AtomicU32>` cutoff + max-by-score worker aggregation
- `crates/bench-audit/src/bin/prune_restart.rs` — `--max-score` / `--no-max-score` / `--pin-all-from-start`

## Definition

Branch-and-bound CP that optimises the matched-edge count instead of returning the first valid completion.

Engine carries running counters on `SearchState`:

- `matched_count: u32` — internal edges with both ends placed AND colors agree (excluding BORDER 0). Incremented in `place_and_propagate_opts` on each placed neighbour at place time; decremented in `undo_place` (LIFO discipline).
- `decided_edges: u32` — internal edges with both ends placed. Same incremental discipline.
- `best_score: u32` and `best_score_partial: Option<Board>` — best leaf observed so far in this worker.
- `shared_best_score: Option<Arc<AtomicU32>>` — cross-worker cutoff under RootSplit parallelism.

At every `recurse()` entry (before position selection), the prune fires when:

```
matched_count + (total_internal_edges - decided_edges)  ≤  max(best_score, shared_best_score)
```

`≤` (not `<`) because a tie can't improve the running best. Single-threaded runs use `best_score` only; RootSplit workers use `max(local, shared)`.

At a leaf (no more positions to fill) under MaxScore: capture `matched_count` if it beats local `best_score`, CAS-bump `shared_best_score`, return `Exhausted` (not `Found`) so the parent loop keeps trying alternatives. After all branches exhausted, the engine surfaces `best_score_partial` as `SolveOutcome::Solved`.

## Upper bound (loose, current implementation)

`remaining_upper_bound = total_internal_edges - decided_edges`

Every still-undecided internal edge is counted as potentially matchable. Sound (it's ≥ the actual achievable additional matches) and O(1) to maintain. Loose: a tighter bound would account for piece-uniqueness and per-edge domain feasibility, expected to roughly halve node count on canonical E2 (vol-25+ refinement).

## What we measured (vol-24)

A/B on `output/v23_pr_cold/round_2_board.json` (depth 152, 184 placed, score 297) with `--pin-all-from-start`:

| Run | Objective | Budget | Score | Nodes |
|---|---|---|---|---|
| FirstSolution | none | 60s | **412** (exits at 0.2s) | 220 k |
| FirstSolution | none | 300s | **412** (exits at 0.2s) | 220 k |
| MaxScore (60s) | `Some(MaxScore)` | 60s | **418** | 103 M |
| MaxScore (300s) | `Some(MaxScore)` | 300s | **419** | 533 M |

**MaxScore CP-fill beats FirstSolution CP-fill by +7 points** (412 → 419) on the vol-23 chain's round-2 partial. Diminishing returns past 60s (60s → 300s = +1 point for 5× more nodes).

Comparison to non-CP fillers from the same partial:
- ALNS-fill: 424 (vol-23 measured). +5 over MaxScore CP-fill.
- Vanilla cold-start ALNS (no pinning): 430-450 median, 451 best (vol-22 batch, seed 112).

## Why MaxScore beats FirstSolution but loses to ALNS

CP-fill is a *constrained sub-optimisation*: given 184 pinned cells, find the best fill for the 72 holes. The 419 ceiling is the structural maximum of that sub-problem.

ALNS-fill is *unconstrained search*: it can unpin cells, swap pieces across the whole board, shuffle into different basins. The 424 it reaches uses moves that violate the 184-cell pinning.

So MaxScore closes the gap *within the prune-restart pipeline* but doesn't change the pipeline's ceiling vs alternative methods. The takeaway for the cold-start search tree: ALNS dominates CP-fill at the round-2 partial; MaxScore makes CP-fill less embarrassing but not competitive.

## What's still open

- **Tighter bound**: per-cell minimum-matchable-with-remaining-pieces. Expected ~2× node-count reduction.
- **Bound + ALNS hybrid**: use MaxScore CP-fill as an *initial filler*, then ALNS as a *re-optimiser*. The 419 board might be a better ALNS start than the 297 partial; never measured.
- **Score-optimising CP on Blackwood schedule**: combine MaxScore with break-index allowance to enumerate score-optimal completions under heuristic-side relaxation. Theoretical novelty: encodes McGavin's score-as-an-objective explicitly instead of relying on completeness.
- **MaxSAT route** (BACKLOG `kissat-rc2-maxsat`): the same objective via existing `sat-encoder` crate. Would give exact joint bound; MaxScore B&B gives anytime upper-bounded improvement.

## Cost model

- Build: ~4 hours focused work (engine 2h, driver 30min, parallel-aggregation refactor 1h, tests + A/B 30min). Estimate honest, not padded.
- Per-call overhead: ~16 ALU ops per place/undo for incremental counters; one AtomicU32 load per node; one CAS at each leaf. Measured negligible vs propagation cost.

## Linked concepts

- [[prune-restart]] — the parent pipeline. MaxScore is the fill-step sharpener.
- [[exact-joint-bound]] — the MaxSAT alternative. Different cost/strength tradeoff.
- [[relaxed-bound]] — basin-local ceiling metric; MaxScore CP-fill cannot exceed it.
- [[blackwood-algorithm]] — McGavin's algorithm uses a score-aware variant; MaxScore is the explicit version of what Blackwood does implicitly via schedule pruning.

## Linked memory

- `project_e2_vol23_pr_cold_start` — vol-23 baseline numbers, the "underperforms ALNS-fill" finding that motivated this.
