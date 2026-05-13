---
tags: [concept, calibration, blackwood]
status: built
origin-vol: 17
---

# Blackwood schedule calibration (from community 469 corpus)

**Status**: `built` (vol-17)
**Origin**: vol-17 (Tier-1 unblock)
**Files**: `crates/bench-audit/src/bin/calibrate_blackwood.rs` (469 LoC), schedule variants `calibrated_v17a`, `v17b`, `v17c`

## Why calibration was needed

Vol-15's port of Blackwood's exact 469 parameter set (heuristic_sides `[17, 2, 18]`, breaks `[201, …, 256]`) **didn't transfer well** to our stack:
- 5min run: depth 80, score 405/480 (with cliff-fix) — worse than baseline 439/480.
- 2h pilot of `blackwood_raw_layered`: 382/480 (schedule wall structural, not budget-bound).

Vol-17's insight (post hoc): the published 469 schedule was derived from a **different piece set / engine throughput** than ours. The schedule must be **calibrated empirically** for our specific engine + propagator stack.

## What `calibrate_blackwood` does

Reads community 469-class boards from `output/community_corpus/`. For each board, simulates row-major bottom-up scan and measures:
- How many heuristic-color edges are placed by each depth.
- Which depths first allow a mismatch (the natural break points).

Outputs a schedule whose `heuristic_array` and `break_indexes` match the corpus statistics.

## v17a / v17b / v17c variants

- **v17a**: median of community-469-class boards (most conservative).
- **v17b**: 25th-percentile (more permissive; allows breaks earlier).
- **v17c**: empirical envelope (loosest).

The schedule is calibrated to require **2.8× fewer** heuristic-color edges at depth 120 than the raw Blackwood spec → self-pruning at our throughput.

## Empirical results

| Config | Wall | Score (cold) |
|---|---:|---:|
| Baseline `joe_depth150_bp_par` | 5min | 439/480 |
| `BLACKWOOD_RAW` (raw 469 spec) | 5min | 416/480 |
| `calibrated_v17a` | 5min | 447/480 |
| `calibrated_v17b` | 5min | 448/480 |
| v17a + WorstBand + ConflictDriven{80} ALNS | — | **455/480** (best vol-17 cold) |

## Vol-17 overnight portfolio finding

21 chunks × 10+10min CP+ALNS:
- **v17b outperforms v17a by +4.3 matches mean** (F4).
- v17c/v17e never ran (portfolio trapped in v17a basin).
- Best overnight: 453/480 (chunk 19, v17b, H22=0 tie-shuffle).

→ The schedule axis still has signal; v17c/v17e are worth running separately.

## Insight

The Blackwood schedule on community 469 boards demands **2.8× more** heuristic edges placed at depth 120 than our engine actually achieves on canonical 5-clue E2 → branches self-prune. The published 469 schedule was tight for Blackwood's throughput and unframed-variant piece set. Tightness must scale to engine + variant.

## Linked concepts

- [[blackwood-algorithm]] — the algorithm being calibrated
- [[engine-profile-registry]] — where the calibrated profiles live
- [[blackwood-layered-depth-wall]] — null result that motivated calibration

## Linked memory

- `project_e2_vol17_session_summary`
