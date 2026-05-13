# Bound-ascent

**Status**: `built` (vol-21), single-swap variant only
**Origin**: vol-21
**Files**: `crates/bench-audit/src/bin/edge_bound_ascent.rs`, `edge_bound_score_alt.rs`, `edge_bound_floor_alns.rs`

## Definition

Optimize the **relaxed-bound** (see [[relaxed-bound]]) instead of score. 2-piece swap mutations; accept moves that strictly increase relaxed bound.

## Results

- From our 457 (bound 461): bound climbs 461 → 462 → ... → 468 in 710 iters (greedy). Score collapses 457 → 128.
- From 450/465 board: bound climbs to 473 in 4254 iters; 50k iters: bound 475.
- Multi-seed 2000 iters: bounds 467-471, median 470.

## What FAILED

- **`bound-floor-alns` (vol-22 T1)**: bound-ascend +1, then reject any ALNS repair that drops bound. EMPIRICALLY NULL: 0/9 attempts preserved bound floor; ALNS always returns to our 457 with bound 461.
- **`alternating bound-score` (vol-21)**: bound-ascend, then ALNS-recover. Every step undone within 30s; lands on byte-identical 457.

## What WORKS

- **`basin-escape-recipe`**: bound-ascend → Hungarian match → ALNS. Escapes 457 lock. See [[basin-escape-recipe]].

## Open extensions (`unbuilt`)

- **`multi-cell-bound-ascent`**: 3-cycle, 4-cycle moves. Single-swap plateaus at bound 470-475; multi-cell might break through.
- **`bound-ascent-with-CP-recovery`**: bound-ascent → Blackwood CP from canonical hints with bound state as value-order guide. Vol-22 T2.

## Linked concepts

- [[relaxed-bound]] — the metric being optimized
- [[basin-escape-recipe]] — the successful composition
- [[operator-lock]] — bound-ascent crosses the lock but can't preserve score
