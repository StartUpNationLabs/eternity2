---
name: j1-band-14-failure-analysis
description: "J1 chain fails at band 14 (rows 14, 15) due to color-constraint incompatibility between row 14's committed bottom edges and the remaining bottom-border pieces. Supply is correct (2 corners + 14 edges remaining); colors don't match."
metadata:
  type: project
status: refuted
---

# J1 — Band 14 failure analysis

## Empirical fact

J1 single-chain on canonical 16×16 completes bands 0-13, fails at band 14.
At band 14 (rows 14, 15):

- Available pieces: 16 (2 corners + 14 edges + 0 interior).
- Required pieces for band 14:
  - Row 14 (interior row): 14 interior + 2 edge pieces (cols 0, 15).
  - Row 15 (bottom border): 14 edge + 2 corner pieces.

**But all 196 interior pieces are already used** in rows 0-13. So row 14
has NO interior pieces available. Row 14 needs 14 INTERIOR pieces at cols
1-14, but we have only edges and corners left.

## Root cause

The chain commits rows 0-13 using all 196 interior pieces. By construction
this is over-greedy: it doesn't reserve interior pieces for row 14.

## Math

Total interior pieces: $196 = 14 \times 14$.
Interior cells: 14 rows × 14 cols = 196.

Distribution by row:
- Rows 0, 15: 0 interior pieces (border row).
- Rows 1-14: 14 interior pieces per row (cols 1-14).

Total interior pieces required: $14 \times 14 = 196$. ✓ exactly matches supply.

In the chain, band $r$ uses rows $r, r+1$. Interior pieces used per band:
- Band 0 (rows 0, 1): only row 1 has interior cells (14 pieces).
- Band $r$ for $r \in [1, 13]$: rows $r, r+1$ both have interior cells (28 pieces).
- Band 14 (rows 14, 15): only row 14 has interior cells (14 pieces).

Sequential cumulative interior used after band $r$:
- $r = 0$: 14
- $r = 1$: 14 + 14 = 28 (row 2 added)
- $r = k$ for $k = 2..13$: $14 + 14k = 14(k+1)$ interior pieces used (rows 1..k+1)
- After band 13: $14 \times 14 = 196$ interior pieces used. ✓

So after band 13 (rows 13, 14), ALL interior pieces are exhausted. Band 14
adds row 15 which is BORDER, no interior pieces needed. So **supply-wise the
chain CAN complete band 14** if row 14 was correctly committed.

**Wait, I miscounted.** Let me redo:

- Band 0 covers rows (0, 1). Row 1 has 14 interior cells.
- Band 13 covers rows (13, 14). Row 14 has 14 interior cells.

After band 13, used interior = 14 × 14 = 196. ✓

Band 14 covers rows (14, 15). Row 14 was already done in band 13. Row 15 is
border, needs 14 edges + 2 corners.

So band 14 just adds row 15 — but my script treats it as a 2-row band with
fixed top (= row 14) and free bottom (= row 15).

The failure at band 14 = no feasible row-15 (16 pieces) given row 14's
specific color profile.

## Why row 15 fails

Row 15 is bottom-border. Each piece at (15, c) must have BORDER color (0)
on its BOTTOM edge. The bottom-border-compatible pieces are:
- 2 corners at cols 0, 15 (BL, BR shape).
- 14 edges at cols 1-14 (bottom-border edge shape).

The remaining 16 pieces are exactly these 2 + 14 = 16 pieces with correct
border-side profiles.

The constraint that fails: each (15, c) piece's TOP edge must match row 14's
BOTTOM edge at col c. The chain committed row 14's bottom edges (via the
specific pieces chosen), and the remaining pieces' TOP edges don't match
this color sequence.

## The fundamental problem

The greedy chain optimizes one band at a time. Band $r$'s solver maximizes
its own 46 edges, choosing colors that may be incompatible with what row $r+1$
will eventually need.

**Specifically**: band 13 commits row 14's BOTTOM edges. These must match
the TOP edges of row 15's bottom-border pieces. But the chain didn't see
this constraint when committing band 13.

## Fix directions

1. **Forward-look constraint**: when solving band $r$, only allow row-$r+1$
   bottom colors that match SOME bottom-border piece's top color. This
   prunes infeasible branches early.

2. **Bottom-row-first**: solve row 15 FIRST (place bottom-border pieces in
   a valid configuration), then chain upward from row 15 to row 0.

3. **Multi-direction**: solve in BOTH directions and meet in the middle.

4. **Increase chain_K significantly**: try thousands of band-13 alternatives
   to find one whose row-14-bottom is compatible with available row-15 pieces.

## Insight

J1 is fundamentally a HEURISTIC GREEDY decomposition. The greedy band-by-band
choice leaks the "what row 15 needs" constraint. Adding that forward-look
should let the chain complete.

## Status

`obstruction-characterized` — partial mathematically. Fix #1 (forward-look)
is the highest-EV next step.

## Linked

- [[j1-column-dp-design]]
- [[j1-chain-band-decomposition-math]]
- [[j1-multi-band-beam-search]]
