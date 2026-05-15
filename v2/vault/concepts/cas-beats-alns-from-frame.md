# CAS beats ALNS when starting from a perfect frame — vol-77 (2026-05-15)

**Status**: `built` — vol-77 (2026-05-15).
**Note**: Surprising result.

## Test

Pin each of 10 enumerated 60/60 frames + run continuation:
- **CAS** (vol-76): solve shells 1-7 sequentially via MIP. 25-45s/frame.
- **ALNS** (vol-77): standard alns_only winning5, 60s/frame, seed=1.

## Result

| frame | CAS score | ALNS score | Δ (CAS − ALNS) |
|---|---|---|---|
| 0 | 436 | (n/a) | — |
| 1 | 434 | 393 | +41 |
| 10 | 430 | 391 | +39 |
| 11 | 434 | 385 | +49 |
| 12 | 430 | 387 | +43 |
| 13 | 432 | 398 | +34 |
| 14 | 431 | 393 | +38 |
| 15 | 432 | 390 | +42 |
| 16 | 435 | 394 | +41 |
| 17 | (n/a) | 392 | — |

CAS wins every comparison by **+34 to +49 points**.

## Why this is surprising

ALNS is the proven workhorse — it reaches 459 in our standard
pipeline. CAS is a new invented algorithm that we tested today.
Naïvely, ALNS should perform well from any starting point.

But ALNS-from-bare-frame plateaus at 385-398 in 60s. CAS systematically
fills shells via MIP and reaches 430-436.

## Interpretation

ALNS reaches 459 NOT by starting from a clean frame, but by JOINTLY
EVOLVING frame + interior. The standard ALNS pipeline:
1. CP places 175-200 cells (not necessarily a perfect frame)
2. ALNS swaps pieces across the whole board

When forced to start with a "perfect" frame (60/60 matched) and
empty interior, ALNS can't construct a coherent interior in 60s.
Its destroy-and-repair operators expect a complete board to mutate.

CAS, in contrast, BUILDS the interior shell-by-shell via MIP — exactly
the constructive task it's designed for.

## Implication

**Different algorithms are best for different starting states.**

- Cold start (empty board): vanilla_path + ALNS works (reaches 459)
- Warm partial (200/256 placed): ALNS-only works
- Perfect frame + empty interior: CAS works (430-436)
- Top-14-rows of McGavin pinned: ALNS works (reconstructs 469)

The PIPELINE composition matters. Choosing the right algorithm
for the current state matters.

## What CAS DOESN'T win

- CAS-greedy ceiling is 436, vs ALNS pipeline's 459. So CAS isn't a
  record-breaker; it's the right tool for "from frame" subproblems.

## Linked

- vault/concepts/cas-frame-final.md (CAS-greedy from 20 frames)
- vault/concepts/cas-hybrid-refutation.md (CAS-prefix + ALNS-suffix)
- vault/concepts/concentric-annular-solving.md (CAS spec)
