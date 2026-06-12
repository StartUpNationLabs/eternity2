---
name: constraint-immediacy-principle
description: "Vol-216 synthesis (user Q&A): total constraint volume is PATH-INVARIANT (sum of per-cell constraint counts = #edges for every visit order); a path only chooses WHEN each constraint binds. Search efficiency = immediacy: minimize the distance between a decision and its refutation. Explains hint-link (51/480), spiral (204), seam (-3..-5) vs row-major (433) and border-first (445) with one principle; locates all remaining leverage in INFORMATIONAL early binding (req propagation, priors, pool restrictions, computed gates)."
status: built
metadata:
  type: concept
---

# The constraint-immediacy principle

**Origin**: vol-216 Q&A synthesis (user asked whether hint-link paths
"restrict the puzzle earlier" and whether that should reduce search
space). Unifies vol-14/36 path refutations, vol-213 seam results, the
spiral closure-tax refutation, and the border-first win.

## The invariance

For any complete visit order, let $k_i$ = number of already-decided
constraints cell $i$ faces when placed. Every board edge is checked
exactly once (by whichever endpoint is placed second), so

$$\sum_i k_i = \#\text{edges} = \text{const (path-invariant)}.$$

Loosely, total tree volume ~ $\prod_i (\text{pool}\cdot p^{k_i})$
depends on $\sum k_i$ — so no path "adds restriction". A path only
schedules WHEN restriction binds.

## The principle

**Search efficiency = immediacy of testing**: the cost of a wrong
decision is the size of the subtree explored before its refutation
surfaces. Paths with under-constrained stretches (k=1 corridors,
~35-50 candidates, untested) followed by over-constrained closures
(k≥3, where the corridor's errors finally surface) are *fail-last* —
maximally expensive. Uniform k=2 (row-major/boustro) keeps the
decision-to-refutation distance ≈ 0.

## Evidence (all measured in this project)

| path | shape | result |
|---|---|---|
| hint-link (vol-36) | k=1 corridors + k≥3 pockets | 51/480 (8× worse than row-major) |
| outer-spiral | closure everywhere | 204/480 |
| seam two-front (vol-213) | k=3-4 meeting band | −3..−5 vs row-major |
| row-major | uniform k=2 | 433/480 |
| border-first (vol-36) | most-constrained subpool FIRST, binds immediately | **445/480** |

Border-first is the proof that "restrict early" is right WHEN the
restriction tests decisions immediately; hint-link is the proof that
geometric earliness without immediacy is worse than nothing.

## Corollary — where the remaining leverage lives

Geometry is maxed out at k=2-uniform (you cannot have high-k cells
without first laying low-k ones — the conservation law). All further
early binding must be INFORMATIONAL:
- req back-propagation (hints bind approaching cells — built),
- pool restrictions (Verhaard quotas — built, marginal),
- priors (REPLAY — built),
- computed gate schedules ([[actuary-markov-optimizer]] — in progress),
- global evaluation at the root ([[assignment-lp-prefix-scoring]],
  [[fugacity-corrected-counts]]).

This is the same conclusion the triple-null forced from the
statistics side: the puzzle yields nothing to local geometric
cleverness; everything further is information positioning.

## Linked

[[scan-order]], [[ladder-prefix-racing]], [[replay-prior-over-cost]],
session [[vol-216]], [[vol-213]]
