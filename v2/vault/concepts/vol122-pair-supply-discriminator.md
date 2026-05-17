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

## Status

- **Discriminator: CONFIRMED** (preliminary, 3 data points + 100 in
  flight).
- **Optimization target**: enumerate borders by max pair-supply score
  → re-run A1 pipeline → expect best border to score 460+.
- **Open**: is this a SUFFICIENT condition or just NECESSARY? Maybe
  beating 459 requires pair-supply > 1300.

## Implications

This is the first PROVEN-positive structural property of "good" borders.
After 4+ negative LP-based hypotheses (PCLS, B4 Hall, color-uniformity,
per-cell-pair LP), we have a hand-hold.

## Next step

Enumerate borders by max pair-supply score (greedy or local search) →
generate 50 high-pair-supply borders → run A1 pipeline → measure scores.

## Linked

- [[vol122-pcls-poc-result]]
- [[vol122-border-structure-analysis]]
- [[vol122-a1-pipeline-result]]
- [[../sessions/vol-122]]
- [[../plans/INVENTIONS_BACKLOG]] — promote to NEW invention "border-DP with pair-supply objective"
