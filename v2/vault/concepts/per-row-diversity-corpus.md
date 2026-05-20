---
name: per-row-diversity-corpus
description: Across 421 complete high-score boards, rows 12-15 have ~3× more distinct piece arrangements (131-132 each) than rows 0-11 (49-63). Quantifies basin diversity at the bottom of the board.
metadata:
  type: project
status: built
---

# Per-row diversity across 421-board corpus (vol-99 finding)

**Status**: `built` — measured 2026-05-16 ~06:25.

## Result

For each row r ∈ 0..15, counted distinct (16-tuple of piece-ids)
across 421 complete boards with score ≥ 455:

| row | distinct arrangements | fraction unique |
|----:|----------------------:|----------------:|
|  0  |  49 | 11.6% |
|  1  |  49 | 11.6% |
|  2  |  49 | 11.6% |
|  3  |  50 | 11.9% |
|  4  |  39 |  9.3% |
|  5  |  44 | 10.5% |
|  6  |  47 | 11.2% |
|  7  |  47 | 11.2% |
|  8  |  48 | 11.4% |
|  9  |  47 | 11.2% |
| 10  |  48 | 11.4% |
| 11  |  63 | 15.0% |
| 12  | **131** | **31.1%** |
| 13  | **132** | **31.4%** |
| 14  | **132** | **31.4%** |
| 15  | **132** | **31.4%** |

## Interpretation

Rows 0-11 have 39-63 distinct arrangements each (~10-15% of
boards have unique row-r arrangements). Rows 12-15 have 131-132
each (~31% — about 3× higher diversity).

Combined with [[universal-mismatch-heatmap]] (rows 11-13 fail
most often) and [[universal-match-backbone]] (rows 4-10 are
backbone): the **bottom of the board (rows 12-15) is where our
pipeline's basins maximally diverge.**

## Why?

Our top-down ALNS pipeline:
- Border ring (rows 0+15+col 0+15) is forced into fixed
  perm-class arrangements (~49 distinct rows 0).
- Rows 4-10 form the "structural backbone" (constrained by
  middle propagation).
- Rows 11-15 are filled LAST, with the most accumulated
  constraint propagation eaten up at row 12 (universal hard band).
- ALNS divergence concentrates in the last-filled rows.

McGavin's algorithm (different scan order) would show the
inverse pattern (top-row diversity).

## Implication for record-breaking

If row 12-15 arrangements are 3× more diverse, then **the
algorithm that explores DIFFERENT row-12-15 piece-sets has access
to 3× more basins**. Concrete approaches:
1. ALNS variant that destroys ONLY rows 12-15 (preserving rows
   0-11 as basin-defining structure)
2. CP-MaxScore restricted to rows 12-15 piece-permutations
3. MIP on rows 12-15 only (256 piece-ids × 64 cells = 16k binary
   vars, smaller than vol-86 top-4 MIP)

Bottom-3 rows MIP on local 459 (vol-87) was inconclusive at 600s
but with the 3× diversity finding, a longer run with more diverse
seeds might find a 460+.

## Linked

- [[universal-mismatch-heatmap]]
- [[universal-match-backbone]]
- [[local459-mismatch-geometry]]
- [[basin-corner-permutations]]
