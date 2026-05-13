---
tags: [concept, gap-analysis, key-finding]
status: documented
origin-vol: 14
---

# McGavin-Blackwood gap analysis

**Status**: `built` analysis (vol-14)
**Origin**: vol-14 reverse-engineering of community 469 algorithm
**Files**: docs analysis; memory `project_e2_mcgavin_blackwood_gap_analysis`

## Four orthogonal gaps to 469

Vol-14 reverse-engineered the community 469 record from `docs/community-mining/09_Blackwood_solver_thread.md` + `05_Joe_pruning_method_thread.md`. Our stack is missing **four independent mechanisms**:

| # | Mechanism | McGavin / Blackwood | Our stack | Gap |
|--:|---|---|---|---|
| 1 | Heuristic-color schedule | YES (`[17, 2, 18]` + piecewise-linear targets) | ✗ vol-15 onward partial | algorithm gap |
| 2 | Break-index allowance | YES (12 breaks → 469 max) | ✗ vol-15 onward partial | algorithm gap |
| 3 | In-place prune-back-to-T restart | YES (Joe: N=1600 at depth > T=150 → roll back) | ✗ vol-12 shipped depth-GATE only | algorithm gap |
| 4 | Per-cell unrolled goto + 4-axis lookup | YES (295M nps single-core) | ✗ generic propagator (~367k nps post-vol-16) | engineering gap |

## Throughput math

- McGavin: 295M nps × 200 cores × a few days = reaches 50B-iteration cap where 469s emerge.
- Our stack: ~367k nps × 8 cores × ~5min ≈ 9e10 nodes/run.
- At our throughput, **~40 days wall-clock** to match a single McGavin run on canonical 5-clue.

**We cannot brute-force to 469; we need the algorithm.**

## Implication for vol-15+

The 446-454 regime is **the ceiling of "without Blackwood's algorithm"** on canonical E2 with 5-hint constraints. To break it requires gaps #1 + #2 + #3, **independent of better local search**. PT/ALNS tuning on its own cannot close the 469 gap.

## What we've shipped against the gaps

| # | Status as of vol-23 |
|--:|---|
| 1 | partial (vol-15 Blackwood port + vol-17 calibrated_v17a/b/c schedules; +8 over baseline cold) |
| 2 | partial (vol-15 break_index allowance in DFS; needs schedule co-tuning) |
| 3 | **shipped vol-23** ([[prune-restart]] driver, Round-2 lift +266 score) |
| 4 | partial (vol-12 bitset + vol-16 LUT) — still 800× slower than McGavin |

## Key Blackwood quotes

- *"arbitrary — I tried a few big numbers (over 1B) and they didn't make too much of a difference."* — Blackwood msg #22 on iteration cap.
- *"It seems we do not need to search the full search space, and can calculate the target search space based on the first 116 to 150 tiles and pruning periodically."* — Joe, Jan 2026.
- *"For the fewest number of hints to practically solve the 16x16, I would expect those few hints to be dotted around the lower half (say) of the board, perhaps at knight spacing, or in the corner of every 3x3."* — McGavin, Jan 2026. (Confirms our 5 canonical hints are intentionally well-placed for difficulty.)

## Linked concepts

- [[blackwood-algorithm]] — gaps #1 + #2
- [[prune-restart]] — gap #3 (shipped vol-23)
- [[mcgavin-engine]] — gap #4
- [[blackwood-schedule-calibration]] — partial coverage of gap #1

## Linked memory

- `project_e2_mcgavin_blackwood_gap_analysis`
- `project_e2_state`
