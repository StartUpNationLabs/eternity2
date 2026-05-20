---
name: mcgavin-top3-mip-proven
description: McGavin's top-3 rows (48 cells, rows 0-2) PROVEN MIP-optimal. Gap 0% after 70s HiGHS. Extends vol-83's halo-1 proof to a meaningfully larger region — strongest local-optimality result yet on canonical E2.
metadata:
  type: project
status: built
---

# McGavin top-3-rows — MIP-OPTIMAL (vol-85)

**Status**: `built` — PROVEN 2026-05-16 00:46.
**Tool**: `repair_region` (cluster_repair backend, HiGHS solver).
**Time**: 70.37s, gap 0% (proven optimal).
**Files**: `output/vol-85-top3-mip/mcgavin_top3.log`.

## Result

McGavin's 469 with cluster = rows 0-2 (top 3 rows, 48 cells).

- MIP size: 10,926 binary vars, 3,500 rows, 48,171 nonzeros.
- Initial score: 469.
- MIP-optimal score: 469. **delta = +0**.
- Objective value: 89 (matches current top-3 contribution to score).
- **Gap: 0%** at termination — provably optimal.
- HiGHS time: 70.37s (well under 600s budget).

## Strategic significance

This is a stronger statement than vol-83's halo-1 (37 cells).
Vol-85 covers the ENTIRE top 3 rows = 48 cells, which contains:
- All cells incident to McGavin's mismatched edges in rows 0-2.
- Plus all cells in those rows that are NOT incident to mismatches.

So vol-85 proves: **McGavin's top-3 rows cannot be rearranged to
ANY better configuration under the constraint that rows 3-15 stay
fixed.** This includes moves that:
- Swap pieces between mismatched and non-mismatched cells.
- Rotate pieces freely.
- Permute pieces within the 48-cell region.

## What vol-85 does NOT prove

- McGavin's top-5 might still be improvable (vol-84 inconclusive,
  600s timeout at 1745% gap).
- A larger halo or different region MIGHT yield improvement.
- Cross-row swaps between rows 0-2 and rows 3-15 MIGHT help.

## Chained proofs on McGavin

Combining vol-83 + vol-85:
1. **Halo-1 around mismatches** (37 cells, vol-83): delta=+0
   PROVEN in 895s.
2. **Top-3 rows** (48 cells, vol-85): delta=+0 PROVEN in 70s.
3. **Top-5 rows** (80 cells, vol-84): "no improvement found" in
   600s but gap 1745% — NOT proven.

## Mathematical conclusion

McGavin's 469 is **rigidly locally optimal** in a region of at
least 48 cells (top 3 rows) and additionally in the 37-cell
halo-1 around all 16 defect cells.

To break 469 requires either:
- Cross-row swap involving cells outside both the 37-cell and
  48-cell regions (i.e., cells in rows 3-15 that vol-85 didn't
  cover but that could feed into a top-5 improvement).
- Larger MIP (vol-84 hit limit; top-3 + halo-1 around bottom
  mismatches could be tried).
- Board-spanning σ-cycle move (per
  [[vol-65-oracle-sigma-indecomposable]] memory).

## Linked

- [[mcgavin-mip-local-optimal-halo1]] (vol-83 parent)
- [[mcgavin-top5-mip-inconclusive]] (vol-84 sibling)
- [[mcgavin-469-mismatch-geometry]]
- [[mcgavin-basin-top-bottom-symmetry]]
