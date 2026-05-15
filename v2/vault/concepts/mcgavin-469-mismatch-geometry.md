---
name: mcgavin-469-mismatch-geometry
description: McGavin's 469 has all 11 mismatches concentrated in rows 0-4 (top 5 rows). Rows 5-15 are locally perfect. Implies basin is top-determining and explains why top-N pinning works at smaller N than bottom-N pinning would.
metadata:
  type: project
---

# McGavin 469 — mismatch geometry (top-concentrated)

**Status**: `built` — derived 2026-05-16 00:25.
**Origin**: vol-82 motivation analysis on McGavin 469 reference board.
**Files**: `output/vol-65/mcgavin_469.json`.

## Result

McGavin's 469 has exactly 11 unmatched edges. ALL 11 are in rows
0-4 (top 5 rows). Rows 5-15 are LOCALLY PERFECT.

### Detailed mismatch list

Horizontal-edge mismatches (between (r,c) and (r,c+1)):
- (2,7)-(2,8)
- (3,6)-(3,7)
- (3,7)-(3,8)
- (4,10)-(4,11)
- (4,11)-(4,12)
- (4,13)-(4,14)

Vertical-edge mismatches (between (r,c) and (r+1,c)):
- (0,9)-(1,9)
- (1,9)-(2,9)
- (2,14)-(3,14)
- (3,10)-(4,10)
- (3,14)-(4,14)

### Distribution by row (weighted, V-edges count to upper row)

| row | mismatch count |
|----:|---------------:|
| 0   | 1              |
| 1   | 1.5            |
| 2   | 2.5            |
| 3   | 4.5            |
| 4   | 4.0            |
| 5-15| **0**          |

## What this implies

1. **McGavin's basin is top-asymmetric.** The hard region is the
   top 5 rows; the bottom 11 rows are well-solved.

2. **Mismatch concentration in a band** (rows 0-4) suggests
   Blackwood's algorithm "ran out of break-index budget" near the
   top of the board during its scan. The schedule places mismatches
   at specific cell indices; for McGavin's board these indices map
   to top-band cells under the scan order used.

3. **Vol-68 top-N=14 threshold makes sense.** Pinning McGavin's
   top 14 rows (rows 0..13 = 224 pieces) keeps the HARD region's
   solution intact. The unpinned rows 14-15 (32 pieces) are in the
   locally-perfect region and ALNS can fill them trivially.

4. **Bottom-N=14 prediction.** Pinning McGavin's bottom 14 rows
   (rows 2-15 = 224 pieces) keeps the EASY region pinned and frees
   the HARD region (rows 0-1 plus some of row 2) for ALNS. Our
   ALNS lacks Blackwood's break-index machinery, so reconstructing
   the hard top band is unlikely to produce 469-quality. Predict
   score in the 455-465 range, NOT 469.

5. **Vol-65 cross-record geometry corroborates.** Per memory
   `project_e2_vol14_mismatch_geometry_universal.md`: community
   469/468 boards have hard regions at TOP, our 443/454 boards
   have hard regions at BOTTOM. McGavin (top-concentrated) is
   consistent with the community pattern. **Scan-order dependent:
   community used a TOP-DOWN scan that exhausted break-budget
   bottom-first leaving top-mismatches; our top-down stack has
   the opposite outcome.**

6. **Border ring is perfect in McGavin.** All 60 border-ring edges
   match (positions 0-15, 240-255, and column 0/15 verticals).
   The 11 mismatches are all interior-interior.

## What might invalidate this geometry analysis

- The mismatch count of 11 matches the puzzle convention (matched
  + mismatches + border-mismatches = 480 internal edges + border
  border-edges, but border-color matches are not in the 480).
- Independently confirmed by `rescore_board` on
  `output/vol-65/mcgavin_469.json` reporting 469/480.

## Connection to break-index schedule

Blackwood's calibrated_v17a schedule has break indexes at
{201, 206, 211, 216, 221, 225, 229, 233, 237, 239, 241, 255}.
These are cell indices in scan order.

If the scan is row-major top-down, cell 201 is row 12 col 9, cell
255 is row 15 col 15. Breaks are concentrated at the BOTTOM under
top-down scan. Yet McGavin's mismatches are at the TOP. This is
because Blackwood/McGavin used a DIFFERENT scan order (likely
bottom-up or border-first).

**Insight**: confirming McGavin used a non-trivial scan order is
implicit in the geometry. Vol-65 notes mention this explicitly.

## Linked

- [[mcgavin-469-basin]]
- [[mcgavin-basin-top-bottom-symmetry]] (vol-82 hypothesis)
- [[mismatch-geometry-universal]] (vol-14)
- Memory: `project_e2_vol14_mismatch_geometry_universal.md`
- Memory: `project_e2_vol68_n_row_scaling.md`
