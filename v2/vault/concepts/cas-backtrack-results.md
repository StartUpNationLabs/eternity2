# CAS-BACKTRACK results: 434/480 — vol-78 (2026-05-15)

**Status**: `built` (negative — same-shell-retry doesn't help) — vol-78.

## Result

Ran CAS-BACKTRACK from frame_0 (CAS-greedy best, 436). Final: **434/480**.

WORSE than CAS-greedy (436) on the same frame. Retrying SAME shell with
forbidden-cuts doesn't help.

## Shell-by-shell trace

| shell | score | attempts | total |
|---|---|---|---|
| 0 (frame) | 60/60 | 1 | 60 |
| 1 | 104/104 | 1 | 164 |
| 2 | 88/88 | 1 | 252 |
| 3 | 72/72 | 1 (first run hit perfect) | 324 |
| 4 | 53/56 | 4 (all forbidden) | 377 |
| 5 | 34/40 | 4 (all forbidden) | 411 |
| 6 | 18/24 | 4 (all forbidden) | 429 |
| 7 | 4/8 | 4 (all forbidden) | 433 |

Final 434 (off-by-1 from MIP-sum due to rescore inclusion).

## Why same-shell-retry fails

Shells 4-7 have MULTIPLE equally-imperfect MIP-optimal solutions
(all scoring 53/56, 34/40, etc.). Forbidding one finds another with
SAME score. The cuts just enumerate equivalent solutions, not better.

## What would actually help

CAS-DEEP-BACKTRACK: when shell k is stuck, go BACK to shell k-1 and
forbid THAT solution. Try a different shell-k-1 to expose different
constraints on shell k.

Example: shell 4 stuck at 53/56. Going back to shell 3 (which had
72/72 perfect) and forbidding it. Now shell 3 might give 71/72 with
different piece set, leading shell 4 to maybe 55/56.

But this is exponentially expensive: backtrack depth × cuts × shells.

## Alternative: CAS + ALNS-refine

Instead of CAS-BACKTRACK, just take CAS's 433 output and run ALNS
on it. Standard ALNS might find a 460+ from this starting point
since it's already 90% matched.

Quick test (vol-78b).

## Linked

- vault/concepts/cas-backtrack.md (parent)
- vault/concepts/cas-frame-final.md (vol-76 CAS-greedy results)
