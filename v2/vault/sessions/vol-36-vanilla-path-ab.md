# Vol-36 — vanilla_path A/B across 4 cell-visit orders

**Date**: 2026-05-14.
**Status**: T1 measurement done at 30s × single-thread. Next: 5min × 8 threads + ALNS for border-first.

## What this is

`vanilla_path` — a raw-DFS backtracker (no propagators, no ML), like
`vanilla_fast` but with a CUSTOM cell-visit path instead of hardcoded
row-major. Per-step pre-bucketing on constrained-side colors.

User-proposed (vol-36 open): "raw DFS with a path linking hints
then fill center then outside". This A/B answers: does path order
matter for raw-DFS depth/score reach?

## Implementation

- `crates/bench-audit/src/bin/vanilla_path.rs` (660 lines).
- Per-step constraint pattern (which NESW neighbours are placed by
  prior path steps) computed at init.
- Per-step buckets keyed by colors of constrained sides only;
  bucket count = 23^popcount(mask), max 280k per cell.
- Hot loop mirrors vanilla_fast: bucket-slice lookup at each enter_fresh.
- Built-in path modes:
  - `row-major` (control, matches vanilla_fast)
  - `hint-link` (user idea: 5 hints connected by shortest paths,
    then centre-out spiral)
  - `outer-spiral` (border ring, then concentric inward squares)
  - `border-first` (entire perimeter, then row-major interior)
  - `--path-csv` for arbitrary user-supplied path

## A/B results (30s, single-thread, no propagators)

| Path mode | Max depth (along-path) | Matched edges | pp/s | Verdict |
|---|---:|---:|---:|---|
| row-major | 210 | 433/480 | 66M | baseline |
| **border-first** | **215** | **445/480** | 63M | **+12 edges over row-major** |
| outer-spiral | 99 | 204/480 | 107M | mediocre |
| hint-link | 48 | 51/480 | 85M | **catastrophic** |

## Findings

1. **border-first wins** at +12 matched edges over row-major in 30s.
   Same algorithm, just visits all 56 perimeter cells first (where
   the domain is small due to border-matches-border constraint) before
   any interior cell. This shrinks the average domain of interior
   cells at the time they're visited (one less neighbour to constrain).

2. **hint-link refutes the user's hypothesis at the raw-DFS level**.
   Centre-out from hints creates an early high-domain wall: 866M
   placements in 30s all under depth 48. This matches vol-14's
   "hint-centric scan order NULL" finding (depth 42 / 62 matched
   vs border-first MRV's 164 / 282) from the engine-with-propagators
   experiment. Both confirm: **starting at the interior is worse
   than starting at the border**, regardless of propagator presence.

3. **Throughput tradeoff**: pre-bucketing brings vanilla_path from
   1.5M pp/s (per-candidate filter loop) to 63-107M pp/s (bucket
   slice lookup), but still 30-50% below vanilla_fast's 124M pp/s
   row-major. The bucket-size overhead from mask-aware keying is
   the gap; mask=15 cells (k=4 constraints) have 280k bucket slots,
   the loading of which is non-trivial.

4. **Pure-DFS depth ceiling**: row-major at single-thread 30s
   reaches depth 210 / 433 score. vanilla_fast at 5min/8 threads
   reaches depth ~210-240 / ~440 score. The depth-along-path metric
   is the same axis; the gain from border-first might compound
   under longer/multi-thread runs.

## Next step

5min × 8 threads × `border-first` with `--pin-hints`, then ALNS-5min
lottery. Compare:
- Best vs vol-32 vanilla_fast 5min partial (~score 440 best).
- Post-ALNS lottery score distribution vs vol-32 vanilla_fast →
  ALNS (which produced the 458 RECORD).

## Concepts touched

- [[hint-centric]] (vol-14) — refuted again, in a different setting.
- new concept: **`path-aware-vanilla`** — the bucket structure
  generalises vanilla_fast's row-major bucket to arbitrary paths.

## Open

- Does border-first → ALNS exceed 458? **Awaits 5min run + lottery.**
- Are there even-better paths? Row-major-bottom-up, spiral-out,
  layered-rectangle-from-vol-14 paths could be tested cheaply.
- Should `border-first` become the new vanilla_fast default? Maybe;
  +12 edges at 30s is real, but multi-thread effects may differ.
