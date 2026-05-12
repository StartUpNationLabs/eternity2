# "Estimated number of solution with and without hints" — topic 103684518 (28 msgs, 2024-01)

## Headline (most important number in the corpus)

McGavin's Brendan Owen complex-theory implementation gives:

- **1-hint canonical E2 (just piece 139)**: estimated **~14,702 solutions**
  (accurate to factor ~2).
- **5-hint canonical E2 (139 + 4 clue pieces)**: estimated **~4×10^-8
  solutions** — i.e., almost certainly **exactly one** solution.

**The 5-hint canonical E2 puzzle is the constructive case where unique
solvability is overwhelmingly likely** (probability ~99.9999999% from
the random-tile-distribution null model).

## The depth-vs-cumulative-solutions table

McGavin posted his C implementation of complex theory using GNU MP. Output
for scan-row from bottom-left with just the mandatory start piece:

| Depth | Solutions at depth | Cumulative |
|------:|------------------:|-----------:|
| 1 (I8, hint) | 1 | 1 |
| 2 (P1) | 4 | 5 |
| 3 (P2) | 44.8 | 49.8 |
| 4 (P3) | 493.37 | 543.17 |
| 5 (P4) | 5340.6 | 5883.8 |
| 6 (P5) | 56,806 | 62,690 |
| 7 (P6) | 5.9×10^5 | 6.56×10^5 |
| 8 (P7) | 6.1×10^6 | 6.74×10^6 |
| 9 (P8) | 6.1×10^7 | 6.8×10^7 |
| 10 (P9) | 6.1×10^8 | 6.7×10^8 |
| 13 (P12) | 5.2×10^11 | 5.8×10^11 |
| 16 (P15) | 3.7×10^14 | 4.2×10^14 |
| 157 (G13) | 5.0×10^45 | 6.3×10^46 |
| 160 (G16) | 1.4×10^45 | 7.5×10^46 |
| 163 (F03) | 6.4×10^45 | 9.5×10^46 |
| 166 (F06) | 4.8×10^45 | 1.1×10^47 |
| 249 (A09) | 2.7×10^8 | **1.37×10^47** |
| 250 (A10) | 4.5×10^7 | 1.37×10^47 |
| 254 (A14) | 65,434 | 1.37×10^47 |
| 255 (A15) | 26,663 | 1.37×10^47 |
| 256 (A16) | **14,702** | **1.37×10^47** |

## Three regimes of E2 difficulty

The cumulative-solutions curve has three clear regimes:

1. **Exponential growth phase, depth 1-50**: solutions multiply geometrically
   from 1 to ~10^28. Each piece placement is essentially unconstrained.
2. **Plateau phase, depth 50-200**: cumulative grows by only ~10^17, but
   individual node count peaks at ~10^45. **This is where backtrackers
   waste 99% of their time** (cf. Joe's "70% at depth >150" empirical
   finding — almost exact match).
3. **Funnel collapse, depth 200-256**: cumulative *stays* at ~10^47 but
   per-depth solutions collapse from 10^45 to 10^4. **The last 60 pieces
   are tightly constrained** — each piece placed eliminates orders of
   magnitude of branches.

**This is the formal model of "the E2 funnel"** — the same shape Hopfer's
"stall 202-206, jump 213, die 218-221" empirically observed, and the
same shape that explains xtal's shell-4 wall.

## What this changes for vol-9 / vol-11

- **The 14,702 estimate is the canonical baseline** for "how rare are
  full E2 solutions" given just the start piece. If we find even one
  solution on the 1-hint variant, that's evidence we're in the
  predicted ~14,702-solution space.
- The **funnel-collapse structure suggests the right algorithm is
  "find any path through the plateau, then chain through the funnel
  deterministically"**. The funnel itself is locally easy; the
  problem is reaching it.
- **All of vol-9's solver runtime should be measured in "did we reach
  depth 200"** — that's the entrance to the funnel. Anything below
  is "still in the plateau."

## Caveat

Complex Theory assumes edges are independently drawn. They're not:
groups of 4 edges are attached to one piece. McGavin's calibration
on smaller puzzles suggests **the estimates are accurate within a
factor of 2** for puzzles where empirical counts are known. For E2,
the 14,702 could plausibly be anywhere from 7,000 to 30,000.

## Dieter von Holten's dual hypothesis (worth recording)

dvh (msg #5) suggests the multi-solution count comes from **"flexible
frames around few valid inner 14×14 squares"** — the border has many
valid arrangements, the interior has fewer; different border-interior
matchings give different solutions. This is testable on smaller
synthetic puzzles. Vol-7's pinned-perimeter saturation at 449-454
is consistent: pinning the border collapses the solution count.
