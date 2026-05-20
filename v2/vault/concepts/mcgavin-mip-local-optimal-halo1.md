---
name: mcgavin-mip-local-optimal-halo1
description: McGavin's 469 is JOINT-MIP-locally-optimal at halo r=1. Adds him to the corpus of 5 high-score records (458, 459×3, 469) all proved unbreakable by local ops with halo ≤ 1. Strongest evidence yet for "maximally-adversarial puzzle" thesis.
metadata:
  type: project
status: built
---

# McGavin 469 — joint-MIP-locally-optimal at halo r=1

**Status**: `built` — proven 2026-05-16 00:41 vol-83.
**Tool**: `vol62_cluster_mip_bound` with `--joint-mip --joint-halo 1`.
**Time**: 895s (15 min) HiGHS B&B on 37-cell joint MIP.
**Files**: `output/vol-83-mcgavin-mip/mcgavin_halo1.log`.

## Result

McGavin's 469 has 16 defect cells (cells incident on ≥1 mismatched
edge) in 2 connected components of 8 cells each.

**Per-component MIPs** (halo r=1):
- Component 0: core 8, region 18 cells. **delta = +0**, obj=41.
- Component 1: core 8, region 21 cells. **delta = +0**, obj=48.

**Joint MIP** across both components + halo r=1 (37 total cells):
**delta = +0**, obj=80, time=895s.

**Conclusion**: McGavin's 469 is JOINT-MIP-locally-optimal at every
tested radius (r=0 trivially, r=1 here). No piece-permutation +
rotation within the 37-cell joint region can improve his score.

## Strategic implication

This adds McGavin to the corpus of high-score records all proven
joint-MIP-locally-optimal at halo-1:

| score | board path | halo-1 delta |
|---|---|---|
| 458 (vol-32) | `output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json` | +0 |
| 459 (vol-60) | `output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json` | +0 |
| 458 (basin A) | (per memory) | +0 |
| 459 (sister) | (per memory) | +0 |
| **469 (McGavin)** | `output/vol-65/mcgavin_469.json` | **+0** ← NEW |

**All 5 tested high-score records are MIP-locally-optimal at halo-1.**

## Refutation of local destroy operators

This refutes ALL local-destroy ALNS operators with halo ≤ 1 as
mechanisms for breaking record:
- ComponentClusterDestroy (halo 1)
- WorstWindow / WorstBand (smaller than 37 cells)
- MwpmDefectPair (matches defect cells, small region)
- ConflictDriven (max_size 30 — too small)
- Standard piece-swap / 2-cell transpose

To break a 469 (or any of the 5 records), **board-spanning or
larger-halo** moves are required. Per memory
`project_e2_vol65_oracle_sigma_indecomposable`: the σ-cycle from
459 → McGavin's 469 has 11 cycles spanning 255 cells, with every
subset reducing score. **Cross-basin transitions need full-cycle
joint moves.**

## What this strengthens

- **Maximally-adversarial thesis** (now 21+ axes):
  EVERY tested local-optimum at the top of the score landscape is
  joint-MIP-rigid against halo-1 ops.
- **Vol-62 protocol's reliability**: the joint-MIP test correctly
  identifies "unbreakable by local ops". McGavin's 469 was a
  highest-stakes test of this protocol; it passed.

## What's still open

- **Halo-2 MIP**: is McGavin breakable at halo r=2? Region would be
  ~70-90 cells, MIP ~50k binary vars, hours to solve. Unknown.
- **Top-5-rows MIP** (vol-84 currently running): tests whether the
  TOP HALF of the board (80 cells, McGavin's hard region) has any
  rearrangement giving fewer than 11 mismatches.
- **Cross-basin joint moves**: explicit construction of board-
  spanning destroy operators. The σ-cycle suggests the structure
  exists; how to discover it without an oracle is open.

## Linked

- [[mcgavin-469-basin]]
- [[mcgavin-469-mismatch-geometry]]
- Memory: `project_e2_vol62_mip_local_optimality.md`
- Memory: `project_e2_vol65_oracle_sigma_indecomposable.md`
