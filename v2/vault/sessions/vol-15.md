# Session — vol-15

**Theme**: Blackwood algorithm shipped. Cliff bug fixed. BLACKWOOD_RAW 47× speedup. Schedule-wall structural.
**Raw**: [[../sessions/archive/raw/RESEARCH_NOTES_15|RESEARCH_NOTES_15.md]], [[../sessions/archive/raw/RESEARCH_NOTES_15_PLAN|RESEARCH_NOTES_15_PLAN.md]], [[../sessions/archive/raw/V15_BLACKWOOD_SPEC|V15_BLACKWOOD_SPEC.md]]

## What was attempted

- Implement [[blackwood-algorithm]] per spec: `BlackwoodSchedule`, `ScanOrder::RowMajorBottomUp`, `ValueOrder::BlackwoodHeuristic`, break-index allowance in DFS.
- Cliff-fix: affine remap of post-border schedule.
- `BLACKWOOD_RAW` profile: drop AC-3/gacolor/NS-1 (unsound under breaks).
- Composition with RectangleDestroy + LayeredDestroy.
- 2h pilot of `blackwood_raw_layered`.
- 12×12 testbed sanity check (`run_blackwood_12x12`).

## What was measured / kept

- **[[blackwood-algorithm]] ported**: full break-index DFS + heuristic-color schedule.
- **Cliff bug**: raw 469 schedule has discontinuity at border-to-interior boundary; affine remap fixes it.
- **[[engine-profile-registry|BLACKWOOD_RAW]]**: 47× single-thread speedup (~80k → ~367k nps post-vol-16 cleanup) by dropping AC-3/gacolor/NS-1 which are **unsound under break allowance**.
- Vol-15 best cold-start: **416/480** (BLACKWOOD_RAW, depth 87).
- **[[blackwood-layered-depth-wall]]**: 2h pilot of `blackwood_raw_layered` shows depth-80 wall is **structural, not time-bound** (identical 382/480 across 5min and 2h).

## What was refuted

- **Blackwood standalone lift** (raw 469 spec on our stack): below baseline 439/480 (best 416/480).
- **Propagator soundness under breaks**: AC-3, gacolor, NS-1 incompatible. Must be off.
- **Time-budget as constraint**: schedule wall structural, doubling wall-clock zero progress.
- **Rectangle / Layered composition with Blackwood**: refuted; layered ordering conflicts with schedule.

## Concepts touched

- [[blackwood-algorithm]] (introduced, calibrated vol-17)
- [[blackwood-layered-depth-wall]] (introduced + refuted)
- [[engine-profile-registry]] (BLACKWOOD_RAW added)
- [[bitset-domain-rep]] (vol-16 cleanup pre-staged here)

## Tier-1 outcome

Vol-15 Tier 1 (≥454) **NOT MET**. Best cold-start 416/480 < baseline 439/480. The Blackwood raw schedule does not transfer to our stack without calibration. → vol-17 calibration unblocks Tier 1.

## Insight

The published 469 schedule was tight for **Blackwood's piece set + throughput**, not ours. Schedule parameters must be calibrated empirically. Vol-17 builds `calibrate_blackwood` to derive `v17a/b/c` schedules from community 469 boards.

## Linked memory

- `project_e2_vol15_blackwood_results`
- `project_e2_blackwood_layered_depth_wall`
- `project_e2_mcgavin_blackwood_gap_analysis`
