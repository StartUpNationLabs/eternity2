---
name: fanout-sort-value-order
description: "Vol-108 T2 — static value-ordering heuristic for blackwood-fast buckets: sort each candidate bucket by descending 'fanout' (sum of bucket sizes the candidate's bottom + right edges would create downstream). Free at runtime. REFUTED: same trajectory at strict v17a (same max_depth 192, score 344) but 5-6% nps regression (80M vs 85M PGO+T1)."
metadata:
  type: project
status: refuted
---

# Fanout-sort value ordering (vol-108 T2 — REFUTED)

**Status**: `refuted` 2026-05-16 ~12:00 CEST.
**Origin**: brainstorming "what's a cheap value-ordering heuristic
that improves blackwood-fast without changing the engine shape?"

## The idea

Per piece-rotation pr, define:

```
fanout(pr) = Σ_{top∈colors} bucket_size((tbl=0, top, left=pr.right))
           + Σ_{left∈colors} bucket_size((tbl=0, top=pr.bottom, left))
```

This sums over all bucket sizes that pr's right edge (→ left of
D+1) and bottom edge (→ top of D+w) would create as constraints
downstream. High fanout = piece is "future-flexible" — many
candidates can satisfy its downstream cells.

Sort each candidate bucket by descending fanout. Tries
future-flexible pieces first.

Cost: O(N_PIECES × 4 × 32) at index build (sub-second). FREE at
runtime — the bucket order is baked in.

## Measurement

Single-thread canonical Selby-Riordan 16×16, v17a strict, 10s × 3
runs (PGO + T12 + T1 const-tables baseline):

| variant                       | nps (M)   | max_depth | score |
|-------------------------------|----------:|----------:|------:|
| baseline (no fanout)          | 84-85     |       192 |   344 |
| + fanout-sort (T2)            | **80**    |       192 |   344 |

Same trajectory (max_depth, score, nodes-visit pattern unchanged).
~5% nps regression.

Multi-thread 30s 4t v17a: score 429 (vs 444 baseline) — perturbed
the trajectory to a slightly worse outcome on this seed.

## Why it doesn't help

- The schedule v17a strict has a depth wall at 192 regardless of
  value ordering — pieces are constrained by the schedule's
  heuristic-edge count requirement, not by fanout.
- The fanout heuristic correlates with piece "popularity" — but
  high-fanout pieces also tend to be high-popularity pieces that
  ALREADY appear early in the rare-pid-sort or in many buckets.
  Sorting by fanout doesn't add information.
- The sort changes the bucket layout in memory, hurting cache
  locality (small but real ~5% nps cost).

## Why it might still pay off elsewhere

- Schedules with no depth wall (e.g. pure DFS without schedule) —
  fanout might actually help the search find deeper trajectories
  before backtracking.
- Generated puzzles with uniform color distribution (no rare-pid
  asymmetry to start with).

Not pursued further; refuted for the canonical-E2 v17a path.

## Linked

- [[blackwood-fast]] — the engine this was applied to.
- [[vol-108]] — origin.
- [[rust-perf-at-scale]] — perf log; T2 doesn't make it onto the
  table.
