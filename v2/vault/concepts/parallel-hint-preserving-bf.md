---
name: parallel-hint-preserving-bf
description: "Vol-118 T5b — 8-thread hint-preserving Blackwood-schedule DFS produces SIGNIFICANTLY deeper partials than single-thread. 60s budget: single reaches depth 192/score 338; parallel-8 reaches depth 232/score 414 (244/256 placed). The per-thread shuffle of candidate-list buckets exposes search regions single-thread doesn't reach in budget. Pipeline output: Hungarian 432/480, ALNS pending."
metadata:
  type: project
---

# Parallel hint-preserving Blackwood (vol-118 T5b)

**Status**: `built` — shipped + measured 2026-05-16.

## Mechanism

`solve_blackwood_par_with_hints` spawns N workers via rayon. Each
worker has its own `RowMajorIndex` clone whose candidate buckets are
shuffled by `shuffle_buckets(seed_offset + tid)`. Each worker runs
`solve_blackwood_sized_pinned` with the shared pin state
(canonical 5 hints) and returns its best result. The deepest result
across workers wins.

## Empirical impact

Canonical 16×16 + v17a schedule + 5/5 hints, 60s budget:

| variant            | max_depth | score | placed | hints |
|--------------------|----------:|------:|-------:|------:|
| single-thread      |       192 |   338 |  194/256 |  5/5 |
| par-8 (seed-off 0) |       232 |   414 |  232/256 |  5/5 |

That's +40 depth, +76 score, +38 cells placed.

Pipeline (par-8 partial → bound-ascent → Hungarian):
- Bound-ascent: 411/480, UB 460.
- Hungarian: 432/480 (5/5 hints OK).

## Why parallel helps

Single-thread DFS with the strict v17a schedule reaches depth 192
then stalls (the schedule's heuristic-edge floor + the canonical
hint pinning create dead-end branches that the strict candidate
order can't escape).

Parallel workers shuffle the candidate ordering at each (top_color,
left_color) bucket. With different orderings, different workers
explore different branches first. Some find paths the strict
single-thread doesn't reach in 60s.

This is a classic "parallel diversification" win: cheap (8 cores
× 1 instance = 8 attempts), and effective because the schedule's
search space is much larger than 60s of single-thread can cover.

## Implications

For strict-canonical pipeline work:
1. **Always use --threads 8** (or --threads N for available cores).
2. **Sweep --seed-offset** to find diverse partials.
3. Combined with vol-116 hint-preserving Hungarian, this gives
   the deepest 5/5-canonical partial pipeline ever measured here.

For raw matched-edges work: par-8 of bf_bw (no hints) was already
the default in vol-115.

## Code

- `crates/blackwood-fast/src/lib.rs::solve_blackwood_par_with_hints`
- `crates/blackwood-fast/src/bin/bf_bw_schedule_hinted.rs` — flags
  `--threads N --seed-offset O`.

## Linked

- [[hint-pin-conflict-propagation-fix]] — the bug fix that unblocked this.
- [[hint-compliance-clarification]] — convention reference.
- [[../sessions/vol-118]].
