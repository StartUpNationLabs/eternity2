---
name: vol122-hffm-forced-pieces
description: "Vol-122 J7 — Hint-Free Forced-Move analysis: 92/256 pieces (36%) uniquely provide some adjacency color-pair. These are STRONGLY constrained in placement."
metadata:
  type: project
status: built
---

# Vol-122 J7 — Forced-Move Analysis

## Setup

For each ordered color pair (c1, c2), count pieces that can present
c1 on a side and c2 on the next-clockwise side (= "L-shape supply"
for that pair).

For each piece, find color-pairs that ONLY THIS PIECE provides.

## Result

- **362 distinct (c1, c2) color pairs** appear in piece L-shapes.
- **Distribution of supply (= # (piece, rot, side) producing each pair):**
  - supply=4: 121 pairs (most common, minimal supply)
  - supply=8: 80 pairs
  - supply=12: 75 pairs
  - supply≥16: 86 pairs
- **No supply=1 (singleton) pairs**; minimum supply is 4 (= 1 piece × 4 rotations).
- **92/256 pieces** (36%) uniquely provide at least one color pair.

## Top forced pieces

| Piece | Edges (TRBL) | Unique pairs |
|---|---|---|
| 0 | (B, B, 1, 3) | (1, 3) |
| 1 | (B, B, 1, 4) | (1, 4) |
| 2 | (B, B, 2, 3) | (2, 3) |
| 3 | (B, B, 3, 2) | (3, 2) |
| 4 | (B, 1, 6, 1) | (1, 6), (6, 1) |
| 5 | (B, 1, 7, 2) | (1, 7) |
| 7 | (B, 1, 9, 5) | (9, 5) |
| 8 | (B, 1, 12, 3) | (1, 12), (12, 3) |

The 4 corner pieces each uniquely provide a color pair. Most other
forced pieces are edge pieces (with 1 BORDER side).

## Implication

If we KNEW which adjacencies in a 469+ board require each (c1, c2) pair,
we could **deduce 92 piece placements** directly. The challenge: the
puzzle is hard precisely because we DON'T know the perfect adjacency
pattern.

But the analysis suggests:
- **Border/edge pieces are heavily forced** — their placement is
  constrained by which (c1, c2) pairs they uniquely provide.
- **Interior pieces are less forced** — most have 4-12 piece alternatives
  for the pairs they provide.

This matches the LP-UB finding (per-color supply is loose) but at the
pair level: most pairs have plenty of supply (4+).

## Status

`finding-structural` — confirms what we already knew (border pieces are
constrained, interior more flexible). Doesn't directly yield a new
algorithm but motivates further work:

1. **Adjacency-pair MIP**: encode "puzzle needs N copies of each pair (c1, c2)"
   as a global constraint over which (piece, rot, side) provide it. May
   give tighter UB than per-color.
2. **Pair-supply CSP propagator**: during search, track which pairs have
   been "consumed" and prune branches that would exhaust supply.

## Linked

- [[vol122-pcls-poc-result]] (per-color, not pair)
- [[vol122-cfcc-color-flow-propagator]] (K3, similar idea but per-color)
- [[vol-122]]
