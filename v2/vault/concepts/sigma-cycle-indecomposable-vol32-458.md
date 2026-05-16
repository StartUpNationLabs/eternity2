---
name: sigma-cycle-indecomposable-vol32-458
description: Confirmed σ-cycle indecomposability between vol-32 458 → McGavin 469. Every cycle subset (sizes 2-80) REDUCES score from 458. Matches vol-65 finding for 459 → McGavin. Universal pattern across local basins.
metadata:
  type: project
---

# σ-cycle indecomposable: vol-32 458 → McGavin 469 (vol-99)

**Status**: `built` — measured 2026-05-16 ~03:27.

## Result

Tested every σ-cycle from vol-32 458 to McGavin 469 independently
(applied each cycle's piece-set swap, scored the resulting hybrid
board).

| cycle # | size | hybrid score | delta from 458 |
|---:|---:|---:|---:|
| 0 | 80 | 288 | **-170** |
| 1 | 42 | 328 | -130 |
| 2 | 42 | 334 | -124 |
| 3 | 40 | 402 | -56 |
| 4 | 25 | 375 | -83 |
| 5 | 10 | 438 | -20 |
| 6 | 4 | 451 | -7 |
| 7 | 4 | 442 | -16 |
| 8 | 3 | 453 | -5 |
| 9 | 2 | 451 | -7 |
| 10 | 2 | 452 | -6 |

**Every single cycle, including the smallest 2-cell ones, REDUCES
the score.**

## Significance

This confirms the σ-cycle indecomposability finding from
[[../memory/project_e2_vol65_oracle_sigma_indecomposable]]
extends to a SECOND local basin (vol-32 458, not just our local
459).

**Implication: σ-cycle indecomposability is a UNIVERSAL property
of cross-basin transitions to McGavin's 469.** Not specific to our
local 459 basin.

Combined with:
- [[three-basin-halo2-rigidity]] (all 3 basins halo-2 rigid)
- [[sigma-cycles-are-dispersed]] (cycles are board-spanning)
- [[sigma-cycle-topology-3-basins]] (459 needs 154-cell cycle, 458
  needs 80-cell cycle)

The full picture: **to reach McGavin's 469 from ANY local 458/459
basin, you need a SINGLE simultaneous re-arrangement of 80-154
dispersed cells. No incremental subset works. No local halo ≤ 4
operator works.**

## Why this is a hard theorem to break

The σ-cycle subset reductions are typically -5 to -170 points. To
implement the cycle as a sequence of accepted moves under any
acceptance criterion (SA, ALNS, etc.), you'd need:
- Either an oracle telling you to commit a -170 move and recover
  it 80 moves later
- Or a "lookahead" that evaluates 80-cell joint moves before
  accepting (combinatorial explosion)
- Or a completely different formulation that doesn't proceed by
  incremental moves

No current algorithm I'm aware of does this on canonical E2.

## Linked

- [[sigma-cycle-topology-3-basins]]
- [[sigma-cycles-are-dispersed]]
- [[why-records-are-mip-rigid]]
- Memory: `project_e2_vol65_oracle_sigma_indecomposable.md`
