# CONCORD — Veit Elser's Difference Map for E2

**Status**: `partial` (Vol-126 — PoC built, not yet working as designed)
**Origin**: Brainstorm reservoir
[[plans/EXTERNAL_BRAINSTORM_2026-05-18]] (round 4), Vol-126 build,
2026-05-19.
**Files**:
- `scripts/v126_concord_poc.py` — Python PoC
- `crates/bench-audit/src/bin/gen_small_csv.rs` — tiny puzzle generator
  for PoC validation

## Definition

Given two constraint sets $A, B \subseteq \mathbb{R}^d$ with projections
$P_A, P_B$, the difference-map iteration is

$$
x_{n+1} = x_n + \beta \bigl[ P_A\bigl(2 P_B(x_n) - x_n\bigr) - P_B(x_n) \bigr].
$$

Fixed point ⇔ $P_A(P_B(x)) = P_B(x) = x_\star \in A \cap B$ (a solution).

The map is *not a descent method* — it routinely moves uphill. This
gives it the power to escape local optima.

## E2 instantiation

State $x \in \mathbb{R}^{N \times P \times R}$ where:
- $N = 256$ cells
- $P = 256$ pieces
- $R = 4$ rotations

Interpret $x[c, p, r]$ as a soft assignment of piece $p$ at cell $c$
with rotation $r$.

### Set A (piece-uniqueness)

Each piece is assigned to exactly one cell.

**Projection $P_A$**: Linear-assignment problem (LAP) on score
$s[c, p] = \sum_r x[c, p, r]$. Output is a permutation $\sigma$ and
per-cell rotation distribution.

### Set B (edge-consistency)

Adjacent cells' shared edges have matching colors.

**Projection $P_B$**: Soft message-passing / BP-style update: for each
cell $c$, compute marginal color distribution at each of its 4 sides;
for each adjacent pair $(i, j, s_i, s_j)$ the target color
distribution at the boundary is the average of cell $i$'s $s_i$
distribution and cell $j$'s $s_j$ distribution. Iterate 3 inner steps.

## V126 PoC results (2026-05-19)

**Setup**: 16×16 canonical E2, 100 difference-map iterations,
$\beta = 0.5$, random init.

| metric                 | observed                  |
|------------------------|---------------------------|
| Best matched          | 125 / 480 (26%)            |
| Mean iter time         | 0.4 s                      |
| Update norm           | ~4.05 (constant)           |
| Convergence           | NO (oscillating)           |

**5×5 generated puzzle** (40 interior edges, expected 40 if solved):

| metric                 | observed                  |
|------------------------|---------------------------|
| Best matched          | 17 / 40 (42%)              |
| Convergence           | NO — locks at 17, oscillates |

## What works

- The iteration mechanically updates `x` and never crashes.
- LAP-based $P_A$ runs ~50 ms per call on 256-piece state.
- BP-style $P_B$ runs ~350 ms per call (3 inner iters × per-side
  color marginal computation).

## What does NOT work yet

- The PoC immediately reaches a low-quality fixed point and stays
  there. This is the classic "DM stuck in a basin" failure mode.
- The 5×5 test case (which our backtracker solves trivially) plateaus
  at 17/40, FAR below solution. This means **either** $P_A$ and $P_B$
  are not correctly capturing the constraints, **or** the
  initialization is in a region where DM dynamics are degenerate.

## Hypotheses for failure

1. **Hard one-hot states cause trivial dynamics**. When $P_B$ outputs
   a one-hot per cell and $P_A$ outputs a one-hot per cell, and the
   two are consistent, `pa - pb = 0` and the update vanishes. CONCORD
   PoC needs *continuous* state at one of the projections —
   probably $P_A$ should use a softer LAP-relaxation (e.g. Sinkhorn).
2. **$\beta$ tuning**. Elser's papers suggest $\beta \in [0.5, 1.0]$;
   we only tested 0.5 and 1.0.
3. **Initialization**. We initialize with $\mathrm{Uniform}(0, 1)$.
   Structured noise (e.g. small biased perturbation off a heuristic
   seed) may help.
4. **$P_B$ inner iteration depth**. 3 BP-inner steps may not converge.

## Refutation status

NOT REFUTED. Only the simplest version was tested over 100 iterations.
A proper test requires:
- Sinkhorn-relaxed $P_A$ (continuous LAP).
- $\beta$ sweep $\{0.3, 0.5, 0.7, 1.0\}$.
- Initialization from a bf_bw partial (not random).
- 1000-5000 iterations.
- 8×8/8 puzzle (mid-size testbed) as primary instance.

## What's still open

- **Sinkhorn $P_A$**: replace hard LAP with iterative Sinkhorn doubly-
  stochastic normalization. Continuous output.
- **Bregman-style $P_B$**: variational projection onto edge-consistency
  via mirror-descent (preserve the simplex structure).
- **Hybrid DM**: occasional cold-restart kicks when update_norm
  stagnates.
- **Sub-board PoC**: 4×4 with our backtracker solving it exactly,
  CONCORD must recover the same answer.

## Why this is worth coming back to

Difference-map cracked Sudoku, sphere packing, protein folding, bit
retrieval. The original brainstorm flagged it as the **single most
likely cluster-wall breaker** in the ~25-idea reservoir. Author's
top-1.

Failure of a naive PoC is not refutation; it's the standard
"first-try" outcome for DM. The math is well-established; the
*implementation discipline* matters.

## Vol-126 close (this volume)

Per [[feedback_e2_one_invention_per_volume]], vol-126 is CONCORD-only.
We BUILT the scaffolding (Python PoC, small-puzzle generator, LAP +
BP-style projections, iteration loop). We have NOT validated CONCORD
breaks 461.

Status set to `partial`. Next vol (vol-127) opens on CONCRETION per
priority; CONCORD work resumes in a later vol with the listed
"what's still open" upgrades.

## Linked

- [[plans/EXTERNAL_BRAINSTORM_2026-05-18]]
- [[fpl-frozen-pair-lifting]]
- [[sessions/vol-126]]
