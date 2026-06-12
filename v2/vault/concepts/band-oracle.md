---
name: band-oracle
description: "Vol-216 PoC (user-directed): coupled 2-row break-tolerant transfer profile of interior rows 12-13 (all edges breakable, clue hints pinned in-band, per-prefix pool + real rim). VALIDATED on pre-registered gate + 257-prefix sweep: trio gate passed decisively (seed63 soft 5.82 / floor 7 vs twins 1.3-2.5 / floors 8-9); rho(resid, max-finish)=0.300, rho(resid, MEDIAN)=0.297 (3x the LP's median signal); star #2/75 combined. 1.4 s/prefix. First deliverable of the staged count-guided construction program."
status: built
metadata:
  type: concept
---

# Band-4 oracle (coupled 2-row break profile)

**Origin**: vol-216 PoC, user-directed ("ask 'is there a 4×16 I can
build next' between stages"). The inter-stage oracle of
`staged-count-guided-construction`, instantiated at the boundary that
matters most: the bottom band, where perfect completion is nonexistent
and ~all of the ~28-break budget is paid.

**Files**: `scripts/v216_bandoracle/band_oracle.py`;
`output/vol-216/lp_scoring_*/band_scores.tsv` (all 257 banked
prefixes scored).

## Definition

For a prefix's remaining pool: transfer DP over columns of interior
rows 12-13 with state $(e_{12}, e_{13}, b)$ — east colors of both rows
plus breaks paid. ALL edges break-tolerant (vertical in-column,
horizontal between columns via the exact/marginal/total
decomposition, W/E/S rim targets); the clue pieces FORCED at (12,1)
and (12,12) pin colors mid-band. Repeats-allowed (relaxation; a
ranking feature, not an honest count — see
[[fugacity-corrected-counts]] for the count program). Output:
$N_b$ = number of band fillings paying exactly $b$ breaks, b ≤ 10.
Pre-registered primary score: $\log\sum_b N_b\,\gamma^b$, γ=0.3.
Cost: **1.4 s/prefix** (pure Python; trivially optimizable).

## Validation (vol-216, same protocol as [[assignment-lp-prefix-scoring]])

**Gate (pre-registered, d146 trio)** — PASSED, decisively:

| prefix (300s finish) | soft score | band break floor |
|---|---|---|
| seed63 (451) | **5.82** | **7** |
| seed36 (447) | 2.46 | 8 |
| seed24 (447) | 1.34 | 9 |

**Population (n=75 homogeneous ≥300s set)**:
- ρ(depth-resid soft, max-finish) = **0.300** (LP: 0.335)
- ρ(depth-resid soft, **median**-finish) = **0.297** (LP: 0.115 — the
  band oracle reads TYPICAL finish 3× better than the LP)
- ρ(−break-floor, max) = 0.277; star ranks #2/75 combined, #5 band-only
- top-quartile enrichment for max≥450: 5/18 = 28% vs 13% base (~2.1×)
- ρ(band resid, LP resid) = **0.644** — the two instruments share most
  of their signal (one underlying pool-health factor, two lenses);
  combined rank-sum ρ = 0.346, only +0.011 over LP alone.

## Reading

1. Second independent confirmation that GLOBAL static signals see
   prefix quality (after the triple-null killed local ones).
2. The band oracle's median-finish signal (0.297 vs LP's 0.115)
   makes it arguably the better LADDER rung-0: it predicts what a
   prefix TYPICALLY does, not its lottery tail.
3. The 0.644 inter-instrument correlation says both measure one
   latent factor — adding more global lenses has diminishing returns;
   the next grade up requires the honest count
   ([[fugacity-corrected-counts]] MPS scale-up) or empirical racing.
4. Interpretable side product: the break FLOOR (bmin) is a per-prefix
   lower-bound-flavored difficulty certificate for the bottom band
   (relaxed, repeats-allowed, so a true bound only in the relaxation).

## Adoption + open

- Wire as LADDER rung-0 alongside/instead of the LP (band oracle
  preferred on median-signal grounds; compute both, they're cheap).
- Extend to the band-2→3 boundary oracle ("how many perfect band-3s
  does this stage-2 choice admit?") — the second informative boundary.
- 3-row coupled version (17³ states) for sharper floors.
- Fugacity correction to turn counts honest (subset case needs the
  conditioned term first).

## Linked

[[assignment-lp-prefix-scoring]], [[fugacity-corrected-counts]],
[[ladder-prefix-racing]], session [[vol-216]]
