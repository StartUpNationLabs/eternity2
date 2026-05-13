---
tags: [basin, mismatch-geometry, vol-17]
status: documented
score: 447
---

# Basin 447-top-row (calibrated_v17a)

**Score**: 447/480 — vol-17 cold-start record before WorstBand+ConflictDriven pushed to 455
**Bound** ([[relaxed-bound]]): not measured at vol-17; comparable basins gap +5 to +8
**Representative**: `calibrated_v17a` seed-1 best partial

## Discovery

Vol-17: `calibrated_v17a` Blackwood schedule on canonical E2 seed-1. First cold-start basin to have all mismatches in the TOP rows (rows 0-3).

## Geometry

All 33 mismatches form a single 51-cell connected component in **rows 0-3**. Rows 5-15 are perfect.

**Inverts vol-6 / vol-14 boards** (which have center-BOTTOM hotspots). MATCHES community 469/468 boards (which have TOP-region failures).

## Why this geometry

Calibrated Blackwood schedule uses **RowMajorBottomUp** scan order ([[scan-order]]). It places the easy/forced pieces in rows 14-15 first; failures accumulate at the row 0-3 top before the algorithm runs out of options.

Community 469s have the same geometry because they use the same scan-order direction (bottom-up Blackwood). See [[mismatch-geometry]].

## What broke past it (within vol-17)

- WorstBand + ConflictDriven{80} ALNS targeting the top rows → 455/480 (vol-17 cold record).
- The 51-cell component is too large for K ≤ 5 operators; ConflictDriven{80} matches the size.

## What's still unshipped

- **Band-destroy ALNS operator** specifically for rows 0-3.
- K = 80 ConflictDriven was the working size; finer top-region destroy not optimized.

## Sister basins

- [[basin-457-pt]] — different scan-order origin
- [[basin-454-vol6]] — center-BOTTOM geometry
- [[basin-440-469]] — vol-22 fresh basin

## Linked concepts

- [[mismatch-geometry]] — top-row geometry
- [[blackwood-schedule-calibration]] — what produced this basin
- [[alns]] — WorstBand op
- [[scan-order]] — RowMajorBottomUp explains the geometry

## Linked memory

- `project_e2_vol17_447_top_mismatch`
- `project_e2_vol17_session_summary`
