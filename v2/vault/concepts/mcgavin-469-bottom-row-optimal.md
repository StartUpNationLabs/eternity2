---
name: mcgavin-469-bottom-row-optimal
description: "Vol-125 2026-05-18: PROOF that McGavin's 469 is globally optimal on the 4-cell σ-cycle at bottom row (positions 246-249, pieces 4/8/34/56). Exhaustive 24×256=6144 enumeration confirms no permutation+rotation beats 469 in this region."
metadata:
  type: project
status: built
---

# McGavin 469 — bottom-row 4-cell σ-cycle is proven optimal

**Discovery**: 2026-05-18, vol-125, via near-basin-attack systematic search.

## Setup

McGavin's 469 board (`469_mcgavin_469_6c9a2448.json`) and a winning5-sa
466 board (`466_winning5_sa_t1_s200_166766000_p55554_db75903a.json`)
differ in EXACTLY 4 cells:

| pos | (row, col) | 469 placement | 466 placement |
|-----|------------|---------------|---------------|
| 246 | (15, 6)    | piece 4, rot 2 | piece 8, rot 2 |
| 247 | (15, 7)    | piece 8, rot 2 | piece 34, rot 2 |
| 248 | (15, 8)    | piece 34, rot 2 | piece 56, rot 2 |
| 249 | (15, 9)    | piece 56, rot 2 | piece 4, rot 2 |

The 4 cells form a **horizontal strip on the bottom row** (cols 6-9).

The pieces {4, 8, 34, 56} are IDENTICAL in both basins — only their
positions differ. This is a **σ-cycle of length 4** between 469 and 466
basins, all with rotation=2.

In 469: (4, 8, 34, 56)
In 466: (8, 34, 56, 4) — left-shift by 1

## Exhaustive optimality proof

Enumerated all $4! \times 4^4 = 6144$ configurations:
- 24 permutations of pieces {4, 8, 34, 56} over positions {246, 247, 248, 249}
- 4 rotations independently per piece (4^4 = 256)
- Score each, keep max

**Result**: maximum score across all 6144 configurations is **469**
(McGavin's arrangement). The 466 (shifted) and 22 other configurations
score lower. The σ-cycle's only globally-optimal arrangement is McGavin's.

## Implication

This is a **sub-region optimality proof**. McGavin's 469 is provably
optimal on this 4-cell sub-puzzle. Any breakthrough beyond 469 cannot
come from rearranging just THESE 4 cells.

To beat 469, the rearrangement must involve:
- Cells NOT in {246, 247, 248, 249}, OR
- Pieces NOT in {4, 8, 34, 56}, OR
- Both

This **prunes** the search space for 470+ candidates: don't look in
the bottom-row 4-strip; look elsewhere.

## Combined with other rigidity proofs

This joins the growing list of **proven local optima** for McGavin 469:
- Vol-44 cluster MIP: 22 clusters at halo-1 are locally MIP-optimal
- Vol-99 extended: McGavin near-twin orbit = exactly 2 boards
- Vol-65 σ-cycle indecomposability: σ between 459↔469 is fully coupled
- **NEW vol-125 (this)**: bottom-row 4-strip {246-249} is 6144-trial optimal

The cumulative picture: McGavin 469 is *deeply* locally optimal across
all measured sub-regions. To find 470+ requires a **board-spanning move**
that touches at least 1 cell outside {known-locally-optimal sub-regions}.

## Method

`scripts/inspect_469_466.py` — exhaustive 6144-config enumeration over
the diff cells. Generalizes to any near-basin pair with diff <= 6
(beyond that, factorial blow-up).

Script also tested for 466 ↔ 462 (diff=11): factorial too large for
exhaustive (11! × 4^11 = 1.6 × 10^14 configs). Need smarter enumeration
or LP-relaxation for diff > 8.

## Linked

- [[basin-457-pt]]
- [[mcgavin-469]]
- [[depth-40-phase-transition]]
- [[spectral-swap-invention]]
