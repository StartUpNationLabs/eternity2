---
name: basin-permutation-group
description: The two 458 boards vol-61-stage3-seed17 and vol-61-stage3-seed200
status: built
metadata:
  type: concept
---
# Basin-permutation-group on 458 sister basins (vol-65 day 3.5)

**Status**: `built` (empirical observation), `unbuilt` (theory) — vol-65 (2026-05-15).
**Type**: structural finding from twin-diagnostic + sister-basin-diff.

## The observation

The two 458 boards `vol-61-stage3-seed17` and `vol-61-stage3-seed200`
(produced by the same pipeline, different seeds, identical stage 2
input) differ in **46 cells** out of 256, and they share the same
score (458/480).

**Detailed structural analysis** (`scripts/vol65_sister_basin_diff.py`):

| property | value |
|---|---|
| Hamming distance | 46 cells |
| Bounding box of diffs | rows 12-15 (entire bottom strip) |
| Connected components of diffs | 2 (size 39 + size 7) |
| σ-cycles in piece-permutation | 6 (lengths 17, 11, 8, 5, 3, 2) |
| Diff cells in s17 defect set | 7 / 34 |
| Diff cells in s200 defect set | 8 / 35 |
| Diff cells in EITHER defect set | 9 |
| **Diff cells in NEITHER defect set** | **37 (80%)** |

## The implication

**37 of 46 diff cells are MATCHED IN BOTH BASINS.** Same matched
score, achieved via two distinct piece-placements at those cells.

This means there is a **piece-permutation σ** with the following
properties:
- σ is non-trivial: 46 cells affected
- σ decomposes into 6 cycles (lengths 17, 11, 8, 5, 3, 2)
- σ preserves the matched-edge count (score = 458 in both)

In other words, **σ is a SCORE-PRESERVING symmetry on the 458 basin**.
The basin is not a single board; it's an EQUIVALENCE CLASS of boards
related by σ-type permutations.

## Why this is significant

Classical ALNS treats each piece-position as an independent variable.
This finding says: **at the matched-edge level, 6-cycle σ-permutations
across the bottom 4 rows are free moves**. They don't gain or lose
score, but they switch basins.

If we can characterize the **subgroup of permutations** that preserve
the 458 score-level set, we have a group action with orbits = score-
equivalence-classes. Moving WITHIN an orbit doesn't help, but
**moving BETWEEN orbits (i.e., to a higher-score class) might be
easier from certain orbits than others**.

This is a vol-65 candidate for a new algorithm: **Orbit-Cycling-Search**
— at each step, before destroying anything, try ALL σ-cycle
permutations within the score-preserving subgroup. Some moves are
within-orbit (free); some break the symmetry and produce higher-score
boards.

## Cycle structure as a starting point

The 6-cycle decomposition above gives 6 "atomic" σ-moves on this
specific basin pair. Their cycle structure (17+11+8+5+3+2) reflects
the local color compatibility — pieces in a cycle of length k can
rotate through positions where ALL k pieces are color-compatible
with their new neighbors.

## What this tells us about the 458 plateau

Vol-22 / vol-32 found 458 basins are operator-locked under K≤5 moves.
This vol-65 finding REFINES that:
- 458 basins are operator-locked for SCORE-IMPROVING moves of K≤5.
- But they're NOT operator-locked for SCORE-PRESERVING moves of K up
  to 17 (the largest σ-cycle here).

The score-equivalence orbits are LARGER than we thought; the 458
ceiling is reached via many equivalent placements.

## How this connects to vol-62 MIP-bound

Vol-62 proved 458/459 basins are joint-MIP-locally-optimal at halo-1
(57-64 cell joint region). This is consistent: the σ-cycle moves
here have cycles WITHIN the bottom-4-rows region (rows 12-15, =
cells 192-255). That's 64 cells — exactly the halo region size
where MIP says "no improvement possible." The σ-moves are
SCORE-PRESERVING; MIP wasn't asked about those, only score-improving.

If we re-run MIP with the relaxation "allow ≤ 0 delta but enumerate
distinct solutions," we'd recover the σ-orbit structure.

## Vol-65 next experiment

Take all 4 known 458/459 records:
- local 459 (p06)
- vol-32 458
- vol-61 458 seed17
- vol-61 458 seed200

Pairwise compute the σ-cycle decomposition. Do they form a single
σ-orbit? Or multiple disjoint orbits? Are some cycle-lengths common
across pairs?

If a stable cycle-length distribution emerges (e.g., "all 458 basins
within a family differ by 6-cycles of length 17+11+8+5+3+2"), that's
a structural invariant of the 458 plateau.

## Cross-orbit distance to McGavin 469

The McGavin community-469 board (decoded from
`output/community_corpus/groups_172011298_469.json` via
`scripts/vol65_decode_bucas_to_placement.py`,
`output/vol-65/mcgavin_469.json`) is Hamming-DISTANT from every
458 we have:

| pair (vs McGavin 469) | Ham | cycle decomp |
|---|---|---|
| local-459-p06 | 255 | 154+22+19+18+13+9+7+6+3+2+2 |
| vol-32 458 | 254 | 80+42+42+40+25+10+4+4+3+2+2 |
| vol-61 458 s17 | 252 | 94+58+34+27+26+5+2+2+2+2 |
| vol-61 458 s200 | 248 | 99+47+42+23+15+13+3+2+2+2 |

**The σ-cycle structure to reach McGavin 469 contains cycles of
length 80-154** in every pair. Standard ALNS destroys at most
~64 cells; reaching McGavin requires σ-cycle moves an order of
magnitude larger.

This characterizes the **σ-cycle gap** between our 458/459 basins
and the community ceiling. It's structural and measurable.

### Implication for vol-65+ algorithms

Any algorithm targeting 469 (or higher) must support **basin-scale
σ-cycle moves** (length ≥ 80 cells). This rules out:
- Standard ALNS (k ≤ 64 cell destroys)
- Local repair (MIP bounded at halo ≤ 1)
- 5-cycle / cluster swaps (vol-22 scale)

What might work:
- **Trajectory replay** like vol-63 Temporal-Rewind-Search (jumps
  to past states, may cross orbit boundaries)
- **Cross-basin σ-cycle import** — given a reference 469 board,
  apply σ-cycle to translate our board toward it
- **Hybrid: PSM-LP with multiple basin warm-starts** — solve PSM
  with bias toward different known-good boards as initialization

## Linked

- [[piece-side-matching]] (parent PSM concept)
- [[piece-orbit-structure]] (group-theoretic context)
- [[vol-65]]
- [[mip-local-optimality-459]] (complementary — local MIP at score-improving)
- vol-22 basin-escape recipe (sister-basin discovery via bound-ascent;
  this is now refined as σ-orbit structure)
