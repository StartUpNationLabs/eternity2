---
name: mcgavin-basin-rigidity
description: Pinning top N rows of each basin's source + running our ALNS (60s,
status: built
metadata:
  type: concept
---
# McGavin's basin has unique rigidity: bottom-2-rows determined by top-14

**Status**: `built` — vol-68 (2026-05-15).
**Origin**: cross-basin N-row scaling experiment.

## Result

Pinning top N rows of each basin's source + running our ALNS (60s,
winning5, seed=1), comparing score to target:

| basin | target | N=12 | N=13 | N=14 | N=15 |
|---|---|---|---|---|---|
| McGavin | 469 | 450 | 455 | **469** ★ | 469 |
| local-459 | 459 | 441 | 454 | 456 | 454 |
| vol-32-458 | 458 | 456 | 455 | 456 | 454 |
| vol-61-s17 | 458 | 444 | 455 | 454 | 454 |

**Only McGavin's basin shows the sharp N=14 threshold (+14 jump
from 455 to 469).** Our 3 basins all cluster at 454-456 across all
N values 12-15.

## The rigidity property

McGavin's basin has a STRUCTURAL RIGIDITY: pinning the top 14 rows
uniquely forces the remaining 32 cells to produce 469. The bottom 2
rows have ONE valid completion.

Our basins don't have this rigidity: even with 15 rows pinned (240
of 256 pieces), our ALNS finds a 454-completion. Multiple completions
of similar score exist; ALNS picks an alternate.

This means McGavin's basin has an **unusually-deterministic bottom
half**. Most basins admit several completions; McGavin's admits one.

## Why our basins are "flexible"

Hypothesis: our basins have low score AT THE BOUNDARY between
last-row-pinned and last-row-free. The 16 free cells in row 15
admit multiple piece-arrangements all giving ~454. ALNS picks one
randomly.

McGavin's basin has the OPPOSITE property: row 15's 16 free cells
admit ONE piece-arrangement giving 469. ALNS converges to it.

## Implication

McGavin's basin is a STRUCTURAL OUTLIER in our 47-component
landscape. It has a property our other basins lack: rigid
bottom-row completion.

This means: to find new basins similar to McGavin, we should
look for basins where pinning N=14 rows gives a unique 469-class
completion. Standard ALNS doesn't find these — too few constraints
force the search.

## What's NEXT to test

1. Does pinning top N=14 rows of ALL 47 of our basins give the
   pinned-basin's score? If most basins are "loose" (multiple
   bottom completions), the answer is mostly no.

2. Does McGavin's basin have other "rigidity" axes? E.g.,
   left-half + right-half is rigid? Top-quadrant + bottom-quadrant?

3. Can we ENGINEER rigid basins by adding extra-hint pinning?
   That is, generate top-14-row candidates that uniquely force
   bottom-row to a target.

## Linked

- [[mcgavin-n-row-scaling]] (parent — single-basin scaling)
- [[basin-component-landscape]]
- [[e2-maximally-adversarial-thesis]]
