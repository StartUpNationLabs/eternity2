---
name: lifted-lp-column-generation
description: intractable for HiGHS. Need column generation.
status: unbuilt
metadata:
  type: concept
---
# Lifted LP via column generation (vol-47 refinement)

**Status**: design.
**Origin**: vol-47 naive lifted LP has 5-20M z-vars on canonical-E2,
intractable for HiGHS. Need column generation.

## The size problem

Naive lifting: for each I-I edge × each color-matched (p1, r1, p2, r2)
pair, instantiate $z_{e, p_1, r_1, p_2, r_2}$.

On canonical-E2 16×16/22 with 458 board's border + 5 hints:
- 196 interior cells, ~764 candidates each (191 non-hint pieces × 4 rot).
- 364 I-I edges.
- Per-edge, color-matched pairs: ~14k naive, ~55k worst case.
- Total z-vars: 5–20 million.

HiGHS times out at 60s on 10×10/6 (1.25M z-vars). Canonical is 10×
bigger. **Not solvable in any reasonable time.**

## Column generation

Standard OR technique for huge LPs. **Iterate**:

1. Solve a "small" LP with only x-vars and y-vars (= standard LP).
2. For each $y_{e,k}$ that's fractional (0 < y < 1), the LP can
   potentially be tightened by adding z-vars for that (edge, color).
3. Among the z-vars NOT yet in the LP, add the ones that the dual
   indicates would tighten the bound most (column generation pricing).
4. Re-solve. Loop until either:
   - No more "useful" z-vars to add (LP converged).
   - Time budget exhausted.

The key insight: **most z-vars in the lifted LP have value 0 at
optimum.** Standard LP techniques exploit this by only materializing
columns that have positive reduced cost.

## Pricing rule

For a z-var $z_{e, p_1, r_1, p_2, r_2}$ to be useful, its reduced
cost (∂objective/∂z evaluated at current LP solution) must be
positive. The reduced cost is:

$$\bar{c}_z = 1 - \pi_1 - \pi_2 - \mu$$

where:
- $\pi_1, \pi_2$ are duals of the McCormick UB constraints
  $z \le x_1, z \le x_2$ if they were in the LP.
- $\mu$ is the dual of the per-edge sum constraint $\sum_z \le 1$.

If $\bar{c}_z > 0$, adding $z$ tightens the bound.

**Heuristic**: instead of computing $\bar{c}_z$ exactly (requires
modifying HiGHS), use a proxy:
- A z-var $z_{e, p_1, r_1, p_2, r_2}$ is "promising" if both
  $x_{c_1, p_1, r_1}$ and $x_{c_2, p_2, r_2}$ have fractional
  value > some threshold (e.g., 0.05).

## Implementation plan

1. Solve standard LP. Extract x-var values.
2. For each I-I edge $e$, identify candidates with $x > \epsilon$
   at both endpoints. List ALL color-matched (p1,r1,p2,r2) pairs
   among these candidates.
3. Add only those z-vars (with McCormick) to the LP.
4. Re-solve.
5. Repeat from step 2 until converged or time-out.

## Expected size after pricing

If the standard LP solution has ~5 candidates per cell with x > 0.05
(out of 764), the per-edge z-vars are 5² × 22 ≈ 550 per edge.
Total: 364 × 550 = **200k z-vars**.

That's 100× smaller than naive. HiGHS should handle it in minutes,
not hours.

## Expected outcome

If the column generation converges and finds many positive-reduced-
cost z-vars to add, the lifted LP UB tightens. The question is by
how much.

**Best case**: tightens from 478 → 459 or lower on the vol-32 458
basin. We'd see the true integer-LP gap shrink dramatically.

**Worst case**: only adds 0.1 of tightening per iteration, takes
1000+ iterations to converge. Still gives some signal.

**Realistic expectation**: 2-5 iterations to converge, total bound
drop of 5-10 points (from 478 → 468-473). Still informative.

## Linked

- [[lifted-lp-formulation]] — naive design
- [[border-enum-lp-ub]] — standard LP
- [[lp-ub-478-basins]] — basin survey
