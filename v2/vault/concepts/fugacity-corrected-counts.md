---
name: fugacity-corrected-counts
description: "Vol-216 (user-directed): grand-canonical fugacity correction for the piece-distinctness overcount in transfer/MPS counts (the vol-209 10^101 wall). Sinkhorn-style saddle z_p <- z_p/u_p enforcing E[usage]=1, log N ~ log Z(z*) - sum log z*. VALIDATED on ground-truth bands (equal case): naive error grows with size (0.30 -> 0.78 log10 at 8 -> 15 cells), corrected error <= 0.002 throughout. Subset case (pool > cells) needs a conditioned correction — Poissonization over-corrects (documented negative)."
status: partial
metadata:
  type: concept
---

# Fugacity-corrected transfer counts

**Origin**: vol-216, user-directed during the multi-dimensional-methods
Q&A. The statistical-mechanics route around the wall that stopped
[[isentrope-entropy-growth]]'s boundary-MPS from counting REAL
completions: transfer formalisms let pieces repeat (10^101 overcount
at board scale, the "boundary-MPS null").

**Files**: `scripts/v216_transfer/fugacity.py` (Band: exact DFS
ground truth, weighted transfer DP with forward-backward usage
marginals, Sinkhorn saddle iteration).

## Method

Grand-canonical relaxation: weight piece $p$ by fugacity $z_p$ in the
transfer DP, giving $Z(z) = \sum_{\text{configs}} \prod_p z_p^{n_p}$
over repeats-allowed configs. For the CANONICAL case (#cells = #pool,
each piece used exactly once — i.e. the endgame counting problem),
the mean-field/saddle estimate of the distinct-pieces count is

$$\log N \approx \min_{z>0}\Big[\log Z(z) - \sum_p \log z_p\Big]$$

solved by damped generalized-Sinkhorn iteration
$z_p \leftarrow z_p / u_p(z)$ where $u_p = z_p\,\partial \log Z /
\partial z_p$ = expected usage (computed by forward-backward over
column states). Convex in $\log z$.

## Validation (ground truth = exact DFS on real-board bands)

Bands cut from the vol-215 452 board's PERFECT region (rows 4-6, true
boundary, pool = exactly the board's pieces there):

| cells | exact | naive log10 err | **fugacity log10 err** |
|---|---|---|---|
| 8 (2×4) | 2 | +0.301 | **+0.001** |
| 10-14 (2×5..7) | 2 | 0 (pinned) | 0.000 |
| 12 (3×4) | 1 | +0.301 | **+0.001** |
| 15 (3×5) | 1 | +0.778 | **+0.002** |

★ Naive error GROWS with region size; corrected error stays ~0.
(Bands from rows 12-13 have exact count 0 — no perfect filling exists
where the board pays its breaks; the count detects this correctly.)

## Vol-218 ground-truth validation (equal case, b-graded)

10×10 testbed, b\*-graded ladder, exact distinct counts as truth
(56 rungs, 8 instances): gap recovery **98%/91%/86% at b\*=2/3/4**
(naive ×150 → corrected ×1.1 at b\*=2), decaying to **53%/43% at
b\*=5/6** with saddle pathologies (one over-correction to 0, one
non-convergence). ★ Structural limit found: the correction is
FIRST-MOMENT only — **exchange-symmetric overcounting (piece-swap
cycles) has uniform usage marginals and is invisible to fugacities**
(measured at b\*=0: naive=corrected, exact ×2 lower). The vol-216
validations were usage-asymmetric cases. Consequence: the 16×16
corrected-floor gate (vol-218 prereg S1) is deferred on measured
grounds — recovery trend unpromising at b≈44 and finite-difference
saddles infeasible at NC=23 (adjoint build = the open alternate).
Data: `output/vol-218/fugladder_*.tsv`; code: `weighted_profile` /
`fugacity_corrected_lncount` in `bench-audit/src/mini.rs`,
`fugacity_lab --seed N` (ladder mode).

## Documented negative: the subset case

Pool > cells (e.g. 18 pieces, 10 cells): uniform-usage targets
diverge (unused pieces shouldn't have uniform fractional usage), and
the z=1 Poissonization correction $\sum_p[\log(1+u_p)-u_p]$
OVER-corrects by 0.7-1.5 log10 — usages are negatively correlated by
the fixed cell count, violating Poisson independence. Needs the
total-count-conditioned (second-order / Gaussian) term. Open.

## Why this matters (the prize)

The theoretically-correct prefix score per [[isentrope-entropy-growth]]
is log-#completions — the quantity the triple-null says no local
statistic sees and vol-209 couldn't count honestly. Equal-case
fugacity + χ-truncated MPS at width 14 would estimate it for REAL
prefixes (the remaining 50-cell region IS the equal case). Path:
1. extend ground-truth validation to ~20 cells (bitmask transfer DP);
2. fugacity weights inside the width-14 boundary-MPS (χ-truncation +
   saddle — watch vol-210's χ-artifact lesson: convergence checks
   pre-registered);
3. score the d146 trio + the 75-prefix labeled set; compare against
   [[assignment-lp-prefix-scoring]] (bound) — this would be a COUNT.

## Linked

[[isentrope-entropy-growth]], [[assignment-lp-prefix-scoring]],
[[piece-tensor-spectroscopy]], session [[vol-216]]
