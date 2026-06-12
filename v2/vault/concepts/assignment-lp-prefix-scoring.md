---
name: assignment-lp-prefix-scoring
description: "Vol-216: assignment-LP with edge terms over the remaining pool scores LADDER prefixes. THE GLOBAL LENS THE TRIPLE-NULL NEVER TESTED — and the first static signal that survives: the 451-producer outranks its 446-twins (gate passed + empirically controlled), pop-level rho ~ 0.34 vs >=300s finishes. Pre-filter grade, not oracle grade."
status: built
metadata:
  type: concept
---

# Assignment-LP prefix scoring

**Origin**: vol-216 (2026-06-12), binding 2 — the direct answer to the
vol-215 [[ladder-prefix-racing]] triple-null ("prefix quality is an
emergent GLOBAL property"). The LP couples the ENTIRE remaining pool
through the assignment polytope + per-edge match variables — the first
scorer in this project that is global by construction.

**Files**: `scripts/v216_lp/lp_prefix_score.py` (HiGHS),
`scripts/v216_lp/harvest_finishes.py` (label harvester),
`output/vol-216/lp_scoring_*/{labels,scores}.tsv`.

## Definition

For a pinned perfect prefix on the bordered+hinted 14×14 interior:

$$\max \sum_{c,j} w_{cj}\, x_{cj} + \sum_{e,k} y_{ek}$$

- $x_{cj} \in [0,1]$: empty cell $c$ takes piece-rotation $j$ from the
  remaining pool; $\sum_j x_{cj}=1$ per cell, $\sum_{c,r} x_{c(p,r)}=1$
  per piece (the assignment polytope).
- $w_{cj}$ = matches against FIXED sides (placed prefix neighbors, rim
  targets, forced hints).
- For each empty-empty edge $e=(c,c')$ and color $k$:
  $y_{ek} \le \sum_{j:\,\text{side}=k} x_{cj}$ (both endpoints);
  $\sum_k y_{ek} \le 1$ holds automatically since side-color masses
  sum to 1.

LP optimum = **sound UB** on completable II+IB from the prefix.
`ub_total = fixed + lp_obj + BB(60)`. Solver note: HiGHS **IPM**
(0.7-0.9 s); dual simplex needs 35 s on this degenerate polytope
(same objective to 6 decimals).

## What we measured (vol-216)

**Pre-registered gate (d146 trio, identical depth ⇒ identical fixed
term 302, hand-verified):**

| prefix | finish (300 s × 8, identical config) | lp_obj |
|---|---|---|
| d146-seed63 | **450/451/451** | **104.245** |
| d146-seed24 | 446/447/448 (fresh control) | 102.142 |
| d146-seed36 | 446/447/448 (fresh control, n=7) | 102.568 |

GATE PASSED + empirically controlled same-day: LP ordering = finish
ordering. The twins had never been raced ≥300 s before; they stay
in-band.

**Population (257 banked prefixes scored, 3 frames):**
- vs 30-s rung-2 labels: NULL (median within-group ρ ≈ 0.01) — those
  labels are noise-dominated (the star itself reads 447 at 60 s).
- vs ≥300-s finishes, homogeneous ladder.sh config (n=75):
  **ρ(depth-residualized ub_total, max-finish) = 0.335 (p ≈ 0.003)**,
  consistent per frame (0.42 / 0.30 / 0.28); ρ vs median = 0.115 (ns).
- The star ranks **#2/75**; top-quartile enrichment for max≥450
  prefixes ≈ 2× base rate; one clear miss (a med-450 gen0143 prefix
  ranks 55/75).
- Depth trend: ub_total ≈ 509.6 − 0.309·depth — cross-depth ranking
  REQUIRES residualizing on depth.

## Verdict + adoption

**Signal confirmed at pre-filter grade.** The triple-null does NOT
extend to global relaxations — exactly the [[isentrope-entropy-growth]]
prediction (the discriminating information is global distinctness).
But ρ ≈ 0.34 is not an oracle: adoption is **LADDER rung-0** — LP
pre-rank the banked pool (≈1 s/prefix), then race the top-k
empirically. Racing stays the promoter; LP buys a cheaper, wider
funnel. NOT valid as sole promoter.

## Open

- Sharper features from the same LP: per-cell margins, fractionality
  mass, dual prices on piece constraints (starved pieces?).
- LP-guided probe steering (maximize LP of the NEXT placement) — a
  global value-order; cost per node is the obstacle (0.7 s).
- Tail-region LP as admissible bound inside exact endgames — see
  [[exact-region-growth]] (binding 3 uses Hungarian on static costs;
  the LP with edge terms is the next-stronger rung).

## Linked

[[ladder-prefix-racing]], [[isentrope-entropy-growth]],
[[exact-region-growth]], session [[vol-216]]
