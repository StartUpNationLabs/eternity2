---
name: interior-14x14-parity-feasible
description: "Vol-122 prep — parity check on canonical E2 interior pieces: 196 interior pieces have 784 total edges, 8 colors have ODD instance count. Achievable II=364 (complete interior) requires each odd-color to be absorbed by IB-adjacencies; with 56 IB slots ≥ 8 odd colors, parity is FEASIBLE. The veteran's milestone #3 is NOT blocked at the parity / supply level."
metadata:
  type: project
status: built
---

# Interior 14×14 parity check — FEASIBLE

## Setup

Canonical E2 puzzle has 4 corner + 56 edge + **196 interior pieces**.
Interior pieces have 0 BORDER edges → 4 colored edges each → 784
total interior-piece edges.

The 14×14 standalone interior puzzle = these 196 pieces in 196 cells
with **364 II-adjacencies + 56 IB-adjacencies** = 420 interior-touching
edges. (Each II adjacency consumes 2 piece-sides; each IB consumes 1
piece-side from interior, 1 from border. Sum: 2×364 + 56 = 784. ✓)

## Parity constraint for II = 364

For each color k, let C_k = count of color k across interior-piece
edges. To fully match all 364 II-adjacencies:
- II_k = number of II-adjacencies of color k matched.
- IB_k = number of IB-adjacencies on interior-side of color k.
- Constraint: C_k = 2·II_k + IB_k for each k.
- Therefore C_k − IB_k must be EVEN.

If C_k is EVEN, IB_k can be 0 or any even count.
If C_k is ODD, IB_k must be ODD ≥ 1.

## Measurement

Interior-piece edge counts (canonical E2):

| color | count | parity |
|------:|------:|:------:|
|  6 |  44 | EVEN |
|  7 |  43 | ODD  |
|  8 |  45 | ODD  |
|  9 |  45 | ODD  |
| 10 |  47 | ODD  |
| 11 |  49 | ODD  |
| 12 |  48 | EVEN |
| 13 |  47 | ODD  |
| 14 |  46 | EVEN |
| 15 |  44 | EVEN |
| 16 |  46 | EVEN |
| 17 |  48 | EVEN |
| 18 |  47 | ODD  |
| 19 |  44 | EVEN |
| 20 |  46 | EVEN |
| 21 |  47 | ODD  |
| 22 |  48 | EVEN |

**8 colors have ODD count.** So at least 8 of the 56 IB-slots must
absorb one instance of each odd color.

## Feasibility

- IB slots: 56 (interior-side of each B-I adjacency, fixed by 14
  positions per border side × 4 sides = 56).
- Required odd-color absorption: 8 (one per ODD color).
- 56 ≥ 8, so parity is **FEASIBLE**.

## Implication

The veteran's milestone "complete 14×14 interior" is NOT blocked by
piece-edge supply parity. There exists a *combinatorial* assignment
of interior pieces to cells with all 364 II-adjacencies matched,
assuming the border pieces can be chosen to absorb the 8 odd-color
instances on their interior-facing sides.

This is parallel to vol-44's color UB = 480 finding: combinatorial
feasibility holds for the full 480; the obstruction is geometric.

## Caveat

This is a NECESSARY condition (parity), not sufficient. Even if
parity holds, geometric placement of pieces in the 14×14 grid such
that all 364 II edges align is unknown. Could be:
- Solvable in poly time via standalone 14×14 CSP. Untested.
- Provably infeasible via more refined constraints (LP-UB on the
  interior subgraph). Untested.

## Next experiments (vol-122+)

1. **Standalone 14×14 LP-UB**: adapt `border_lp_ub` to score the
   196-piece × 196-cell subproblem. If LP-UB < 364, infeasible.
2. **Standalone 14×14 MIP**: vol-44-style but on 196 cells with all
   196 interior pieces as candidates. Estimated hours-to-days.
3. **Greedy 14×14 fill**: take McGavin's interior (II=354), apply
   region MIP on the 10 II-mismatch clusters at halo-large with
   FULL piece freedom (vol-44 only did halo-1 to halo-4).

## Linked

- [[three-milestones-from-veteran]]
- [[lp-ub-478-basins]]
- [[ns1-deficit]]
- [[vol-121]]
