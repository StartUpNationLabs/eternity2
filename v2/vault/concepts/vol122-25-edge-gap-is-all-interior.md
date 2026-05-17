---
name: vol122-25-edge-gap-is-all-interior
description: "Vol-122 K7 — DECOMPOSITION of McGavin 469 vs perm0 444 = 60BB + 55IB + 354II (McGavin) vs 60BB + 55IB + 329II (perm0). The 25-edge gap is ENTIRELY in interior-interior."
metadata:
  type: project
---

# Vol-122 K7 — Where is the 469-vs-444 gap?

## Method

Decompose every board's score into 3 categories:
- **BB**: border-border adjacencies (60 total).
- **IB**: interior-boundary adjacencies (= interior piece's outward-facing edge matching adjacent border piece's inward color, 56 total).
- **II**: interior-interior adjacencies (within the 14×14 interior, 364 total).

Total = BB + IB + II ≤ 480.

## Result

| Board | BB | IB | II | Total |
|---|---|---|---|---|
| McGavin (469) | 60/60 | 55/56 | **354/364** | **469** |
| perm0 (444) | 60/60 | 55/56 | **329/364** | **444** |

**The 25-edge gap is ENTIRELY in interior-interior matches.**

Both boards have:
- Same border (60/60 BB).
- Same interior-boundary score (55/56 IB) — 1 mismatch each (different one).
- 96.5% identical boundary color distribution (multiset-equal by construction).

The only meaningful difference: McGavin's 196 interior pieces are
arranged so 354/364 interior edges match. Ours arrange them so only
329/364 match. **The 25-edge gap is a pure interior-tiling-quality
gap, decoupled from border/boundary.**

## Implication

If we ran ALNS only on the INTERIOR cells (freezing the border), and
gave it enough compute, could we reach 354/364 II? That's a sub-question
we can actually test:

1. Use J5 (interior-only ALNS with --extra-hint pinning the border).
2. Compare convergence to a 354-II achievement.

Even without J5: the 4 perm0 ALNS basic 30min jobs currently running
(PIDs 56196-56199) effectively do this — the border is hint-pinned.

## Math view

The 14×14 interior has **364 internal adjacencies** (13 × 14 horizontal
+ 14 × 13 vertical = 182 + 182).
- LP-UB for this sub-problem given boundary = 364 (Vol-122 B3 LP gave
  perm0 lp_interior=364, see border_lp_ub on bf-bw partials).
- McGavin achieves 354 (= LP-UB - 10).
- We achieve 329 (= LP-UB - 35).

**McGavin's integrality gap is 10; ours is 35.** A 25-edge potential
improvement exists IF the interior arrangement is the right one.

## Open question

**Is the interior structurally rigid GIVEN the boundary, or is there a
better arrangement that our ALNS can't find?** Cannot answer without
running interior-only MIP on perm0's boundary. That's a follow-up
experiment.

## Status

`finding-localizing` — pinpoints WHERE the gap is. Doesn't yet close it.

## Linked

- [[../sessions/vol-122]]
- [[../concepts/vol122-border-structure-analysis]]
- [[../concepts/vol122-mcgavin-border-our-stack-435]]
- vol-122 B3 per-border interior LP-UB
