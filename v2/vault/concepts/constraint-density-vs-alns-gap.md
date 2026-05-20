---
name: constraint-density-vs-alns-gap
description: For a puzzle with $P$ pieces and color set $\{0, 1, ..., K\}$, the
status: built
metadata:
  type: concept
---
# Constraint Density vs ALNS Gap (V132, 2026-05-19)

**Status**: `built`
**Origin**: Vol-132 post-McGavin pivot
**Files**:
- `scripts/v132_constraint_density.py`
- `scripts/v132_density_table.py`
- `output/vol-131/density_comparison.json`

## Definition

For a puzzle with $P$ pieces and color set $\{0, 1, ..., K\}$, the
**random-placement match probability** is

$$
p_{\text{match}} = \sum_{C \ne 0} P(C)^2
$$

where $P(C) = \frac{|\{(p, r, s) : \text{edges}[p, r, s] = C\}|}{4PR}$
is the marginal probability of color $C$ at a uniformly-random
piece-rotation-side. The expected matched-edges count under
random placement (ignoring piece-uniqueness) is then
$E[\text{matched}] = n_{\text{interior}} \cdot p_{\text{match}}$.

The **ALNS gap** is the difference between actual solver score
percentage and the random-placement baseline.

## Measured table

| Puzzle | pieces | colors | int_edges | $p_{\text{match}}$ | $E[\%]$ random | ALNS % | gap |
|--------|--------|--------|-----------|-----|------|------|------|
| canonical 16×16/22 | 256 | 23 | 480 | **0.0423** | 4.2% | 96.0% | **+91.8** |
| 6×6/c4   | 36  | 5  | 60  | 0.1806 | 18.1% | 100.0% | +81.9 |
| 7×7/c5   | 49  | 6  | 84  | 0.1506 | 15.1% | 97.6% | +82.5 |
| 8×8/c6   | 64  | 7  | 112 | 0.1338 | 13.4% | 92.9% | +79.5 |
| 10×10/c8 | 100 | 9  | 180 | 0.1060 | 10.6% | 91.1% | +80.5 |
| 12×12/c10 | 144 | 11 | 264 | 0.0859 | 8.6% | 86.4% | +77.8 |
| 14×14/c12 | 196 | 13 | 364 | 0.0733 | 7.3% | 81.6% | +74.3 |

## Three findings

### 1. ALNS gap is REMARKABLY STABLE

Across 7 puzzles spanning $36 \to 256$ pieces and $5 \to 23$ colors,
the gap (ALNS% − random%) stays in the band **[74, 92]**, with most
values near 80. ALNS reliably extracts ~80 percentage points above
the random baseline regardless of puzzle size or constraint density.

### 2. Canonical 16×16/22 is the OUTLIER on density

Canonical's $p_{\text{match}} = 0.0423$ is **6× LOWER** than 6×6/c4's
0.1806. Despite having more pieces than any generated suite member,
canonical has the LOWEST random-match probability because of its
22-color palette: each piece-side has ~22 different candidates.

### 3. Canonical has the LARGEST gap (+91.8)

The canonical 461/480 record extracts +91.8 percentage points above
its random baseline. This is the highest gap in our suite — meaning
ALNS does the most "work" relative to randomness on canonical. It's
NOT that canonical is easy; it's that random placement is especially
bad on canonical (color is so sparse that few edges match by chance),
making ALNS' lift look proportionally larger.

## Implications

- The "ALNS plateau" isn't a fixed % wall; it's `random_% + ~80`.
- If we want to find a puzzle where ALNS struggles, we should look
  for one where **random% + 80 > 100%** — i.e., $p_{\text{match}} >
  0.2$. None of our suite hit this, but a 5×5/c3 generated puzzle
  would: $p_{\text{match}} \approx 1/3 \cdot$ for 3 colors.
- Conversely, the canonical's score gap above random is the gap that
  ALNS needs to close to reach 480. **At 461, ALNS is 19 edges short
  of perfect**, but already 91.8 percentage points above random.

## What's still open

- Compute a per-piece adjacency-graph density: for each color $C$,
  the bipartite-matching density between $E$-side carriers and
  $W$-side carriers. This is the tight constraint that LP relaxes.
- Predict community-board scores from density alone. Are the 18
  basin families clustered by density?
- Run ALNS with a CONSTANT budget (not 60s) on each puzzle and
  measure the wall TIME rather than score.

## Linked

- [[scaling-curve-2026-05-19]]
- [[plans/MONTH_AHEAD_2026-05-19]]
