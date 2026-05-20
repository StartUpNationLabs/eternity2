---
name: joint-cell-piece-set-mip
description: T1 (vol-105) - MIP on a non-contiguous σ-cycle cell set, asking whether MIP can find a > 0 permutation when outside-of-cycle pieces are pinned. Tests the rigidity theorem on a 80-cell board-spanning region.
metadata:
  type: project
status: built
---

# Joint cell-set + piece-set MIP (vol-105 T1)

**Status**: `in-progress` (MIP queued behind T2.a).
**Files**:
- `scripts/vol105_sigma_cycle_extract.py` — σ-cycle decomposition.
- `output/vol-105-sigma-cycles/458_to_mcgavin_cycles.json`.
- `output/vol-105-sigma-mip/*` (results).

## Setup

Starting from the local 458 board (vol-32 RECORD_BREAK_458).
σ-decomposition to McGavin 469: 11 cycles, sizes
[80, 42, 42, 40, 25, 10, 4, 4, 3, 2, 2], total 254 cells differ.

We pick the 80-cell giant cycle (board-spanning rows 1-14 × cols 1-14).
- **Cluster** = those 80 cells.
- **Outside** = the other 176 cells, pinned to vol-32 458's pieces.
- **MIP** = `repair_cluster` from `bench-audit::cluster_repair` — Option A
  (permute pieces within the cluster).
- **Pieces in cluster** = the 80 pieces currently in those 80 cells
  under the 458 board (NOT McGavin's 80 pieces — those are different
  pieces).
- **Objective** = matched edges internal to cluster + boundary edges
  (where one cell in cluster, neighbor pinned).

## What outcomes mean

Per vol-99: applying THE 80-CYCLE (specific permutation that brings
the 80 pieces to McGavin's positions) gives global score 288 from 458,
i.e. -170. So the σ-cycle IS the McGavin-target permutation but the
hybrid score is much worse because the OTHER 174 different cells stay
at 458 (mismatching McGavin's boundary).

MIP outcomes:

1. **delta = 0** (identity is optimal): the 80-cell σ-cycle cell-set
   is rigid under MIP-optimal permutation, EVEN THOUGH the outside is
   not McGavin. Extends rigidity theorem to non-contiguous,
   board-spanning regions. Strong negative.

2. **delta > 0, found new basin > 458**: a new basin discovered.
   Constructive 458-breaker.

3. **delta > 0 but the MIP-found permutation = the McGavin σ-cycle**:
   not possible (vol-99 shows -170, not > 458).

4. **MIP terminates by time limit with non-trivial gap**: gives a
   sound UB on the 80-cell isolated contribution.

## Why this is non-trivial

The existing halo-r ≤ 4 rigidity proofs all use CONTIGUOUS clusters
around defect cells, max 56-cell cluster (vol-96 halo-4 comp-0). The
80-cell σ-cycle is NON-CONTIGUOUS, BOARD-SPANNING (rows 1-14 × cols
1-14). This tests whether rigidity holds for the "natural" cell-set
that the σ-decomposition theory identifies.

If rigidity holds even here, the rigidity theorem is even stronger
than already proven: every "natural" basin-transition cell set is
MIP-locally optimal.

If rigidity fails, we have an ALGORITHM: extract the giant σ-cycle
from a target basin, MIP-optimize that cell-set, iterate. Could lift
458 → 459 → 460 → ...

## MIP size estimate

- 80 cells × 80 pieces × 4 rotations = 25,600 x-vars.
- Plus internal-edge y-vars + boundary-edge y-vars.
- vol-86 top-4 was 18,776 vars, 1200s, 6% gap.
- This is ~1.4× larger; expect 1500-3600s for similar gap.

## Linked

- [[sigma-cycle-topology-3-basins]]
- [[sigma-cycle-indecomposable-vol32-458]]
- [[mcgavin-mip-local-optimal-halo1]]
- [[mcgavin-halo4-comp0-proven]]
- [[vol-105]]
