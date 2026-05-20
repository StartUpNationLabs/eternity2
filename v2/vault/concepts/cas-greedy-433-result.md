---
name: cas-greedy-433-result
description: Each shell solved as a SEPARATE MIP, conditioned on previous shells.
status: built
metadata:
  type: concept
---
# CAS greedy-annular result: 433/480 — vol-74 (2026-05-15)

**Status**: `built` — vol-74 (2026-05-15).
**Result**: Greedy Concentric Annular Solving with FIXED MIP gives
**433/480** on canonical E2.

## Shell-by-shell breakdown

Each shell solved as a SEPARATE MIP, conditioned on previous shells.
Per-color z[e, c] variables enforce SAME-color matching at each edge.

| shell | cells | ring | outer | total | / max | gap |
|---|---|---|---|---|---|---|
| 0 (frame) | 60 | 60 | — | 60 | 60/60 | 0 |
| 1 | 52 | 52 | 52 | 104 | 104/104 | 0 |
| 2 | 44 | 44 | 44 | 88 | 88/88 | 0 |
| 3 | 36 | 36 | 35 | 71 | 71/72 | 1 |
| 4 | 28 | 25 | 27 | 53 | 53/56 | 3 |
| 5 | 20 | 18 | 16 | 34 | 34/40 | 6 |
| 6 | 12 | 8 | 8 | 16 | 16/24 | 8 |
| 7 (center) | 4 | 3 | 1 | 4 | 4/8 | 4 |

**Verified by rescore_board: 433/480.**

## Where CAS succeeds vs fails

**Succeeds at outer shells**: 0, 1, 2 — all 100% matched. The frame
and first two interior rings have enough piece-choice flexibility
that greedy MIP can find perfect completions.

**Fails at inner shells**: 3-7 — progressively more unmatched edges.
By shell 6 only 16/24 edges match.

Reason: greedy annular commits early to specific frame + shell-1
pieces. Once committed, shell 7's tiny 4-cell center has very few
candidate pieces left, and MOST candidates don't color-match the
surrounding shell-6 pieces.

## Why this is < ALNS (459)

ALNS does GLOBAL refinement: swap pieces between FAR-APART cells,
escape local optima via destroy-repair. CAS is LOCAL-GREEDY: each
shell commits permanently, no backtracking.

The 459-vs-433 gap (26 edges) shows the cost of greedy-annular.

## What this DOES tell us

1. **Frame and shells 1-2 are perfectly solvable in isolation**.
   The puzzle's outer 3 shells have plenty of color-matchable
   piece arrangements.
2. **Inner shells are the bottleneck**. Shells 5-7 contribute
   most mismatches (18 of the 47-edge gap).
3. **Greedy doesn't suffice**. Some form of backtracking or
   global optimization is needed.

## Variants to try

- **CAS-BACKTRACK**: when shell k fails to complete fully,
  backtrack to shell k-1 and try a different solution.
- **CAS-PARTIAL-COMMIT**: at each shell, commit only the cells
  that have HIGH confidence; leave uncertain cells for later
  global ALNS.
- **CAS-LOOKAHEAD**: when solving shell k, also constrain
  partially based on what shell k+1 will need.

## Linked

- vault/concepts/concentric-annular-solving.md (parent)
- [[piece-side-matching]]
- [[e2-maximally-adversarial-thesis]] (adds axis: greedy-annular bounded)
