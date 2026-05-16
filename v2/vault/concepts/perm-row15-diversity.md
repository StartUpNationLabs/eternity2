---
name: perm-row15-diversity
description: Each corner perm has narrow distinct row-15 arrangement set. McGavin perm has 8 distinct row-15s across 54 boards; local 459 perm has 3 (consistent narrow basin); vol-32 perm has 13 (more diverse).
metadata:
  type: project
---

# Per-perm row-15 diversity (vol-99 finding)

**Status**: `built` — measured 2026-05-16 ~06:30.

## Method

For each corner perm class, count distinct row-15 arrangements
(16-piece tuples) across all stored boards in that perm class
with score ≥ 455.

## Result

| corner perm | max score | n boards | distinct row-15s |
|---|---:|---:|---:|
| (3, 2, 0, 1) McGavin | 469 | 54 | 8 |
| (2, 3, 0, 1) | 462 | 53 | 9 |
| (1, 0, 2, 3) local 459 | 459 | 34 | 3 |
| (0, 3, 1, 2) vol-32 458 | 458 | 130 | 13 |
| (2, 0, 1, 3) | 458 | 86 | 10 |
| (2, 3, 1, 0) | 458 | 63 | 6 |
| (0, 3, 2, 1) | 457 | 96 | 20 |
| (2, 1, 0, 3) | 457 | 80 | 6 |
| (3, 0, 2, 1) | 457 | 90 | 12 |
| (1, 0, 3, 2) | 457 | 30 | 4 |

## Observations

1. **McGavin perm has 8 distinct row-15s across 54 boards** — most
   boards in this perm share the same bottom row. Suggests the
   469-near-twin orbit is small (consistent with vol-68 finding
   of only 2 distinct 469 boards).

2. **Local 459 perm has only 3 distinct row-15s across 34 boards.**
   Even narrower. Our 459 attempts all converge to similar bottoms.

3. **Vol-32 458 perm has 13 distinct row-15s across 130 boards.**
   ~10% diversity. Most-explored perm in our corpus.

4. **Some perms have only 2-4 distinct row-15s** despite
   30+ boards — these basins are very narrow.

5. The (0, 3, 2, 1) perm has 20 distinct row-15s — outlier.
   Possibly a perm with multiple competing basins.

## Implication

Each perm has a CHARACTERISTIC bottom-row signature with limited
diversity. Within a perm, ALNS converges to a small set of basins,
each defined by row-15 piece arrangement.

This refines the basin structure picture: not just "24 perm
classes" but "perm class × ~3-20 row-15-classes" gives ~150-200
distinct basin families across our corpus.

## Implication for record-breaking

A "perm × bottom-row" sweep would systematically explore basins:
- 24 perms × ~10 row-15s × ALNS = ~240 distinct basin attempts
- Each basin attempt = 5 min ALNS = ~20 hours total
- Tractable as a multi-day experiment

## Linked

- [[corner-perm-score-distribution]]
- [[per-row-diversity-corpus]]
- [[basin-corner-permutations]]
