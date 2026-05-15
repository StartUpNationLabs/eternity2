---
name: local459-halo1-joint-proven
description: Local 459 PROVEN joint-MIP locally optimal at halo r=1 over 59-cell region. Adds to corpus alongside vol-83's McGavin proof. BOTH high-score records now rigorously proven halo-1-rigid.
metadata:
  type: project
---

# Local 459 — joint-MIP locally optimal at halo r=1 (vol-90)

**Status**: `built` — PROVEN 2026-05-16 ~01:46.
**Tool**: `vol62_cluster_mip_bound` with `--joint-mip --joint-halo 1`.
**Time**: 1800s HiGHS wall (per-component MIPs ~30s, joint MIP ~1770s).
**Files**: `output/vol-90-local459-halo1.log`.

## Result

Local 459 has 35 defect cells in 4 connected components:
- Comp 0: 18 defect cells, 26-cell region with halo r=1
- Comp 1: 11 defect cells, 22-cell region with halo r=1
- Comp 2: 4 defect cells, 8-cell region with halo r=1
- Comp 3: 2 defect cells, 8-cell region with halo r=1

**Per-component MIPs**: All 4 returned delta = +0 (proven optimal).
Total per-component time: ~30s.

**Joint MIP** across all 35 defect cells + halo r=1 (59 total
cells): **delta = +0, obj = 120, time = 1800s.**

Status output: "This basin is MIP-locally optimal at every tested
radius."

## Significance

This is the **MATCHING PAIR** to vol-83's McGavin halo-1 proof:

| basin | halo-1 joint region | result | time |
|---|---|---|---|
| McGavin 469 | 37 cells | +0 PROVEN | 895s |
| Local 459 | 59 cells | +0 PROVEN | 1800s |

**Both top records of canonical E2 are rigorously proven
halo-1-joint-MIP-locally-optimal.**

The maximally-adversarial thesis now holds across:
- Multiple basins (459 + 469)
- Both top-concentrated (McGavin) and bottom-concentrated
  (local 459) mismatch geometry
- Different mismatch component counts (2 for McGavin, 4 for local 459)

This is the strongest single result enforcing the thesis on
canonical E2 to date.

## Implication for record-breaking

Combined with vol-83 + vol-85 + vol-88 + vol-89 + vol-90:
- McGavin 469: rigid in 37-cell + 48-cell regions
- Local 459: rigid in 16-cell + 32-cell + 59-cell regions

To improve EITHER record by ≥ 1 requires moves spanning more cells
than the union of these proven regions. Concretely:
- McGavin: moves outside the 48-cell top-3 + 37-cell halo-1.
- Local 459: moves outside the 59-cell halo-1 joint region.

Or board-spanning σ-cycle transitions (per
[[vol-65-oracle-sigma-indecomposable]]: 11-cycle, 255-cell joint
move required to move from 459 → McGavin's 469 basin; every
subset of the cycle reduces score).

## Linked

- [[mcgavin-mip-local-optimal-halo1]] (matching pair)
- [[local459-mip-bottom-rigid]] (smaller region proofs)
- [[local459-mismatch-geometry]] (bottom-concentrated)
- Memory: `project_e2_vol62_mip_local_optimality.md`
