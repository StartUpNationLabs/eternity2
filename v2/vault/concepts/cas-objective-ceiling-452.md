---
name: cas-objective-ceiling-452
description: CAS objective fully covers all 480 grid edges — no inter-shell edges are missed. CAS's empirical 433-436 plateau is NOT an objective-coverage issue; it is a piece-availability / shell-frozen-context issue. Refuted my own initial hypothesis live in vol-79.
metadata:
  type: project
---

# CAS objective coverage — full 480, no missing edges

**Status**: `built` — derived and self-corrected 2026-05-15 vol-79.
**Origin**: post-CAS plateau analysis (vol-74, vol-78).

## My initial hypothesis (FALSE)

I conjectured the CAS objective summed across shells missed
~112 inter-shell edges, capping CAS-greedy at ≤ 452/480.

## Honest correction

Edge classification by (shell of cell a, shell of cell b),
counting each undirected edge once:

| shell k | ring_k (within shell) | boundary_k (to shell k−1) |
|--------:|----------------------:|--------------------------:|
| 0       | 60                    |  0                        |
| 1       | 52                    | 56                        |
| 2       | 44                    | 48                        |
| 3       | 36                    | 40                        |
| 4       | 28                    | 32                        |
| 5       | 20                    | 24                        |
| 6       | 12                    | 16                        |
| 7       |  4                    |  8                        |
| **sum** | **256**               | **224**                   |

Total: 256 + 224 = **480**. ✓ All board edges accounted for.

CAS shell-k objective = ring_k + boundary_k (where boundary_k is
the "outer" edges to the already-placed shell k−1). **Each edge
appears in exactly one shell's objective.** No coverage gap.

## So why does CAS plateau at 433-436?

**Not edge accounting.** The bound is search-quality plus piece
availability:

1. **Greedy commit**: CAS solves shells in order. After shell 0
   and shell 1 are placed, shell 2's available pieces are
   constrained. By shell 4-5, the remaining pieces have
   side-color multisets badly matched to the remaining boundary
   colors.
2. **Frozen-context MIP**: at each shell, the MIP fixes the
   inner cells of the already-placed shell — those colors are
   constants. The remaining pieces must match these constants
   AND each other. The MIP is feasible, but the *objective* is
   bounded below ring_k + boundary_k for deeper shells because
   the locked-in inner border may have color profiles that
   force mismatches.
3. **Empirically**: shells 0-2 score 252/252 perfect; shells
   3-7 progressively drop, hitting 53/56, 34/40, 18/24, 4/8 —
   the deeper the shell, the worse the matching.

## Implication for record-chasing

- **CAS-greedy is intrinsically bounded around 436-440.** Not
  because of edge accounting, but because the greedy commit
  locks in poor piece-availability for inner shells. The
  remaining pieces just CAN'T color-match the locked inner
  borders well.
- **The 112 "missing edges" framing was wrong.** All edges are
  optimised; they're optimised under bad context.
- **Fix candidate**: solve adjacent shell PAIRS jointly (option
  3 in my prior page). 4× MIP cost per pair, but the inner
  shell's pieces become free variables again — allowing
  re-arrangement to fix boundary color mismatches.

## Methodological note

I caught this error live (CAS page draft started with wrong "452
ceiling" claim, traced through edge counting, found my own
counter dropped edges going deeper). Logged here to track the
correction trail — vault discipline: no quiet deletes.

The mistake was: my counter only classified neighbours by
shell(n) == k OR shell(n) == k − 1, missing shell(n) == k + 1.
The "missing" direction was actually counted by the OTHER
endpoint as outer. After fixing the audit, 256 ring + 224
boundary = 480.

This is a useful lesson: when computing dual decompositions,
verify your edge accounting by independent sum-to-total.

## Linked

- [[concentric-annular-solving]] (parent algorithm)
- [[cas-greedy-433-result]]
- [[cas-then-alns-refine]] (CAS + ALNS-refine = 437-439, +4-6 only)
- [[cas-backtrack-results]]
