---
name: mcgavin-halo4-comp0-proven
description: McGavin component 0 PROVEN halo-4 MIP-optimal at 57 cells in 1200s. Comp 1 attempted but killed during run; partial result. Extends McGavin local-optimality to halo r=4 for at least one component.
metadata:
  type: project
---

# McGavin component 0 halo-4 — PROVEN (vol-96 partial)

**Status**: `built` (partial — comp 0 proven, comp 1 killed).
**Tool**: `vol62_cluster_mip_bound --radius 4`.
**Files**: `output/vol-96-mcgavin-percomp-halo4/log.txt`.

## Result

McGavin component 0 with halo r=4:
- Core: 8 defect cells
- Region: **57 cells** (largest single-component MIP region proven)
- Time: 1200.02s (at exactly the time limit)
- **delta = +0** PROVEN

Comp 1 was running when I killed the process (stuck during its
own halo-4 expansion).

## McGavin local-optimality progression — full

| vol | tested | cells (largest comp) | result | time |
|----:|---|---:|---|---:|
| 83 | halo-1 joint | 37 | +0 PROVEN | 895s |
| 92 | halo-2 per-comp | 34 | +0 PROVEN | 153s |
| 94 | halo-3 per-comp | 47 | +0 PROVEN | 929s |
| 96 | halo-4 per-comp 0 | 57 | +0 PROVEN | 1200s |

**McGavin component 0 is rigorously proven rigid at every halo from
r=1 to r=4.**

Progression on cells: 37 → 34 → 47 → 57. Largest proven region on
canonical E2.

## Implication

To find a 470 from McGavin's basin would require:
- Halo ≥ 5 single-component (untested; would be ~70+ cells)
- OR cross-component joint moves (open, vol-91 failed at halo-2 joint)
- OR board-spanning (~80-154 cells per σ-cycle topology
  [[sigma-cycle-topology-3-basins]])

## Linked

- [[mcgavin-halo3-percomp-proven]] (vol-94)
- [[mcgavin-halo2-percomp-proven]] (vol-92)
- [[mcgavin-mip-local-optimal-halo1]] (vol-83)
- [[why-records-are-mip-rigid]]
