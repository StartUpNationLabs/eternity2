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

## Vol-54 measurement — integer per-color column FILLED

Built `bin/per_color_integer.rs` and measured on vol-32 458 board:

| color | LP_UB  | INT |  Δ_to_LP |
|------:|------:|----:|---------:|
|     6 |19.9419|  19 |   0.9419 |
|     7 |19.0000|  18 |   1.0000 |
|     8 |20.8874|  21 |  -0.1126 |
|     9 |20.8686|  20 |   0.8686 |
|    10 |22.8289|  22 |   0.8289 |
|    11 |23.6234|  22 |   1.6234 |
|    12 |23.0000|  22 |   1.0000 |
|    13 |22.0000|  21 |   1.0000 |
|    14 |21.1476|  20 |   1.1476 |
|    15 |19.0000|  17 |   2.0000 |
|    16 |20.9401|  20 |   0.9401 |
|    17 |23.0000|  22 |   1.0000 |
|    18 |22.2440|  20 |   2.2440 |
|    19 |19.0000|  19 |   0.0000 |
|    20 |21.4818|  20 |   1.4818 |
|    21 |22.0000|  22 |   0.0000 |
|    22 |23.0000|  21 |   2.0000 |
| **Σ** |363.96 | 346 |  17.9637 |

**Note color 8: INT=21 > floor(LP_UB)=20.** The LP allocates 20.88 to
color 8 at its joint optimum; integer achieves 21. This proves
**`floor(LP_UB[k])` is NOT a per-color integer upper bound** — it's
just where the LP joint optimum happened to land for that color.

### Interpretation correction (vol-54)

The "12 points integer-rounding loss" framing in this page is
numerically correct (5.96 fractional + 12 rounding = 17.96 ≈ 18) but
**conceptually misleading**.

The 12 isn't "loss from piece-uniqueness joint-infeasibility". It's
"the LP allocates colors differently than integer can replicate" —
specifically, the LP exploits cell-fractional x to lift y, while
integer x is forced to commit each piece to one cell.

See [[y-linearisation-cell-fractional-gap]] for the precise gap
mechanism (minimal worked example: 2 cells, 2 pieces, LP=1.0,
integer=0). Vol-53's intuition was right but worded loosely;
vol-54 made it tight.

### What the table now tells us

- Color 15 and color 18 carry the largest integer-LP gaps (2 each).
  Worth checking their geometric distribution in future work (which
  cells, are they clustered, etc.).
- Color 8's INT > LP shows LP UB is not a per-color isolated bound;
  joint reallocation can let a color exceed its solo LP attainability.

## Linked
- [[lp-ub-478-basins]] — basin class data
- [[lp-ub-479-basin-found]] — class D
- [[458-class-A-mismatch-structure]] — cluster geometry
- [[lifted-lp-formulation]] — vol-47 attempt
- [[exact-joint-bound]] — kissat path (wont-do)
- [[per-color-lp-ub-458]] — the existing measurement that this analyses
- [[y-linearisation-cell-fractional-gap]] — **vol-54 successor: precise mechanism**
- [[../sessions/vol-54]] — vol-54 session producing this table
