---
name: inv-b4-hall-color-pair-refuted
description: "Vol-122 INVENTION B4 — color-pair Hall-condition LP. Refined vol-44's color-UB=480 by adding per-side rotation choice. LP optimum = 480.0; integer MIP optimum = 480.0. Hall does NOT tighten."
metadata:
  type: project
---

# INVENTION B4 — Hall-condition refuted (vol-122)

## Method

LP/MIP with binary rotation choice per piece, continuous y_k_h / y_k_v for per-color horizontal/vertical match budget, constrained by min over opposite-side supplies. Geometric caps: total horizontal ≤ 240, total vertical ≤ 240.

## Result

- LP optimum: **480.00**.
- MIP optimum (integer rotation): **480.00**.
- Per-color: each k achieves exactly floor(N_k/2) at optimum.

## Interpretation

Rotation flexibility is fully sufficient: for every color k, there exists a piece-rotation assignment that puts color-k edges on the required opposite sides to fully use floor(N_k/2) instances. The Hall-condition does NOT tighten vol-44's 480.

## What this rules out

The "side-imbalance" hypothesis: vol-44's bound is loose because some piece-rotations put too many color-k edges on the wrong side. **Refuted.**

## What this leaves open

Vol-44's UB-478 comes from per-cell-pair geometric constraints. B4 with just side-bipartite balance gives 480. So:

- B4 (side-bipartite Hall): 480
- Vol-44 (per-cell-pair LP): 478
- Gap from 478 to true integer optimum ≤ McGavin's 469 = 9 edges

## Future directions

- 3-cell column Hall (intra-piece constraints)
- Color-triple supply (corner-adjacent contiguous segments)

## Linked

- [[lp-ub-478-basins]]
- [[../plans/INVENTIONS_BACKLOG]]
- [[../sessions/vol-122]]
