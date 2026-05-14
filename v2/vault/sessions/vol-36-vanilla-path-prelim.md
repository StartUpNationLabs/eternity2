# Vol-36 — vanilla_path bin + prelim A/B on path modes

**Date**: 2026-05-14.
**Status**: vanilla_path bin shipped; 30s × 1-thread + 60s × 8-thread A/B
done; 5min × 8-thread border-first run in flight.

## Motivation (user-proposed)

The vol-15-32 stack has rectangle/layered path options only INSIDE the
solver-engine, which carries propagators (gacolor/AC-3) and runs at
~5-10 kpp/s. vanilla_fast at 125M pp/s is hardcoded row-major. The
user proposed a vanilla-style raw-DFS that walks a **custom path**
(default: hints connected then centre-out spiral).

Vol-14 tested rectangle/layered IN THE ENGINE and lost vs baseline
(see [[../memory-crosswalk/project_e2_vol14_rectangle_path_findings]]);
the open question was whether raw-DFS at 100M pp/s could rescue the
idea by exhausting the constrained sub-problem.

## What was built

`crates/bench-audit/src/bin/vanilla_path.rs` — new bin.

Design:
- Per-step constraint mask (which of NESW is already-placed at step d,
  determined by the path).
- Pre-bucketed candidates per step keyed by the constrained-side
  colors. Bucket count per step = `23^popcount(mask)`, max 280k at
  the rare k=4 cells.
- Hot loop mirrors vanilla_fast's: O(bucket-slice) iteration with
  early `used[pid]` check.
- Per-thread bucket-shuffle for basin diversity (same as vanilla_fast).

Path modes:
- `row-major`         — control (matches vanilla_fast's order)
- `outer-spiral`      — concentric layers from outside in
- `border-first`      — border ring, then row-major interior
- `hint-link`         — 5 hints connected by shortest paths,
                       then centre-out spiral

## A/B results (cold CP only, no ALNS)

**30s × 1 thread, no pin_hints:**

| Path mode | Max depth | Score (matched edges) |
|---|---:|---:|
| row-major | 210 | 433/480 |
| **border-first** | **215** | **445/480** ← winner |
| outer-spiral | 99 | 204/480 |
| hint-link | 48 | 51/480 |

**60s × 8 threads (multi-thread bucket-shuffle), no pin_hints:**

| Path mode | Best depth | Best score |
|---|---:|---:|
| row-major | 211 | 435/480 |
| **border-first** | **215** | **445/480** |

## Throughput

- vanilla_fast row-major (16-bit hardcoded bucket key): **124M pp/s**
- vanilla_path row-major (general bucket key): **66M pp/s** (1.9× slower)
- vanilla_path hint-link: 87M pp/s (high because most depth-50 backtracks
  return early; the search lives at depth < 50, very few placements
  reach further)
- vanilla_path outer-spiral: 107M pp/s (similar reason)

The general bucket key costs ~2× vs the hardcoded one. Acceptable
given we now have a custom-path option.

## Findings

1. **Border-first beats row-major** at cold CP (no ALNS, no propagators):
   +4 max-depth, +10 score. This is the same direction as vol-14's
   "border-first MRV" engine result but reproduced in raw-DFS form,
   confirming the effect is **search-order-driven, not
   propagator-driven**.

2. **Outer-spiral fails**: 99/480 at depth 99. The bottom row of the
   spiral is reached only after all 60 border cells AND 60+ interior
   cells, by which time the unbuilt cells have lost too many options.

3. **Hint-link fails harder**: 48/480 at depth 48. Starting at the
   geometric centre is a structural dead-end for raw DFS — same
   failure mode as vol-14's "hint-centric scan order NULL"
   (project_e2_vol14_hint_centric_null.md). Reproduces the prior
   finding from a propagator-free angle.

## Next: ALNS post-fill from border-first 5min partial

A 5min × 8-thread border-first run with --save-best is in flight.
The plan: feed the saved partial to ALNS (winning5 ops, 5min, ×N seeds)
and compare against vol-32's 458 record (which came from a vanilla_fast
row-major partial via the same ALNS path).

If border-first→ALNS produces ≥458 verified score, this is a new tool
in the cold-start pipeline. If 446-455, the +10 CP-score gain doesn't
translate (vol-23 prune-restart-style "CP gain lost in ALNS" reprise).

## What this is NOT

- Not a NEW basin-family discovery mechanism — border-first hits the
  same general row-major basin space, just with a different early
  scaffold.
- Not a path that BREAKS the canonical 5-hint constraint structure.

## Concepts touched

- [[scan-order]] — empirical confirmation that path order matters
  even without propagation
- (would-link) hint-centric-null — re-confirmed for raw DFS
- (would-link) vanilla_fast — reference implementation

## Files

- `crates/bench-audit/src/bin/vanilla_path.rs` (new)
- `output/vol-36/path_border_first/` (output dir)
- `output/vol-36/border_first_5min_best.json` (5min CP partial, in flight)
