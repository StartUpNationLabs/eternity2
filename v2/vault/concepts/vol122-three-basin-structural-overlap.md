---
name: vol122-three-basin-structural-overlap
description: "Vol-122 cross-basin analysis: McGavin 469, vol-60 459, and vol-122 perm0_444 share only 0-1 cells pairwise (except vol-60↔perm0 share 21). Three distinct basin families."
metadata:
  type: project
status: built
---

# Vol-122 — three-basin structural overlap

## Setup

Compared three boards cell-by-cell (exact pid + rotation match):
- **McGavin 469** (community canonical 1-clue equivalent, 469 matched)
- **vol-60 459** (standing record, 459 matched)
- **vol-122 perm0 444** (clean-slate vol-122 generated, 444 matched)

## Result

| Pair | Shared cells (exact) | / 256 |
|---|---|---|
| McGavin 469 ↔ vol-60 459 | **1** | 0.4% |
| McGavin 469 ↔ perm0 444 | **1** | 0.4% |
| vol-60 459 ↔ perm0 444 | **21** | 8.2% |
| All three | 0 | 0% |

The "1 shared cell" between McGavin and vol-60/perm0 is position 135
(the canonical hint at TL+135).

## Interpretation

**Three structurally distinct basin families.** The shared cells are
near-zero between McGavin and any vol-* basin (1 cell = canonical hint
position only). The local rigidity theorem (memory
`project_e2_2026_05_16_rigidity_theorem`) doesn't imply two high-scoring
boards must look alike — they reach similar scores via COMPLETELY
different piece arrangements.

vol-60 459 and vol-122 perm0 444 share 21 cells = **moderate overlap**
suggesting they're in the same "basin family" (both come from
border-first MRV pipeline + ALNS). But still 91% disjoint.

## Implications

1. **Basin discovery is NOT convergent**: different starts → different
   final boards. No "natural" path between basins.
2. **The rigidity theorem is LOCAL**: McGavin's basin is rigid under
   K-bounded moves WITHIN ITSELF, but completely unconnected to vol-60's
   basin.
3. **Cross-basin transfer is hopeless** (matches K6 cycle-slip refutation):
   moving FROM perm0_444 TOWARD McGavin's 469 requires changing 255/256
   cells.

## Math view

The 459/469-band has at LEAST 2 disjoint basin families. Probably many
more — each "basin family" is roughly defined by the algorithmic
pipeline that discovered it. The number of HIGH-SCORE basins for E2 is
unknown but likely > 100, scattered in piece-permutation space.

To beat 459/469 with high probability, need to enumerate MANY basins
and find one that exceeds. That's what vol-110 corner-sweep did
(thousands of partials → one 459 outlier).

## Status

`finding-structural` — confirms basin diversity, motivates massive
enumeration.

## Linked

- [[vol-122]]
- [[vol122-25-edge-gap-is-all-interior]]
- [[vol122-sigma-perm0-444-to-mcgavin-indecomposable]]
- vol-65 σ-cycle indecomposability (memory)
- vol-110 NEW_459_from_off100 (different 459 basin from vol-60)
