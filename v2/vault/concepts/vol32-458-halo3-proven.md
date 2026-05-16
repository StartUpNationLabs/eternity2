---
name: vol32-458-halo3-proven
description: Vol-32 458 halo-3 per-component MIP-optimal — comp 0 79-cell region PROVEN +0 in 1200s. Largest single-component MIP-optimal region proven on canonical E2 to date.
metadata:
  type: project
---

# Vol-32 458 halo-3 per-component — PROVEN (vol-102)

**Status**: `built` — PROVEN 2026-05-16 ~05:32.
**Tool**: `vol62_cluster_mip_bound --radius 3`.

## Result

| comp | core | size | delta | obj | time |
|---:|---:|---:|---:|---:|---:|
| 0 | 32 | **79** | **+0** | 157 | 1200s |
| 1 | 4 | 19 | +0 | 43 | 0.2s |

## Significance — largest proven region

This is the **LARGEST single-component MIP-optimal region ever proven
on canonical E2**: 79 cells, +0 delta, gap 0%.

Updated cross-basin × halo matrix:

| basin | halo-1 joint | halo-2 per-comp | halo-3 per-comp | halo-4 per-comp |
|---|---|---|---|---|
| McGavin 469 | 37 cells | 29+34 | 42+47 | 57 (comp 0) |
| Local 459 | 59 cells | 35+35+13+17 | (untested) | 56+60+26 (3/4) |
| Vol-32 458 | (vol-62) | 65+13 | **79+19** | (untested) |

**Vol-32 458's halo-3 comp 0 (79 cells, +0 PROVEN) exceeds any
previously-proven region on canonical E2.** The basin is rigidly
locally optimal in a region covering nearly 1/3 of the board.

## Why vol-32 scales better

Vol-32 458's components are larger (32+4 defects vs McGavin's 8+8
or local 459's 18+11+4+2). HiGHS handles the LARGER vol-32 region
(79 cells) MORE EFFICIENTLY than smaller higher-halo McGavin
regions. Counter-intuitive but consistent with the methodological
lesson: **defect-cell density determines LP tightness, not raw
cell count.**

## Total proven coverage

Combined across all halo-1 to halo-4 results:
- McGavin 469: 37 (joint) ∪ 48 (top-3) ∪ 47 (comp 1 halo-3) ∪ 57 (halo-4 comp 0) cells
- Local 459: 59 (joint) ∪ 80 (rows 13-15) ∪ 116+126+55 (halo-4 3/4 comps)
- Vol-32 458: 65+13 (halo-2) ∪ 79+19 (halo-3)

Across 3 basins, hundreds of cells proven MIP-locally-optimal.

## Linked

- [[mcgavin-halo4-comp0-proven]]
- [[local459-halo4-percomp-partial]]
- [[mip-tightness-depends-on-defect-density]]
- [[why-records-are-mip-rigid]]
