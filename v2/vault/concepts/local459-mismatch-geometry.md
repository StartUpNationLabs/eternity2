---
name: local459-mismatch-geometry
description: Our local 459 has all 21 mismatches in rows 11-15 (BOTTOM 5 rows) — exact mirror of McGavin's 469 (TOP 5 rows). Confirms vol-14 "scan-order determined" finding empirically.
metadata:
  type: project
status: built
---

# Local 459 — mismatch geometry (bottom-concentrated)

**Status**: `built` — derived 2026-05-16 00:54.
**Origin**: vol-87 motivation analysis on our highest-scoring local record.
**Files**: `output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json`.

## Result

Our local 459 has exactly 21 unmatched edges. ALL 21 are in rows
11-15 (BOTTOM 5 rows). Rows 0-10 are LOCALLY PERFECT.

### Distribution by row (weighted)

| row | mismatch count |
|----:|---------------:|
| 0-10 | **0**         |
| 11  | 1.5            |
| 12  | 8.0            |
| 13  | 5.0            |
| 14  | 5.5            |
| 15  | 1.0            |

## The mirror finding

**This is a perfect MIRROR of McGavin's 469 geometry** (see
[[mcgavin-469-mismatch-geometry]]):

| board | mismatch concentration | scan direction |
|---|---|---|
| McGavin 469 | rows 0-4 (top 5) | bottom-up or border-first |
| Local 459 | rows 11-15 (bottom 5) | top-down (our vanilla_path) |

Combined with vol-14 memory `project_e2_vol14_mismatch_geometry_universal`:
"scan-order determined — top-down scan exhausts break-budget
bottom-first leaving top-mismatches; bottom-up scan does opposite."

McGavin used a non-default scan order (likely bottom-up or
border-first); our pipeline uses top-down row-major. Both are
local-optima of their respective scan orders. **Neither basin
is intrinsically better** — they're scan-order-dual.

## Implication for breaking records

Our local 459 has 21 mismatches in the BOTTOM. To improve beyond
459, the analogue of "solve the top-5-rows for McGavin" is **solve
the bottom-5-rows for our 459**. Tested by vol-87 (bottom-3 MIP
on our 459).

This is a **PARALLEL CONSTRAINT** to McGavin: each record's basin
is rigid in its mismatch-concentrated region. The asymmetry of
McGavin (top-determining) corresponds to scan-order asymmetry of
HIS algorithm, not the puzzle.

## Asymmetric difficulty?

11 mismatches (McGavin) < 21 mismatches (ours). McGavin's basin
ISN'T just "another local optimum at a different score" — it's
genuinely 10 fewer mismatches in the same 5-row band. McGavin's
algorithm (or scan order, or both) produces tighter packing in
the hard region.

## Linked

- [[mcgavin-469-mismatch-geometry]] (the mirror image)
- [[mcgavin-basin-top-bottom-symmetry]]
- Memory: `project_e2_vol14_mismatch_geometry_universal.md`
- Memory: `project_e2_vol17_447_top_mismatch.md` (calibrated_v17a 447 — top mismatches per top-down + Blackwood)
