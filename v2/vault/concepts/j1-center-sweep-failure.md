---
name: j1-center-sweep-failure
description: "J1 center-out sweep FAILED at center band 7 in 130s with beam=5000. Center band has NO border constraints, so state space is too large for the beam to navigate."
metadata:
  type: project
---

# J1 — Center-Sweep failure

## Result

Center band 7 (rows 7, 8 — interior rows with NO border on top/bottom)
failed to complete with beam=5000 and 120s budget. Failed mid-column.

## Why center is HARDER than boundary bands

Boundary band 0 (rows 0, 1):
- Row 0: top edge MUST be BORDER (0) → only border pieces eligible.
- Reduces row-0 piece options from 4 × 256 = 1024 placements to ~64.

Interior band 7 (rows 7, 8):
- Both rows have NO border constraint.
- All 196 interior pieces × 4 rotations = 784 row-0 options.
- Combined (top, bottom) pairs = 196 × 195 × 4 × 4 / 2 ≈ 153 000 per column.

The constraint reduction at borders makes border-anchored bands tractable
with beam=5000. Interior bands have ~12× more candidate placements per
column and the beam can't keep up.

## Math estimate

For interior band, transitions per state per column $\sim O(P_t \cdot P_b)$
where $P_t, P_b$ are piece-option counts for top/bot rows.

Border band: $P_t \approx 64$ (only edge/corner pieces), $P_b \approx 700$
(interior + edge with right border profile). Combined per state: ~45k.

Interior band: $P_t \approx 700$ (interior pieces, no border), $P_b \approx 700$.
Combined per state: ~490k.

Ratio: 10-11×. Beam=5000 sees ~50% of feasible space on borders, ~5% on
interior — likely missing feasible paths to col 15.

## Solutions

1. **Larger beam for center**: try beam=50000 or 100000 on center band.
2. **Don't start from the center**: stick with border-anchored chains,
   accept the symmetric failure pattern.
3. **Hybrid**: solve corners first (rows 0, 15 with tight border constraints),
   then expand inward.
4. **Smart center band**: use a different objective for the center band —
   not just max-score but also "max compatibility with constraints from
   future expansion" (forward-look).

## Status

`refuted-as-naive` — naive center-out doesn't work with default beam.
Larger beam or smarter algorithm needed.

## Linked

- [[j1-bidirectional-symmetric-failure]]
- [[j1-column-dp-design]]
