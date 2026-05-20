---
name: v186-color-conservation
description: 1. Pool-availability: which pieces remain after the top consumes 8 rows.
status: unbuilt
metadata:
  type: concept
---
# V186-T4 — Color-Conservation Co-Designed Top+Bottom

Status: `unbuilt` — math design, not yet PoC'd.
Origin: vol-186 (after V186-T3 pool-bias refutation isolated layer-2 wall).

## The two-layer obstruction (recap)

The bidirectional LIGHTHOUSE wall has 2 layers:

1. **Pool-availability**: which pieces remain after the top consumes 8 rows.
   Pool-bias (V186-T3) fixes this measurably — uses 1 of 31 β-rich pieces.
2. **Edge-chain feasibility**: even with pool fixed, row-12/13/14 S-edge
   chains are unsatisfiable. This is the actual wall.

V186-T3 refuted pool-bias as a *sole* fix. Layer 2 is what blocks.

## What makes the edge-chain unsatisfiable?

In the bottom-up direction:

- Row 15 has S = BORDER, N = some 16-color sequence $\nu_{15}$.
- Row 14 needs S = $\nu_{15}$ (matching row 15's N).
- Row 14's pieces are picked greedily under N-constraint; their N-edges
  form a new 16-color sequence $\nu_{14}$, used by row 13's S.
- By row 13, $\nu_{13}$ is the cumulative result of three greedy chain-DP
  steps, each making locally optimal choices but globally over-constraining
  the residual pool.

The wall = "no chain in the remaining pool can match the demanded
S-edges at row 12".

## Color-conservation principle

Define the **edge-color budget** $C(c)$ = total count of color $c$ across
all 4 edges of all 256 pieces. Each color appears in a fixed quantity.

In any complete placement, each *horizontal* edge in the board interior
uses 2 color-occurrences (one from each piece). The total color-budget for
H-edges across all rows is conserved.

Specifically, for color $c$:

$$
\sum_{r=0}^{14} (\text{count of color } c \text{ in row } r\text{'s S-edge sequence})
= \frac{C(c) - C_{\text{border}}(c) - C_{\text{vertical}}(c)}{2}
$$

(Conservation rule: H-edges live as pairs, one from each piece.)

This gives a **per-color quota** for each row's S-edge sequence: row $r$'s
S-edge sequence uses some number $q_r(c)$ of color $c$, and
$\sum_r q_r(c)$ is fixed by the puzzle.

## Co-design: budget-aware bidirectional search

The wall happens because top-down greedily uses up too much of some
color quota in the top 8 rows, leaving the bottom insufficient.

**Algorithm**:

1. Pre-compute color budgets $C(c)$ from the puzzle.
2. Define **expected per-row budget**:
   $$
   q^\star_r(c) = \frac{C(c) - C_{\text{border}}}{15} \quad \text{(15 H-edge rows)}
   $$
3. Augment the top-down beam ranker with a quota-deviation penalty:
   $$
   R'(b) = R(b) - \delta \sum_{r=0}^{r_\text{current}} \sum_c \big|q_r(c) - q^\star_r(c)\big|
   $$
4. Symmetrically bias the bottom-up beam.

This forces both halves to use color budgets at the expected rate,
leaving compatible quotas for the un-built middle rows.

## Why this attacks layer 2

Pool-bias (V186-T3) penalises *piece choice*. Color-conservation
penalises *edge-color consumption*. The wall is about edge colors not
pieces — so this targets the actual constraint.

## Implementation

1. Compute $C(c)$ from puzzle (one-shot, ~256-piece scan).
2. Add `--color-budget-penalty δ` to `build_pool_biased.py`.
3. Track running per-row color usage in BeamState.
4. Sweep δ ∈ {0.1, 0.5, 1.0, 2.0} × γ_top ∈ {0, 1.0}.

## Expected outcome

If color-quota is the layer-2 wall, then $\delta > 0$ should:

- Reduce wall-rate (currently ~100% at row 12–14) to < 80%.
- Allow some merges to produce full boards with score 350–420.

If $\delta$ sweep also walls, the layer-2 problem is deeper — probably
involving **piece-piece adjacency rarity** (rare color-color pairs that
must occur in middle rows), which would need a 2-color graph analysis.

## Linked

- [[v186-pool-biased-top-down]]
- [[lighthouse-bidirectional-row]]
- [[semaphore-row-hungarian]]
- [[rare-color-rule]]
