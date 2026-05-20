---
name: w2-sp-for-e2-derivation
description: "Derivation: Survey Propagation adapted for E2's structured factor graph. SP was designed for random k-SAT; E2's factors are STRUCTURED (color matching, piece-uniqueness, hint pins). Derives the message-passing equations and identifies where the structure helps vs. hurts."
metadata:
  type: project
status: partial
---

# W2 — Survey Propagation for Eternity II (derivation)

User goal (vol-123): find **the way** to solve the puzzle, not just records.

Survey Propagation (SP), introduced by Braunstein-Mézard-Zecchina (2002),
solves random k-SAT instances near the SAT/UNSAT threshold where ALL OTHER
ALGORITHMS FAIL. It's not a heuristic — it's a statistical-mechanics-derived
exact (modulo approximation) algorithm that exploits the cluster structure
of the solution space.

This document derives SP for E2's structured factor graph and identifies
where SP can succeed.

## Background: SP on random k-SAT

For random k-SAT with N variables and M clauses, SP works on the factor
graph where variables $x_i \in \{0, 1\}$ are linked to clauses $a$. Each
edge $(i, a)$ carries a survey $\eta_{a \to i} \in [0, 1]$ representing
"probability that clause $a$ sends a *warning* to $i$ telling it to take
the satisfying value".

The SP update equations (Braunstein 2002):

$$\eta_{a \to i} = \prod_{j \in a \setminus i} \frac{\Pi_{j \to a}^{u, [a]}}{\Pi_{j \to a}^{u, [a]} + \Pi_{j \to a}^{s, [a]} + \Pi_{j \to a}^{0, [a]}}$$

where the $\Pi$'s aggregate warnings from other clauses connected to $j$
on the "unsatisfied" (u), "satisfied" (s), and "no-warning" (0) sides.

Decimation: after SP converges, the variable with the most-biased marginal
is fixed; SP rerun on the reduced graph.

## E2's factor graph (different from random k-SAT)

For E2, the variables and factors are STRUCTURED:

### Variables

Two natural choices:
1. **Per-cell variable** $x_c$ with domain `{(p, r) : valid (p, r) for cell c}`.
   For canonical 16×16: 256 cells × ~256 piece-rotations per interior cell
   ≈ 65000 raw (cell, piece-rot) bool variables; or 256 multi-class variables.

2. **Per-piece-rotation-cell boolean** $y_{c,p,r}$ as in Ansótegui-Sellmann-Tabar SAT.
   For canonical: 256 × 256 × 4 = 262144 boolean variables.

We'll use choice 1 (multi-class) for cleaner factor graph.

### Factors

1. **Cell exactly-one**: ✓ automatic if variables are multi-class.
2. **Piece exactly-one** $F_p$: $\sum_c \mathbb{1}[\pi(x_c) = p] = 1$. Spans all
   cells — **NON-LOCAL**, a critical issue (see below).
3. **Color match** $F_{e}$ for interior edge $e = (c_a, s_a, c_b, s_b)$:
   $\text{color}(x_{c_a}, s_a) = \text{color}(x_{c_b}, s_b)$. Local (2-variable).
4. **Hint pins** $F_h$: $x_{c_h} = (p_h, r_h)$. Unary.

## The non-locality challenge

Standard SP assumes factors involve a **bounded** number of variables. The
piece-uniqueness factor $F_p$ involves $O(\text{n\_cells})$ variables —
non-local. This is the same obstruction as vol-13 boundary-MPS.

**Workaround (same as W1 PEPS-Lagrangian)**:
  Drop the explicit piece-uniqueness factor; replace with a Lagrangian
  on per-piece supply, learned iteratively.

So **W2 SP-Lagrangian** would be:
  1. Run SP on the relaxed factor graph (cell + match + hint only).
  2. SP converges to per-cell marginals over (piece, rotation).
  3. Compute expected piece-usage $\langle q_p \rangle$.
  4. Update Lagrangian multipliers $\mu_p$ on per-piece supply.
  5. Iterate until $\langle q_p \rangle = 1$ for all $p$.

This is symmetric to W1 PEPS-Lagrangian but uses SP instead of tensor-network
contraction for the inner computation.

## SP message-passing equations for E2

**Factor-to-variable** (color-match factor $F_e$ to cell $c_a$):
For each candidate value $(p, r)$ at cell $c_a$:
$$\eta_{F_e \to c_a}[(p, r)] = \sum_{(p', r')} \mathbb{1}[\text{color}(p, r, s_a) = \text{color}(p', r', s_b)]
                              \cdot \chi_{c_b \to F_e}[(p', r')]$$

