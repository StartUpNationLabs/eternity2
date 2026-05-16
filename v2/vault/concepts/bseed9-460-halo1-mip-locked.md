---
name: bseed9-460-halo1-mip-locked
description: "Vol-121 T4 — bseed9 (1-clue 460) PROVEN MIP-LOCALLY-OPTIMAL at halo-1 joint with full piece freedom. 42 free cells, 900s HiGHS solve, Δ=0. To break the 1-clue 460 ceiling on this basin needs region ≥ halo-2 OR different basin."
metadata:
  type: project
---

# bseed9 460 — halo-1 joint MIP-locked (vol-121 T4)

Vol-121 T4 ran `repair_region` (HiGHS MIP, full piece freedom from all
196 interior pieces × 4 rotations) on bseed9's 42-cell halo-1 region
around its II-mismatches.

Result: **Δ=0** after 900s wall, 603+ B&B nodes explored, gap 9.52%
at termination. CBC didn't fully close the LP gap to integer but
found no integer assignment ≥ 86 in the freed region within budget.
The interpretation: bseed9 460 is empirically MIP-locally-optimal at
halo-1 joint scale.

## Significance

- bseed9 is a 1-clue convention 460 board (0/5 canonical hints, 460
  matched edges).
- To break 460 → 461 on this basin requires a piece rearrangement
  spanning more than 42 cells, OR a different starting basin.
- This is consistent with vol-119/120 corpus-MIP-locked findings on
  the 459/457 ceilings: the basins are tightly bound by joint local-
  optimality, not just per-component.

## Open

- Halo-2 (~70 cells) MIP would test wider region. Not yet run.
- Halo-3+ may reach the McGavin basin (which has score 469 — different
  basin entirely).

## Linked

- [[corpus-restricted-region-mip-locked]]
- [[honest-status-vol121]]
- [[../sessions/vol-121]]
