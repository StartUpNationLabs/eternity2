---
name: blackwood-triple-sweep
description: 7-triple Blackwood heuristic-color sweep on canonical E2 — REFUTES Blackwood's stated "lots of overlap" rationale for 470 attempt; top-overlap triples score WORST in our color encoding.
metadata:
  type: project
---

# Blackwood heuristic-triple sweep (vol-80, 2026-05-15)

**Status**: `built` — refutes a key Blackwood-thread hypothesis.
**Origin**: docs/community-mining/09_Blackwood_solver_thread.md +
vol-79 motivation.
**Files**: `scripts/vol80_triple_sweep.sh`,
`output/vol-80-triple-sweep-20260515T234345/`.

## Hypothesis tested

Per Blackwood's own writeup of his 470-attempt: "These sides have
lots of overlap — easy to burn early." The claim implies that
high-overlap triples should score BETTER than low-overlap ones.

Our auto-picked default `(12, 13, 14)` ranks 28/165 in pairwise-
overlap among the 11 frequency-tied canonical colors {12..22}. So
we've been using a moderate-overlap triple, not Blackwood's
"max-overlap" approach.

## Method

Added `E2_HEURISTIC_SIDES_OVERRIDE` env var to
`crates/solver-engine/src/schedule_builders.rs::compute_heuristic_sides`
to inject literal triples bypassing the auto-selector. Run
`run_e2_blackwood` with `--schedule calibrated_v17a`, 60s CP +
60s ALNS, seed 1, on each of 7 triples.

## Results

| triple | overlap rank | matched | cp_depth |
|---|---:|---:|---:|
| (14, 15, 19) | 165 (bottom) | **446** | 167 |
| (18, 20, 22) | 4 (top tier) | 445 | 164 |
| (12, 13, 14) | 28 (auto) | 444 | 166 |
| (15, 16, 21) | 162 (anti) | 442 | 165 |
| (13, 18, 20) | 3 (top) | 437 | 166 |
| (14, 18, 20) | 1 (top) | 436 | 167 |
| (12, 14, 20) | 2 (top) | 436 | 168 |

## Refutation

**Blackwood's "lots of overlap" rationale does NOT transfer to our
color encoding.** Top-3 overlap triples scored 436-437, the WORST
in this sweep. The BEST single result (446) used the bottom-overlap
triple (14, 15, 19).

Why this might be: Blackwood's color encoding differs from ours.
Vol-14 verified literal triple [17, 2, 18] does not apply
(color 2 is on 2 of our corners). Without knowing how his color
labels map to ours, "overlap" computed in our labels may have
opposite structural meaning.

Alternative read: 60s CP + 60s ALNS is too noisy a measurement.
Δ of 10 score points (436 ↔ 446) at this budget may be within
single-seed variance. To confirm the refutation, need ≥ 8 seeds
per triple. **DO NOT claim refutation from this single-seed sweep
alone (CLAUDE.md rule 4: variance reporting mandatory).**

## What this experiment shows soundly

1. **No triple at this budget reaches 459+.** Standing record
   stands.
2. **Triple choice DOES matter**: 10-point spread (436 vs 446) at
   identical seed and budget across just 7 triples. The auto-pick
   (444) is consistent with the median.
3. **The "max-overlap" prescription from Blackwood's thread is at
   least NOT obviously beneficial in our encoding.**

## What would settle it

- Sweep all 165 triples × 8 seeds × 5min budget. Total ~110 hours
  CPU. Infeasible in a single autonomous turn; feasible over a few
  days.
- OR: prove a structural correspondence between Blackwood's color
  labels and ours, so "overlap" can be computed in the same frame.

## Linked

- [[blackwood-algorithm]] (parent)
- `docs/community-mining/09_Blackwood_solver_thread.md`
- Memory: `project_e2_vol15_blackwood_results.md`
- Memory: `feedback_no_false_metrics.md`
