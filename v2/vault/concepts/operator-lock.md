# Operator-lock (K≤5)

**Status**: `built` (vol-20), measurement established
**Origin**: vol-20
**Files**: `crates/bench-audit/src/bin/cycle_scan.rs`

## Definition

A board B is K-operator-locked if no move of cardinality ≤ K (rotations, transpositions, K-cycles) strictly improves the score.

## Vol-20 measurements on our 457

| Move family | Count | Improvers |
|---|---:|---:|
| Single rotation flip | 1024 | 0 |
| Single piece swap | full board | 0 |
| Adjacent-pair rotation | 6720 | 0 |
| Non-adjacent transposition | 20240 | 0 |
| 3-cycle on 38 mismatch cells | 32796 | 0 |
| 4-cycle on 38 mismatch cells | 982200 | 0 |
| 5-cycle on 38 mismatch cells | 28480440 | 0 |
| 38-cell perm BB (60s) | ~456k nodes | 0 |
| 82-cell halo-r1 BB (90s) | ~122k nodes | 0 |

All 11 saved PT-457 boards are byte-identical (one basin, found 11 times).

## What's strictly stronger

The vol-21 [[relaxed-bound]] gap test. Gap = 0 implies operator-locked at any K; gap > 0 doesn't say anything about local K because the relaxation differs.

## How to escape

- [[basin-escape-recipe]] — works, but ALNS-saturation gap holds in new basins
- [[prune-restart]] — unbuilt; expected to navigate locked regions globally
