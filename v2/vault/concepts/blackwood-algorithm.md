---
tags: [concept, algorithm, community-port]
status: built-partial
origin-vol: 14
ported-vol: 15
---

# Blackwood algorithm (heuristic-schedule + break-index backtracker)

**Status**: `built` (vol-15, calibrated v17a/b/c in vol-17)
**Origin**: spec in vol-14 ([[V15_BLACKWOOD_SPEC]]), implementation vol-15
**Files**: `crates/solver-engine/src/lib.rs` (BlackwoodSchedule, ScanOrder, value-order BlackwoodHeuristic, break allowance), `crates/bench-audit/src/bin/run_e2_blackwood.rs`, `crates/bench-audit/src/bin/calibrate_blackwood.rs`

## Definition

A row-major backtracker with two extra ingredients beyond standard CP:

1. **Heuristic-side schedule**: pre-pick 3 edge colors covering ~120 piece-edge occurrences. Enforce a piecewise-linear schedule of how many heuristic-piece-occurrences must be exhausted by each depth. Branches that fall behind are pruned.
2. **Break-index allowance**: at a fixed list of depths (e.g. `[201, 206, 211, …, 256]`), allow ≤1 edge mismatch instead of requiring exact matching.

With 12 breaks, the maximum-feasible score is `480 − (12−1) = 469`. The algorithm is **deliberately permissive about the last few mismatches** to make 469 reachable in billions of iterations.

## 469 parameter set (Blackwood 2020-11, verbatim)

```
heuristic_sides       = [17, 2, 18]          # 3 specific edge colors (Blackwood's labelling)
break_indexes_allowed = [201, 206, 211, 216, 221, 225, 229, 233, 237, 239, 241, 256]
heuristic_schedule    = piecewise-linear:
   depth 0   → 0   of 122 occurrences
   depth 16  → 0
   depth 26  → 28
   depth 56  → 71
   depth 76  → 89
   depth 102 → 106
   depth 160 → 119  of 122
max_heuristic_index   = 160
iteration_cap         = 50_000_000_000
```

## Heuristic-color selection rules (Blackwood)

1. **Many occurrences** (~120 across 256 pieces).
2. **Not used on any of 4 corners** (preserves corner flexibility).
3. **Not used on the start piece** (preserves start flexibility).

For canonical E2 (Monckton 5-clue), our σ-bijection maps Blackwood's `[17, 2, 18]` into our color labelling (see [[reference-blackwood-decoded]]).

## What we shipped

- vol-15: `BlackwoodSchedule` struct, `ScanOrder::RowMajorBottomUp`, `ValueOrder::BlackwoodHeuristic`, break allowance hook in DFS recursion.
- vol-15: `BLACKWOOD_RAW` profile — Blackwood + drop AC-3/gacolor/NS-1 (these propagators are **unsound under break allowance**: they assume exact matching). 47× single-thread speedup (~80k → ~367k nps after vol-16 cleanup).
- vol-15 cliff-fix: post-border affine remap of the schedule (raw spec had a discontinuity at the border-to-interior boundary).
- vol-17: schedules `calibrated_v17a`, `v17b`, `v17c` derived empirically from community 469 boards (see [[blackwood-schedule-calibration]]).

## Empirical results on canonical E2

| Config | Wall | Depth | Score | Note |
|---|---:|---:|---:|---|
| baseline `joe_depth150_bp_par` | 5min | 174 | 439/480 | reference, no Blackwood |
| Blackwood orig (cliff bug) | 5min | 56 | 395/480 | schedule wall, raw spec |
| Blackwood (cliff fix) | 5min | 80 | 405/480 | |
| `BLACKWOOD_RAW` | 5min | 87 | 416/480 | best vol-15 cold-start |
| `calibrated_v17a` (seed-1) | 5min | — | 447/480 | vol-17 |
| `calibrated_v17b` (seed-1) | 5min | — | 448/480 | vol-17 |
| `BLACKWOOD_RAW` + `layered` rectangle | 2h | 80 wall | 382/480 | depth-80 wall structural ([[blackwood-layered-depth-wall]]) |
| v17a + WorstBand + ConflictDriven{80} ALNS | — | — | **455/480** | vol-17 best cold-start |

## What it doesn't fix

- **Throughput gap**: McGavin's C backtracker at 295M nps gets to 469 in days on ~200 cores. Our best is ~367k nps single-thread (still ~800× slower). 40 days wall-clock on canonical 5-clue at this throughput.
- **Schedule-as-time-budget gap**: 2h pilot of `blackwood_raw_layered` showed identical 382/480 to 5-min run. Doubling wall-clock doesn't move the wall. The schedule wall is structural, not budget-bound (see [[blackwood-layered-depth-wall]]).
- **Propagator soundness under breaks**: AC-3 and gacolor remove rotations that would induce a mismatch the break allowance might license. They are **off by default** under Blackwood.

## Pipeline use

The natural composition is [[blackwood-then-csp]] (Variant K): run Blackwood to depth ~85 as a SEED GENERATOR, convert to canonical hints, run standard CP+ALNS to fill the rest. Vol-17 trialed this; full evaluation deferred.

## Linked concepts

- [[blackwood-schedule-calibration]] — deriving schedule parameters from community boards
- [[prune-restart]] — Joe's complementary restart policy, [[mcgavin-blackwood-gap-analysis]]
- [[mcgavin-engine]] — throughput target
- [[reference-blackwood-decoded]] — σ-bijection from Blackwood's color labels to ours
- [[alns]] — what runs after Blackwood seeds the prefix

## Linked memory

- `project_e2_vol15_blackwood_results`
- `project_e2_mcgavin_blackwood_gap_analysis`
- `project_e2_blackwood_layered_depth_wall`
- `reference_blackwood_decoded`
