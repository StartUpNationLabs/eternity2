# V179 — LARGE-K PriorDestroy Variants

Status: `built` — variants integrated; tested as part of 3-basin iso-plateau analysis. No record lift but informative negative result.
Origin: vol-179.
Files: `crates/localsearch/src/alns.rs::PriorDestroy` (variants `prior_huge_b1.0_k32`, `prior_huge_b4.0_k48`).

## Motivation

V169 OPHIDIA PriorDestroy supports $k \leq 16$. If the escape from a 460 basin
requires a coherent disturbance of 30+ cells, $k=16$ is too small to even initiate
the escape. V179 adds larger $k$ variants.

## Variants

| Variant | $\beta$ | $k$ |
|---|---|---|
| prior_huge_b1.0_k32 | 1.0 | 32 |
| prior_huge_b4.0_k48 | 4.0 | 48 |

These extend the V169 portfolio:

- prior_escape_b0.5_k16 (V169)
- prior_escape_b2.0_k12 (V169)
- prior_attract_b-1.0_k8 (V169)

## Empirical result

In the [[three-basin-iso-plateau]] test:

- Adaptive ALNS picks LARGE-K variants in ~10% of destroys (comparable to small-k variants).
- All three basins (cp=(1,0,3,2)/(3,0,1,2)/(0,3,1,2)) unchanged after 30min.
- LARGE-K alone is insufficient to escape.

## Why LARGE-K doesn't escape

Even with $k=48$, the repair operator (Hungarian / bipartite matching) finds the
best legal completion given the destroyed cells and remaining edge constraints.
On the iso-460 manifold, the best repair is the original board itself — or a
score-equivalent permutation that ALNS accepts under SA but doesn't lift.

The escape mechanism that's missing isn't bigger destroys; it's a destroy
operator that **violates** local matching to force a structurally different
basin during the repair, with a longer recovery phase to rebuild score.

## What's open

- Pair LARGE-K with **non-matching repair** (random fill + local search).
- Multi-phase ALNS: destroy → degrade-tolerate iterations → re-tighten.
- $k > 64$ — not tested due to repair feasibility concerns.

## Linked concepts

- [[prior-guided-alns]] (V169 OPHIDIA, parent)
- [[three-basin-iso-plateau]]
