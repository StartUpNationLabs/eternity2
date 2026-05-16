---
name: universal-mismatch-heatmap
description: Across 1964 high-score (≥455) canonical E2 boards in our corpus, the universal mismatch heatmap shows vertical edges between rows 11/12, 12/13, 13/14 fail in 38-49% of cases. Confirms our pipeline has a "rows 11-13 universal hard band" structural feature.
metadata:
  type: project
---

# Universal mismatch heatmap — rows 11-13 (vol-99 finding)

**Status**: `built` — measured 2026-05-16 ~05:25.

## Method

Aggregated unmatched edges across all 1964 stored boards with score
≥ 455 in `output/`. Built a frequency heatmap.

## Top 20 most-mismatched edges

| edge | position | mismatch freq |
|---|---|---:|
| V (vertical, between row r and r+1) | r=12 c=2 | **49.4%** |
| V | r=12 c=4 | 47.5% |
| V | r=12 c=7 | 47.3% |
| V | r=12 c=3 | 46.3% |
| V | r=12 c=1 | 46.0% |
| V | r=12 c=6 | 45.8% |
| V | r=12 c=5 | 45.6% |
| V | r=11 c=13 | 41.4% |
| V | r=12 c=0 | 41.1% |
| V | r=11 c=14 | 40.2% |
| ... (all top-20 are in rows 11, 12, 13) | | |

Row distribution: row 11 = 8 edges, row 12 = 10, row 13 = 2.

## Interpretation

**Vertical edges between rows 11 and 12 fail in ~38-49% of all
high-score boards in our corpus.** This is the universal
"hard band" of our search pipeline.

Combined with [[mcgavin-469-mismatch-geometry]] (McGavin has
mismatches in rows 0-4, OUR boards in rows 11-15) and vol-14
memory (`project_e2_vol14_mismatch_geometry_universal`): the hard
band is SCAN-ORDER determined, not intrinsic puzzle property.

Our top-down row-major scan exhausts break-budget at the bottom
of the search, producing rows 11-13 mismatches universally.
McGavin's algorithm (different scan order) inverts this to rows 0-4.

## Significance

This is **scan-order signature data**:
- Any board with our scan-order ALNS will have mismatches
  concentrated in rows 11-15
- McGavin's algorithm has mismatches in rows 0-4
- A solver with neither scan order might land in a different
  hard zone

Future record attempts could try:
1. ALNS with row 11-12 boundary as TARGETED destroy region
2. CP-MaxScore with a higher break-budget for rows 11-13 specifically
3. Diagonal scan to break the universal pattern

## Why row 12 specifically?

Per vol-14 memory + this heatmap: row 12 is where the CP search
runs out of color "budget" under top-down scan with bottom-up-
preferred propagators. The first time the constraint set becomes
over-constrained tends to be at row 12.

## Linked

- [[local459-mismatch-geometry]] (specific local 459 example)
- [[mcgavin-469-mismatch-geometry]] (inverse for McGavin)
- Memory: `project_e2_vol14_mismatch_geometry_universal.md`
