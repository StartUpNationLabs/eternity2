# Current vol — vol-106 CLOSED 2026-05-16 ~10:30 CEST

**Vol-106 closes with a full session of shipping**. Standing record:
459/480 (unchanged). Engine progress: 180× faster than prior + full
Blackwood algorithm port + pipeline to score 450-451 in 7 min.

See [[../sessions/vol-106]] for the consolidated results table.
See [[../concepts/blackwood-fast]] + [[../concepts/vanilla-v2]] +
[[../concepts/rust-perf-at-scale]] for durable references.

## Vol-107 candidates (from open-at-close)

1. **Basin-vs-ALNS-liftability characterisation** (T13.c follow-up).
   Different seed-offsets reach different basins; offset=0 happens
   to land in an ALNS-favourable one. Why? Vol-32-style σ-cycle
   analysis on offset basins. Could surface a heuristic for
   "ALNS-liftable" basin selection.

2. **Schedule + break-index calibration** (T2 follow-up). vol-15's
   v17b/v17c/v17d/v17e schedules haven't been ported. Each may
   reach different depth-wall positions. Empirical sweep across
   schedules × seed-offsets.

3. **Cross-machine throughput claim** (vol-15-style 459 cross-
   machine result). With 79M nps PGO+unrolled single-thread, we
   could in principle run multi-day on a beefy machine to compare
   to the standing 459. NOT a score-axis lottery — a benchmark
   of the new engine vs old engine on identical canonical puzzle.

4. **NEW INVENTION**: dependency-directed backtracking variant.
   When ALL candidates at depth d fail, backjump to the depth
   that caused the conflict (depth d-1 or d-w) directly. For
   row-major DFS the support is just {d-w, d-1}, so DDB collapses
   to chronological backtrack on our scan — UNLESS we instrument
   piece-uniqueness conflicts which can chain to much earlier
   placements.

5. **Per-schedule monomorphisation** of `solve_blackwood_unrolled_256`.
   Currently `targets[D]` and `conflicts_allowed[D]` are runtime
   loads. With per-schedule const tables and a const-generic
   schedule selector, these would fold. Expected additional
   ~5-10% nps on top of T12. Multi-day work.

## Linked

- [[../INDEX]]
- [[../DIRECTIVE_VOLS_106-115_BLANK_PUZZLE_SPEEDUP]]
- [[../concepts/blackwood-fast]]
- [[../concepts/vanilla-v2]]
- [[../concepts/rust-perf-at-scale]]
- [[../sessions/vol-106|vol-106 close]]
