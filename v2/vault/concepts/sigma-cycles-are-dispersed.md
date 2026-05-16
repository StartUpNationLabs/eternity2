---
name: sigma-cycles-are-dispersed
description: σ-cycles between basins (458 → McGavin, etc.) are geometrically DISPERSED across rows 1-14 cols 1-14, not localized in any region. Confirms board-spanning requirement is geometric, not just topological.
metadata:
  type: project
---

# σ-cycles between basins are board-spanning (vol-97)

**Status**: `built` — derived 2026-05-16 ~03:16.

## Result

Decomposed the σ-permutation from vol-32 458 → McGavin 469.
Largest cycle has 80 cells. Computed the geometric layout of each
cycle.

| cycle # | size | rows spanned | cols spanned |
|---:|---:|---|---|
| 0 | 80 | 1-14 (all interior) | 1-14 (all interior) |
| 1 | 42 | 1-14 | 1-13 |
| 2 | 42 | 1-14 | 1-14 |
| 3 | 40 | 0-15 (with gaps) | 0-15 (with gaps) |
| 4 | 25 | 1-14 (some gaps) | 1-14 (some gaps) |
| 5 | 10 | 0, 6, 8, 11, 15 | sparse |
| 6 | 4 | 0, 15 | 0, 15 (corners!) |
| 7-10 | 2-4 | sparse | sparse |

**EVERY large cycle (size ≥ 25) is board-spanning** — touches
nearly every row and column of the interior.

## Geometric implication

The σ-cycles 458 → McGavin are NOT localized to a compact region.
They are dispersed across rows 1-14 × cols 1-14 (the entire
interior).

Implication: a "joint move" implementing one of these cycles would
need to touch ~80 cells SCATTERED across the full interior of the
board, simultaneously.

## Why MIP-tooling fails on these moves

The `cluster_repair` tool we use permutes pieces WITHIN a cluster
(piece-set fixed by current cluster contents). But the σ-cycle
from 458 → McGavin REPLACES pieces (the piece-id at position p in
the cycle changes from p_458 to p_mcg, which is a DIFFERENT piece).

So even feeding the 80 dispersed cycle cells to cluster_repair
would not test the σ-cycle move — it would just permute the
current 80 pieces among themselves, finding nothing new.

## What this means for record-breaking

To traverse from any local basin (458/459) to McGavin's 469:
- A simultaneous re-arrangement of 80-154 cells dispersed across
  the full board is required.
- Each cell involved must accept a DIFFERENT piece from a
  different position.
- The current piece-permutation MIP cannot test such moves.

A **new tool** would be needed: a MIP that allows piece-set swaps
between an "in-region" and "out-of-region" set, not just
permutations within a region.

## Conjectured "right" algorithm class

The algorithm that solves canonical E2 must:
1. Identify dispersed σ-cycle candidates (computational
   topology / group theory).
2. Test feasibility of joint moves where 80+ pieces are
   re-assigned across the board.
3. Have a MIP/CP/SAT formulation that scales to this size.

To my knowledge, no current solver framework does this. Most
puzzle solvers do localized search; cross-basin σ-cycle
construction is unexplored.

## Linked

- [[sigma-cycle-topology-3-basins]]
- [[why-records-are-mip-rigid]]
- Memory: `project_e2_vol65_oracle_sigma_indecomposable.md`
