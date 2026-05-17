---
name: j1-bidirectional-symmetric-failure
description: "J1 chain fails symmetrically: top-down fails at band 14 (last); bottom-up fails at band 0 (first). Failure point is FAR from the starting boundary, regardless of direction."
metadata:
  type: project
---

# J1 — Bidirectional symmetric failure

## Empirical observation

| Direction | Perfect bands | Decay bands | Failed band | Final score |
|---|---|---|---|---|
| Top-down | 0-6 (7 perfect) | 7-13 (decay 45→35) | 14 | 423/449 |
| Bottom-up | 14-8 (7 perfect) | 7-2 (decay 45→42) | 0 | 422/449 |

**Symmetric failure pattern.** The chain works perfectly for ~7 bands from
the starting boundary, then degrades, then fails at the OPPOSITE end.

## Mathematical interpretation

The puzzle has constraints at BOTH borders:

- Top: row 0 must have BORDER on top edge (=color 0).
- Bottom: row 15 must have BORDER on bottom edge.

Greedy chain ANCHORS on one boundary and propagates inward. The
boundary at the OPPOSITE side has its own constraint set that becomes
infeasible if not anchored.

Define $\delta_r$ = "constraint slack" at band $r$ = number of free
choices in committing the row's piece-rotation-tuple. As bands accumulate,
$\delta_r$ decreases (fewer pieces available, more colors fixed).

Mid-chain bands have:
- One boundary (the starting one) FIXED by anchor.
- The other boundary (far side) UNCONSTRAINED.

So mid-chain choices can deviate from what the far boundary would need.

## The "meeting in the middle" hypothesis

Combine top-down and bottom-up:
1. Top-down chain bands 0-7 (7 bands), commit rows 0-8.
2. Bottom-up chain bands 14-8 (7 bands), commit rows 9-15.
3. The MIDDLE rows 8 and 9 must agree on the band 7 ↔ band 8 boundary.

**Constraint**: row 8 (bottom of top-down's band 7) must color-match row 9
(top of bottom-up's band 8). The 16 horizontal-between-row-8-and-9 colors
must align.

This is a **rendezvous problem**:
- Find a (top-down sequence) and (bottom-up sequence) such that the
  inter-row-8/9 color profile matches at all 16 columns.

If feasible, we get bands 0-7 + 8-14 = all 15 bands = full puzzle.

## Math

Let $P_8$ = color profile of row 8 (16 colors on the SOUTH side of each
cell in row 8). Let $P_9^\top$ = color profile of row 9 (NORTH side).

Match condition: $P_8 = P_9^\top$ (16 element-wise equality).

If the top-down chain has $K_1$ valid 8-row configurations and
bottom-up has $K_2$ valid 7-row configurations, the match probability
(under random color assumption):

$$
\Pr[\text{match}] \approx \left(\frac{1}{23}\right)^{16} \approx 10^{-22}
$$

Without further structure, finding a match by brute force is hopeless.

## Solutions

1. **Joint optimization**: process top-down + bottom-up simultaneously
   with shared row-8/9 boundary as a constraint.

2. **Beam-search at boundary**: build top-down's bands 0-7 keeping many
   alternative row-8 profiles. Build bottom-up's bands 14-8 keeping many
   alternative row-9 profiles. For each pair, check match.

3. **Forward-look in top-down**: when solving band 7 (top-down), prune
   row-8 profiles incompatible with ANY known bottom-up row-9 profile.

## Status

`obstruction-characterized` — symmetric failure is a fundamental property
of greedy chain. The "meet in the middle" approach is the next move.

## Linked

- [[j1-band-14-failure-analysis]] (top-down side)
- [[j1-column-dp-design]]
- [[j1-multi-band-beam-search]]
