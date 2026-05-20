---
name: 459-skeleton-and-variability
description: "Vol-111 follow-up. Analysed cell-level variability across 4 distinct 459 basins. Finding: 3 cells are invariant (top-left, top-right corners + position 31 = end of row 1 = border ring). 212 cells have 2 distinct placements (most pieces have a 'swap pair'). 24 cells are FULLY VARIABLE across all 4 basins — concentrated in rows 13-15 (9, 10, 5 cells respectively). The 459-level set's structural diversity is concentrated at the BOTTOM of the board, matching the project_e2_vol68 memory that 'rows 12-15 are 3× more diverse'."
metadata:
  type: project
status: built
---

# 459-basin skeleton and variability geometry (vol-111)

**Status**: `built` 2026-05-16 ~14:15.
**Origin**: vol-111 follow-up to the 4-basin 459 corpus.

## Cell-level variability across 4 459 basins

Counted distinct (piece_id, rotation) per cell across all 4 basins
(vol-60, pipeline-orig, pipeline-bseed1, pipeline-bseed6):

| distinct placements | cells |
|--------------------:|------:|
|                   1 |     3 |
|                   2 |   212 |
|                   3 |    17 |
|                   4 |    24 |

**Invariant cells** (3 total, identical in all 4 basins):
- Position 0 = (x=0, y=0) — top-left CORNER.
- Position 15 = (x=15, y=0) — top-right CORNER.
- Position 31 = (x=15, y=1) — end of row 1.

These are all border-ring positions. The corner pieces' rotations
are uniquely determined by their border constraints; the canonical
hints likely fix specific pieces there.

**Fully-variable cells** (24, different in all 4 basins):
Concentrated in rows 13-15:
- Row 13: 9 cells.
- Row 14: 10 cells.
- Row 15: 5 cells.
- Rows 0-12: 0 fully-variable cells.

The basin diversity is concentrated at the BOTTOM. This matches
the [[project_e2_vol68_n_row_pinning]] memory which found "rows
12-15 are 3× more diverse per row" in arrangements.

## Piece-level skeleton

Counted distinct (position, rotation) per piece_id across the 4
basins:

| distinct placements | pieces |
|--------------------:|-------:|
|                   1 |      3 |  ← fully invariant
|                   2 |    212 |  ← 2-position "swap pair"
|                   3 |     17 |
|                   4 |     41 |

The 41 most-variable pieces (4 distinct (pos, rot) tuples) are the
ones that genuinely differ between basins. The 212 swap-pair pieces
are "skeleton" — they live in one of TWO positions across all
basins. Inferring: the basins differ by "exchanging" swap-pair
pieces in coordinated ways.

## 89-cell σ-cycle to McGavin: per-row distribution

For comparison: the 89-cell σ-cycle from pipeline-orig 459 to
McGavin 469 has roughly uniform per-row distribution (4-9 cells
across rows 1-14), NOT concentrated at the bottom. So McGavin's
transition mass is BROADER than the 459-basin variability.

This means: navigating between 459 basins (bottom-3-rows shuffle)
is structurally easier than reaching McGavin 469 (whole-interior
shuffle).

## What this means

1. **Skeleton-based search**: a search algorithm could PIN the
   3 invariant cells + use the swap-pair structure for the 212
   pieces, freeing only the 24 fully-variable cells + 17 partial.
   That's a 41-cell sub-problem instead of 256.
2. **Bottom-rows MIP focus**: an MIP on rows 13-15 (48 cells) with
   the top 13 rows fixed (after picking a basin) could find new
   bottom-rows arrangements giving 459 or higher. The vol-105 T2.a
   work attempted this and found a 121.14 LP-UB (gap 17.6%) but
   was killed at user redirect. Worth re-running with a clean
   formulation.
3. **Path A reformulation**: subset σ-cycle CP should focus on
   the bottom-3-rows σ-cycles. They're more navigable than the
   full board-spanning cycle.

## Vol-112 candidates updated

- **#1 (Path A CP)**: focus on bottom-3-rows σ-cycle subsets.
- **#5 (bottom-rows MIP)**: revive vol-105 T2.a with bound-ascent
  preconditioning from the pipeline-orig basin (closer to McGavin).

## Linked

- [[multiple-459-basins-rigid]] — the 4-basin corpus.
- [[sigma-cycle-predicts-alns]] — σ-cycle structure analysis.
- [[MATH_NOTES_2026-05-16_459_LEVEL_SET]] — theoretical framing.
