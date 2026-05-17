---
name: vol122-pair-supply-discriminator
description: "Vol-122 FINDING: consecutive-color-pair supply score discriminates McGavin (469) from our borders (424-439). Pair-supply correlates with ALNS-final-score. New optimization target for border enumeration."
metadata:
  type: project
---

# Vol-122 — pair-supply score discriminates border quality

## Setup

For each ordered color pair (c1, c2), count interior-piece-rotations where
the piece has c1 on one side and c2 on the next clockwise side.

For a border, compute **consecutive pair-supply score**: sum over the 56
border-interior-facing colors' consecutive pairs (c_i, c_{i+1}) cyclically
of `pair_supply[(c1, c2)] + pair_supply[(c2, c1)]` (both orderings).

## Result

| Border | ALNS score (30min basic seed 42) | Pair-supply score |
|---|---|---|
| perm0 | 424 | 1116 |
| perm3 | 439 | 1020 |
| **McGavin** | **469** | **1316** |
| mc_b002 (gen) | ? | 1144 (best of mcgavin-perm-100) |
| mc_b006 (gen) | ? | 1104 (worst of mcgavin-perm-100) |

McGavin's pair-supply is **15-30% higher** than any other border tested.
The pair-supply score CORRELATES with the eventual ALNS score, where
prior LP-style discriminators (per-color supply, per-cell-pair LP UB,
color-gap uniformity) did NOT.

## Why this discriminator likely works

The LP-UB sees adjacencies in isolation: "color c1 here is feasible iff
some piece can provide c1 on the facing side". But ACTUAL placement
requires that the piece *also* present compatible colors on its OTHER
sides — for the neighboring cells. The pair-supply captures this:
"how many pieces can present c1 on side S AND c2 on side S+1".

If a border forces consecutive colors (c1, c2) that few interior pieces
can L-shape match, that border is structurally harder. McGavin's
specific permutation puts colors in an order that maximizes interior
L-shape compatibility.

## Refinement (later same day) — DEMOTES the discriminator

A REFINED pair-supply was computed: for each adjacent border-facing pair
(c1, c2), count *pairs of interior pieces* (p1, p2) where p1 in some
rotation shows c1 on top, p2 in some rotation shows c2 on top, AND
p1.right_color == p2.left_color (shared interior-interior edge match).

Results:

| Border | Raw pair-supply | Refined pair-supply | ALNS score |
|---|---|---|---|
| perm0 | 1116 | 6718 | 424 |
| perm3 | 1020 | 6728 | 439 |
| McGavin | 1316 | 6586 | 469 (others); 435 (our stack) |

**The REFINED metric REVERSES the correlation**. McGavin has the LOWEST
refined supply (6586), perm3 the HIGHEST (6728).

Combined with the finding that **McGavin's border + our stack = 435**
(see [[vol122-mcgavin-border-our-stack-435]]), this DEMOTES the
pair-supply hypothesis: the raw correlation was likely coincidence.

## Status

`refined-and-demoted` — raw pair-supply was coincidence; the real
bottleneck is search algorithm, not border choice.

## Linked

- [[vol122-pcls-poc-result]]
- [[vol122-border-structure-analysis]]
- [[vol122-a1-pipeline-result]]
- [[../sessions/vol-122]]
- [[../plans/INVENTIONS_BACKLOG]] — promote to NEW invention "border-DP with pair-supply objective"
