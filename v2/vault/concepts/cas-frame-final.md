---
name: cas-frame-final
description: CAS-from-20-frames final results — vol-76 (2026-05-15)
status: built
metadata:
  type: concept
---
# CAS-from-20-frames final results — vol-76 (2026-05-15)

**Status**: `built` (final) — vol-76 (2026-05-15).

## Result

CAS run on each of 20 enumerated 60/60 frames. Distribution:

| CAS score | count |
|---|---|
| 430 | 5 |
| 431 | 2 |
| 432 | 4 |
| 433 | 3 |
| 434 | 2 |
| 435 | 2 |
| 436 | 2 |

- **Range: 430-436**
- **Mean: 432.4**
- **Best: 436** (frame_solution_0)
- **Std: ~2**

## Conclusion

Greedy CAS plateaus at ~432±3 regardless of frame choice. The +6
spread is structural variance, not opportunity for breakthrough.

**Greedy-annular CAS cannot beat 436 on canonical E2 from any
60/60 frame.**

## Why CAS-greedy plateaus

Each shell's MIP commits to a locally-optimal placement without
considering downstream shells. By shell 5-7 (deep interior), the
remaining 4-12 cells have very few piece-rotation candidates that
match shell-6's inward colors.

The frame is irrelevant: any 60/60 frame leads to the same
structural plateau because the BOTTLENECK is in shell 5-7
piece-availability, not in frame.

## What might help (untested)

- **CAS-BACKTRACK** (vol-78): retry shells when imperfect.
- **CAS-LOOKAHEAD**: when solving shell k, constrain by shell k+1's
  feasibility.
- **CAS-HYBRID-ALNS-DEEP**: CAS for shells 0-3, then ALNS for inner.
  (Compared to vol-74's hybrid CAS-3 + ALNS = 418, this gives less,
  so hybrid is unlikely to help.)

## Linked

- vault/concepts/concentric-annular-solving.md
- vault/concepts/cas-greedy-433-result.md
- vault/concepts/cas-frame-variance.md (preliminary, now superseded)
- vault/concepts/cas-backtrack.md (next attempt)
- vault/concepts/cas-hybrid-refutation.md
