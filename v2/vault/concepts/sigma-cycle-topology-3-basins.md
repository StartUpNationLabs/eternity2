---
name: sigma-cycle-topology-3-basins
description: σ-cycle topology between 3 canonical E2 basins (local 459, vol-32 458, McGavin 469). Local transitions have balanced cycles; cross-McGavin transitions have ONE giant 80-154 cell cycle. Quantifies "board-spanning" requirement to reach McGavin.
metadata:
  type: project
status: built
---

# σ-cycle topology — local-vs-McGavin (vol-97)

**Status**: `built` — computed 2026-05-16 ~03:00.
**Method**: piece-id σ map between three boards.

## Hamming distances

For three canonical E2 records:

| transition | Hamming (cells with different pieces) |
|---|---:|
| Local 459 ↔ vol-32 458 | 227 |
| Local 459 ↔ McGavin 469 | 255 |
| Vol-32 458 ↔ McGavin 469 | 254 |

McGavin is Hamming-equidistant ~255 from BOTH 459 and 458 — these
two local records share a Hamming neighborhood (227 distance) but
are both far from McGavin (255-254).

## σ-cycle decomposition

| transition | # cycles | largest cycle | top-10 sizes |
|---|---:|---:|---|
| 459 → 458 | 14 | 85 | [85, 56, 18, 14, 12, 8, 8, 7, 5, 4] |
| 459 → McGavin | 11 | **154** | [154, 22, 19, 18, 13, 9, 7, 6, 3, 2] |
| 458 → McGavin | 11 | **80** | [80, 42, 42, 40, 25, 10, 4, 4, 3, 2] |

**459 → McGavin requires a 154-cell single joint cycle** — 60% of
all moved cells in one cycle. The transitions BETWEEN local records
(459↔458) have more balanced cycles (max 85, average smaller).

## Mathematical consequence

To use σ-cycle moves to reach McGavin's 469 basin starting from
any local 458/459 basin: **a single joint move involving 80-154
cells is required.**

Combined with vol-65 memory (oracle_sigma_indecomposable: every
subset of the 459→McGavin σ-cycle reduces score), this means:
- The MIP halo-N cellular rigidity proofs (halos 1-3 proven, halo-4
  likely) cover cell-counts up to ~89 cells per region.
- The smallest joint cycle to reach McGavin (80 cells via vol-32
  458) is right at the edge of MIP-tractability.
- The path 459 → McGavin (154 cells) is FAR larger than any MIP
  has solved on canonical E2.

So **escaping any local basin to reach McGavin requires a joint
move at the EXACT THRESHOLD where our MIP capability fails.** This
is the structural choke point.

## Conjectured implication for "the algorithm that solves E2"

If the score landscape is structured such that ALL basin transitions
require ~80-150-cell joint moves AND no local MIP can prove
optimality above ~50-80 cells, then:
- No constraint-propagation or local-search algorithm can
  efficiently traverse basins.
- The algorithm that solves E2 must either:
  - Construct ~100-cell joint moves directly (oracle-like).
  - Use a fundamentally different formulation (e.g., quantum
    annealing, factor-graph reduction, group-theoretic basin
    enumeration).

This is the mathematical formulation of vol-65's
oracle_sigma_indecomposable finding extended to multiple basins.

## Linked

- [[mcgavin-mip-local-optimal-halo1]]
- [[three-basin-halo2-rigidity]]
- Memory: `project_e2_vol65_oracle_sigma_indecomposable.md`
- Memory: `project_e2_vol65_sister_basin_sigma_cycles.md`
