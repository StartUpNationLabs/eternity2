---
name: w2-sp-empirical-result
description: "W2 SP-Lagrangian for E2: NEGATIVE result on 4×4. SP-style BP with Lagrangian-on-piece-uniqueness fails to converge to balanced piece usage. Min piece marginal stuck at 0, max at 2-3, gap=1.2-1.7 regardless of damping/eta tuning."
metadata:
  type: project
---

# W2 SP-Lagrangian — empirical result

After deriving SP-Lagrangian for E2 (see [[w2-sp-for-e2-derivation]]),
implemented and tested on 4×4 generated puzzle.

## Setup

- 4×4 generated puzzle (size_4_colors_6_92cd6738.csv).
- 16 cells, 24 edges, K=8 (BORDER + 7 interior colors).
- BP-style messages between cell-multi-class variables via color-match factors.
- Lagrangian-on-piece-supply on top: μ_p ← μ_p + η(q_p - 1).

## Result: DOES NOT CONVERGE

| Parameters | Final |q-1|∞ | Final max(q) | Final min(q) |
|------------|-----------------|--------------|--------------|
| damping=0.5, eta=0.3 | 1.25 | 2.25 | 0.00 |
| damping=0.9, eta=0.1 | 1.19 | 2.18 | 0.00 |
| damping=0.7, eta=0.5 | similar | similar | 0.00 |

The gap stays around 1.2-1.7 across 50+ outer iterations. **The dual does
not close.**

## Diagnosis

`min(q) = 0` is the smoking gun. It means **at least one piece has
zero probability across all cells**. The Lagrangian update cannot fix this
because: if BP says P(piece p anywhere) = 0, then any μ_p value gives
q_p = 0 (you can't multiply zero by exp(-μ) to get 1).

**Why is BP setting some pieces to zero?**

E2 has many pieces. For random configurations, many pieces are simply
incompatible with the cells' borders + adjacency constraints when seen
through BP's local approximation. BP can be over-confident in ruling out
piece assignments.

This is the same reason BP on E2 only gave 18.84% reduction (vol-12) —
BP misses the global structure.

## Why W1 PEPS-Lagrangian succeeds where W2 SP-Lagrangian fails

W1 uses **exact (or chi-truncated) tensor contraction** for the inner step.
That's exponentially more accurate than BP message-passing.

W2 SP uses BP messages, which are 1st-order approximations to the marginals.
The Lagrangian dual works only when the inner step gives reasonable marginals.
On structured-constraint problems like E2, BP gives biased marginals that
zero out feasible pieces.

## Implications

- **W2 SP-Lagrangian as posed is unworkable** on E2.
- **Pure SP (without Lagrangian)** might still be useful — but only as a
  value-order heuristic. It probably wouldn't beat BP's 18.84%.
- **Hybrid: PEPS-marginals → CSP value-order** remains the most promising
  message-passing-style path.

## Salvaging the work

The SP code itself isn't wasted — it can serve as:
1. **Comparison baseline** for any future SP variant.
2. **Foundation for backtracking-SP (bSP) implementation**, which adds
   conflict-driven backtracking on top of SP.
3. **Component in W3 hybrid pipelines** (different inner solver).

## SECOND TRY: plain BP (no Lagrangian) for value-order

After refuting SP-Lagrangian, retried with mu=0 (just plain BP).

**RESULT: BP converges in 21 iter (10 ms) on 4×4 with reasonable beliefs.**

Sample beliefs:
- Cell (0,0) corner: top 3 = (piece 7 rot 0, 0.386), (piece 4 rot 0, 0.386), (piece 6 rot 3, 0.228)
- Cell (0,2): top candidate 0.614 — high confidence
- Convergence: max change < 1e-4 after 21 iter

This is useful as a **CSP value-order heuristic**! The beliefs give per-cell
piece-rotation probabilities. Vol-12 BP gave 18.84% reduction; this is likely
similar but more efficient (multi-class messages instead of bit-level).

**Followup work**: extract these beliefs as JSON and feed to CSP backtracker
as value-order. Compare against vanilla and vol-12 BP value-order on canonical
16×16.

## Conclusion

W2 SP-Lagrangian is **refuted as a direct E2 solver**. The Lagrangian
trick works for tensor-network methods (W1) but NOT for BP-based methods
because BP itself is too lossy on E2's structured constraints.

**Move on**: W3 Vandermonde-LP is the next candidate (algebraic, different
relaxation). W1 PEPS-Lagrangian remains the leading candidate.

## Linked

- [[w2-sp-for-e2-derivation]] (the derivation)
- [[w1-peps-design-derivation]] (compare/contrast)
- [[bp-marginals]] (vol-11/12 BP measurements)
- [[edge-bp-measurement]] (vol-12 18.84% reduction)
