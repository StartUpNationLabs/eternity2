---
tags: [concept, refuted, blackwood]
status: refuted
origin-vol: 15
---

# Blackwood-layered depth-wall

**Status**: `refuted` (vol-15 1h+1h pilot)
**Origin**: vol-15
**Files**: `crates/bench-audit/src/bin/run_e2_blackwood.rs` with `--ordering layered`

## Hypothesis

`blackwood_raw_rect_layered` = [[blackwood-algorithm]] + RectangleDestroy pre-commit + LayeredDestroy ordering (concentric rings inward). The layered ordering was conjectured to encode the schedule-as-failure-mode that vol-14's hint-rectangle finding pointed at.

## Refutation

1h pilot on canonical E2:
- 3.4 G nodes.
- Depth = **80 wall** (was 80 at 5 min, +1 at 1 h).
- Doubling wall-clock from 5min to 1h: zero progress past the wall.

2h pilot: identical 382/480 to 5min, confirming the wall is **structural, not time-budget**.

## Verdict

Layered + Blackwood is fundamentally wrong. The layered ordering enforces a constraint pattern that conflicts with Blackwood's heuristic schedule. **Do NOT retry with bigger budget.** Clean null.

## What replaced it

[[blackwood-schedule-calibration]] (vol-17) — instead of imposing an external structural ordering, calibrate the existing schedule to match our engine's actual throughput and break statistics from community 469 boards.

## Linked concepts

- [[blackwood-algorithm]] — what this tried to extend
- [[blackwood-schedule-calibration]] — the successful vol-17 successor

## Linked memory

- `project_e2_blackwood_layered_depth_wall`
