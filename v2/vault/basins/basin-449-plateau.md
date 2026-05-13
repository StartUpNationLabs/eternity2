---
tags: [basin, plateau-family]
status: historic
score: 449
---

# Basin 449-plateau (the original cell-CP saturation)

**Score**: 449/480 — the historic cell-CP plateau (vol-1 through vol-3)
**Discovery**: Vol-1 cell-CP with GAColor+AC-3, deterministic prefix
**Representative**: any vol-1/2/3 default-config run

## Why it matters

This is **the** classical plateau: every solver — CP, PT, ALNS, GA — converged to 449 in vols 1-3. Breaking it took **frame-first decomposition** (vol-4 → 450) and then **GA-LARGE** (vol-5 → 453) and then **border diversity + PT** (vol-6 → 454).

The plateau is the textbook example of [[prefix-determinism]]: the deterministic CP prefix is **globally infeasible to extend past 449**, but local search has no way to detect this.

## Properties

- Standard row-major scan: top-down → mismatch hotspot at center-BOTTOM (see [[mismatch-geometry]]).
- 31 mismatches, all in the universal-mismatch region (rows 10-13, cols 4-13).
- All 24×5 = 120 rare-color edges matched.
- Deterministic prefix across seeds (same border under same scan order).

## Why local search saturates

- Local CP region repair: infeasible (vol-2 proof).
- Houdayer cluster moves: zero `joint_delta` (vol-2/3).
- ALNS at K ≤ 5: hits Hamming moat (vol-5/18 [[r5f-cooperativity]]).
- GA within same border family: 452-453 ceiling (vol-5).

## Plateau-family corpus

29 plateau boards from 6 independent solver families form a coherent corpus. Vol-4/5 analysis identified the top-6 universal mismatches (47-63% prevalence).

## Why this is now historic

Post-vol-6, the team works at higher cold-start scores (439 baseline, 447 calibrated_v17a, 455 + ALNS, 457 hot-PT). The 449 plateau is the **floor** of "CP without diversification". Reaching it is automatic; going higher needs structural moves.

## Linked concepts

- [[prefix-determinism]] — the lock
- [[border-diversity]] — vol-6 break
- [[frame-first]] — vol-4 break
- [[mismatch-geometry]] — where the mismatches live

## Linked memory

- `project_e2_state` (vol-1/2/3 baseline rows)
