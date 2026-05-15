# CAS frame variance: 430-436 across frames (vol-76)

**Status**: `built` (preliminary, ongoing) — vol-76 (2026-05-15).

## Test

For each of the first ~20 enumerated 60/60 frames, run CAS shells 1-7.
Record final score.

## Result (first 6 frames)

| frame | CAS final score |
|---|---|
| 0 | 436 |
| 1 | 434 |
| 10 | 430 |
| 11 | 434 |
| 12 | 430 |
| 13 | 432 |

Range: **430-436**. Mean ~432. Std ~2-3.

## Implication

CAS variance across distinct frames is small (~6 points). All frames
produce CAS scores in the 430-436 range, well below ALNS pipeline's 459.

This means: **the frame choice doesn't significantly help CAS**.
The CAS bottleneck is at shells 3-7, not at frame.

## Refined understanding

CAS's plateau is structural to the greedy-annular method, not to
frame selection. To beat 459 via CAS, we'd need:
- Lookahead (consider shell k+1 needs at shell k)
- Backtracking (try different shells when stuck)
- Hybrid with ALNS at the deep center

But these add complexity that may not pay off.

## Linked

- vault/concepts/cas-greedy-433-result.md
- vault/concepts/cas-hybrid-refutation.md
