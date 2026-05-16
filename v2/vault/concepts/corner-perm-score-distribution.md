---
name: corner-perm-score-distribution
description: Across 1156 stored canonical E2 boards, max scores by corner permutation. McGavin's (3,2,0,1) is the ONLY perm reaching 469. Other perms cap at 462 or below. Suggests corner permutation may partly determine achievable max score.
metadata:
  type: project
---

# Corner-permutation × max-score distribution (vol-99 finding)

**Status**: `built` — measured 2026-05-16 ~04:20 from corpus survey.

## Method

Surveyed all `output/**/*.json` board files in v2 with a score field
in [440, 480]. Extracted corner permutation (pieces at positions
0, 15, 240, 255) for each. Computed max score per permutation.

1156 boards found.

## Results — top 15 corner permutations

| permutation (pos 0,15,240,255) | max score | # boards |
|---|---:|---:|
| **(3, 2, 0, 1)** | **469** (McGavin) | 54 |
| (2, 3, 0, 1) | 462 | 53 |
| (1, 0, 2, 3) | 459 (local) | 34 |
| (0, 3, 1, 2) | 458 (vol-32) | 130 |
| (2, 0, 1, 3) | 458 | 86 |
| (2, 3, 1, 0) | 458 | 63 |
| (0, 3, 2, 1) | 457 | 96 |
| (2, 1, 0, 3) | 457 | 80 |
| (0, 2, 1, 3) | 457 | 73 |
| (1, 0, 3, 2) | 457 | 30 |
| (2, 0, 3, 1) | 457 | 50 |
| (3, 0, 1, 2) | 457 | 45 |
| (3, 0, 2, 1) | 457 | 90 |
| (1, 3, 0, 2) | 457 | 38 |
| (3, 1, 2, 0) | 457 | 44 |

## Key observations

1. **Only McGavin's perm (3,2,0,1) reaches 469.** No other
   permutation in our corpus exceeds 462.
2. Second-best perm (2,3,0,1) has max 462 across 53 boards —
   well-explored, real ceiling.
3. Local 459's perm (1,0,2,3) has 34 boards, all maxing at 459.
4. The most-explored perm is (0,3,1,2) with 130 boards, all
   maxing at 458 (vol-32 basin family).

## Score-by-permutation pattern

Plotting max score vs # boards explored shows:
- Perm (3,2,0,1): 54 boards → 469 max (highest)
- Perms with 50-100 boards → typically 457-462 max
- Perms with < 30 boards → 454-458 max (under-explored)

**This suggests two interpretations**:

(A) **Permutation-dependent ceiling**: Different perms have
    intrinsically different score ceilings. (3,2,0,1) is specially
    suited to 469. This would mean we should ALWAYS use
    (3,2,0,1) for record-attempts.

(B) **Search-amount-dependent**: With more search compute, every
    perm could reach similar max. (3,2,0,1) is just the perm where
    McGavin's algorithm landed.

## What would distinguish (A) from (B)

Run a 50+ board ALNS lottery on a single non-(3,2,0,1) perm and
see if it reaches > 462. If yes → (B). If consistently capped
below 462 even with 100+ boards → (A).

The vol-32 perm (0,3,1,2) at 130 boards capped at 458 already
HINTS at (A) — but (3,2,0,1) at only 54 boards still reached 469,
which doesn't fit (A) cleanly either (would expect (3,2,0,1) max
to be even higher with more search).

**Most likely combined**: the corner-perm landscape has bimodal
basin distribution where (3,2,0,1) hosts a basin family reaching
469 that other perms simply DON'T host.

## Implication for record-breaking

- Future record attempts on canonical E2 should **start with corner
  permutation (3,2,0,1)** — McGavin's choice.
- Other perms appear to cap at 458-462 even with significant
  exploration (130 boards in vol-32 perm hit 458 ceiling).

## Linked

- [[basin-corner-permutations]]
- [[mcgavin-mip-local-optimal-halo1]]
- [[why-records-are-mip-rigid]]
