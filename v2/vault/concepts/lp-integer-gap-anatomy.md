# Anatomy of the LP-integer gap on vol-32 458 board

**Status**: math analysis, no new code shipped.
**Origin**: vol-50 (2026-05-15), while waiting on blackwood_raw+MRV 1h.
**Source data**: `output/vol-44_border_lp_ub/per_color_458.log`.

## The gap

vol-32 458 board, class-A border:
- LP UB: 478 (= 60 BB + 54.04 BI + 363.96 II)
- Integer best: 458 (= 60 BB + 52 BI + 346 II)
- BB gap: 0 (LP=integer, both 60)
- BI gap: 2.04 (LP=54.04, integer=52)
- **II gap: 17.96** ≈ 18 (LP=363.96, integer=346)

Where is the 18-point II gap localised?

## Per-color II LP-UB on the 458 board

| Color | LP UB | Integer best (need data) | Fractional part |
|---:|---:|---:|---:|
| 1-5 (rare) | 0.00 | 0 | 0.00 |
| 6 | 19.94 | ? | 0.94 |
| 7 | 19.00 | ? | 0.00 |
| 8 | 20.89 | ? | 0.89 |
| 9 | 20.87 | ? | 0.87 |
| 10 | 22.83 | ? | 0.83 |
| 11 | 23.62 | ? | 0.62 |
| 12 | 23.00 | ? | 0.00 |
| 13 | 22.00 | ? | 0.00 |
| 14 | 21.15 | ? | 0.15 |
| 15 | 19.00 | ? | 0.00 |
| 16 | 20.94 | ? | 0.94 |
| 17 | 23.00 | ? | 0.00 |
| 18 | 22.24 | ? | 0.24 |
| 19 | 19.00 | ? | 0.00 |
| 20 | 21.48 | ? | 0.48 |
| 21 | 22.00 | ? | 0.00 |
| 22 | 23.00 | ? | 0.00 |
| **Sum** | **363.96** | **346** | **5.96** |

## Two contributions to the gap

1. **Fractional LP**: sum of fractional parts = 5.96. Could potentially
   be tightened by rounding cuts.
2. **Integer-rounding loss**: 18.0 - 5.96 = **12.04** is LP-integer-valued
   per color but NOT jointly achievable in the integer optimum.

**This is the surprising part**: 67% of the LP-integer gap is in
*per-color LP-values that are integer*. The LP says e.g. "color 7
can match 19 times, color 12 can match 23 times, color 13 can match 22
times" — these are integer claims, but they cannot all be true
simultaneously because they require piece-rotation arrangements that
conflict.

## Implication for cut generation

Traditional LP cuts (Gomory, MIR, lift-and-project on y) target the
**fractional part**. They could close 5.96 / 18 = 33% of the gap at
most. Even closing 100% of the fractional gap leaves 12 of the 18
points uncloseable by y-cuts.

**The binding constraint is x-piece-uniqueness, not y-edge-matching.**
The relaxation `y = min(a_left, b_right)` is tight per-edge, but the
underlying `x` (piece assignments to cells with rotations) is fractional.

## What this rules out

- Single-cut Gomory rounds on y: insufficient.
- Per-color LP tightening: insufficient.
- Naive lifted-LP (McCormick on x products): vol-47 refuted as
  intractable at canonical scale.

## What this MIGHT enable

1. **Column-generation with per-piece subproblems**: generate
   placements per-piece. Master problem enforces uniqueness
   exactly; pricing problem is per-piece assignment LP. Decomposition
   structure may make this tractable where monolithic lifted-LP wasn't.
   Multi-week build.

2. **Block-decomposed MIP**: solve MIP exactly on small piece-blocks
   (e.g. 16 pieces at a time) and combine via constraint propagation.
   Less LP-theoretic, more solver-engineering.

3. **Exact joint bound via SAT/MaxSAT** with piece-uniqueness as hard
   constraints. The MaxSAT route was BACKLOG'd ([[exact-joint-bound]])
   but considered intractable at 16×16.

## Open question — needs measurement

The "integer best" column above is UNKNOWN per-color. The LP gave
us per-color UB; the integer best per-color (sum = 346 known) is
distributed somehow. Knowing this distribution would tell us:
- Which colors are jointly-infeasible at LP UB (those with biggest
  LP-int gap per color).
- Whether the gap is concentrated on 1-2 colors or spread evenly.

To compute: enumerate matched edges per-color in the integer 458 board.
Fast (Python script over the placement JSON). Worth doing for vol-51.

## Linked
- [[lp-ub-478-basins]] — basin class data
- [[lp-ub-479-basin-found]] — class D
- [[458-class-A-mismatch-structure]] — cluster geometry
- [[lifted-lp-formulation]] — vol-47 attempt
- [[exact-joint-bound]] — kissat path (wont-do)
- [[per-color-lp-ub-458]] — the existing measurement that this analyses