where $\chi$ is the variable-to-factor message.

**Variable-to-factor** (cell $c_a$ to match factor $F_e$):
$$\chi_{c_a \to F_e}[(p, r)] = \prod_{e' \ne e \text{ incident to } c_a}
                                \eta_{F_{e'} \to c_a}[(p, r)]
                                \cdot e^{-\mu_p}$$

The $e^{-\mu_p}$ term is the Lagrangian on per-piece supply. The dual
multiplier $\mu_p$ enforces $\langle \mathbb{1}[\pi(x_c) = p] \rangle$
summed over cells = 1.

## SP vs BP for E2

Belief Propagation (BP) for E2 was measured in vol-11/12:
- 18.84% interior reduction (vol-12 edge-BP).
- BP "saw" the local color-matching structure but missed piece-uniqueness.

SP differs from BP by passing **surveys** (probabilities of warnings) rather
than marginals. SP handles **frustration**: in random k-SAT near threshold,
many constraints are "almost satisfied" simultaneously, and SP correctly
identifies which constraints to fix first.

**For E2**, the question is whether the SP equations converge:
- BP on E2 converged (vol-11/12), so local structure is BP-friendly.
- SP generalizes BP by aggregating over **clusters of solutions**. For E2,
  cluster structure exists (vols 18-22 cooperativity, vols 65-99 σ-orbits).
- **SP may give STRONGER marginals** than BP because it accounts for the
  cluster correlation that BP averages over.

## Computational cost

- Factor graph: ~256 multi-class variables + 480 match factors + 5 hints.
- Each factor-to-variable message: per cell value (~256-1024), sum over
  neighbor's compatible values (~256-1024). Per message: ~256² = ~65k ops.
- Total messages per SP iter: 480 factors × 2 cells × 1024 values = ~1M ops.
- Times ~100 iter to converge: ~$10^8$ ops. **Trivial in seconds.**

So **SP is MUCH cheaper than W1 PEPS**. If SP gives good enough marginals,
it's a winning candidate.

## What could go wrong

1. **SP may not converge** on E2's structured graph. Random k-SAT has
   provable convergence near threshold; E2 has no such guarantee.

2. **Lagrangian dual may not converge.** Same risk as W1.

3. **Marginals may not be informative.** If most cells have near-uniform
   marginals after SP, no useful value-order signal.

## Plan

1. **Phase 1 (1-2 days)**: implement SP-Lagrangian for E2.
   - Adapt thibsej/SurveyPropagation message-passing core.
   - Build E2 factor graph (script started: `scripts/w2_sp/sp_e2.py`).
   - Test on 4×4 generated puzzle.

2. **Phase 2 (1-2 days)**: validate on 6×6 generated puzzle.
   - Compare marginals to W1 PEPS marginals (both at chi=128).
   - If SP marginals correlate with W1's, then SP is much faster path to
     same information.

3. **Phase 3 (2-3 days)**: scale to canonical 16×16.
   - SP scales linearly in n_factors, so 16×16 is feasible on laptop.

4. **Phase 4 (1 day)**: feed SP marginals as CSP value-order.
   - Compare against BP baseline (vol-12: 18.84%) on canonical.
   - If SP gives >50% reduction, we have a CLEAR path to solve.

## Why SP is the most promising

- W1 (PEPS): correct but needs cloud-scale compute for canonical.
- W2 (SP): **canonical-scale runs trivially on laptop** if it converges.
- W3 (Vandermonde-LP): smaller relaxation, untested on E2 entirely.

The cost-benefit is in W2's favor IF SP converges on E2. The next session
should prioritize building W2.

## References

- Braunstein, Mézard, Zecchina. *Survey propagation: An algorithm for
  satisfiability*. Random Structures & Algorithms 27(2):201-226 (2005).
  https://arxiv.org/abs/cs/0212002
- Marino, Parisi, Ricci-Tersenghi. *The backtracking survey propagation
  algorithm for solving random K-SAT problems*. Nature Comms 7:12996 (2016).
- thibsej/SurveyPropagation Python reference implementation.

## Linked

- [[bp-marginals]] (vol-11 BP)
- [[edge-bp-measurement]] (vol-12 18.84% reduction)
- [[w1-peps-design-derivation]] (parallel Lagrangian-relaxation strategy)
- [[web-roam-2026-05-17]] (W2 entry)
- [[SOLVING-E2-VISION]] (strategic doc)
