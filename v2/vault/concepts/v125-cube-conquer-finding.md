---
name: v125-cube-conquer-finding
description: "Vol-125 2026-05-18: 576 piece-unique cubes (top-4 candidates per cell × 4 corners + 4 edge cells; piece-uniqueness filter) all decide UNSAT in <1s each via kissat. Average 0.6s per UNSAT decision; max 0.95s. Compared to vol-124 UNKNOWN-after-1h on unconstrained instance, the cube assumptions provide MASSIVE pruning."
metadata:
  type: project
status: built
---

# Vol-125 cube-and-conquer (initial 576-cube run)

## What we did

Generated CNF cubes by adding 8 unit clauses each:
- 4 corners (cells 0, 15, 240, 255): top-4 piece-rot candidates per cell.
- 4 top-row/left-col cells (1, 2, 16, 32): top-4 piece-rot candidates per cell.
- Filtered for piece-uniqueness: a cube was kept iff no two cells used
  the same piece. 576 of 65536 raw products survived this filter.

For each surviving cube, appended its 8 unit clauses to the canonical
SAT CNF (171k vars × 5.8M clauses + 5 official hint unit clauses) and
ran kissat 4.0 with `--relaxed`.

## What we found

**ALL 576 cubes returned UNSATISFIABLE in <1s each.**

- Avg time: 0.589s
- Max: 0.950s
- Min: 0.430s
- Total wall time: 339s across all 576 (effective ~5min on 2 cores)

## Why this matters

Compared to vol-124's 8 × kissat × 1800s (=14400s CPU) on the bare canonical instance
returning all UNKNOWN:

- Bare instance: UNKNOWN after 1h.
- Cube + 8 unit clauses: UNSAT in <1s.

The 8 assumptions provide enough constraint propagation that kissat's
CDCL finds a clean refutation in fractions of a second. This proves
**the canonical SAT is tractable in cube-conquer form even on monolithic
CDCL**, just not from an empty assumption set.

## What we proved (and didn't)

We PROVED: across the 576 piece-unique 8-cell combinations enumerated,
NONE extend to a 480 solution. Specifically:
- TL corner: top-4 piece-rots are {(0,3), (1,3), (2,3), (3,3)}.
- TR corner: top-4 piece-rots from {(0,0), (1,0), (2,0), (3,0)}.
- BL/BR similar.
- Top-row cells 1, 2: top-4 piece-rots are pieces 4-7 at rot 0.
- Left-col cells 16, 32: top-4 piece-rots are pieces 4-7 at rot 3.

We have NOT proven the canonical instance is UNSAT — the top-4 picks
exclude 52 of the 56 candidates per edge-class cell. The 480 could
use a piece outside the top-4 at any of these 8 positions.

## Implications for further cube design

This 576-cube run took 5 min on 2 cores. To increase coverage:

1. **Wider top_k**: top-8 per cell → 8^8 = 16.7M raw cubes; piece-unique
   subset would be ~tens of thousands. At 1s/cube on 4 cores ≈ tens of
   hours per full sweep.
2. **Decision cells with smaller domains**: cells 0, 15, 240, 255 have
   only 4 candidates each. Limiting cubing to corners only (top-K=4)
   gives 4! = 24 cubes total (this is exactly the vol-124 corner-perm
   sweep — already exhausted).
3. **Adversarial cubing**: instead of top-K, pick cubes where the most
   COMMON pieces are placed at decision cells (high-info cubes). Could
   reduce time-per-cube but doesn't necessarily improve coverage.
4. **Variable selection via VSIDS**: run kissat briefly (10s) on the bare
   instance, extract the top-VSIDS literals from its prober output,
   use those as decision variables for cubing. This is the original
   AlphaMapleSAT idea.

## Wider-cube empirical NULL (2026-05-18 09:23)

Followup run: top-row 6 contiguous cells (positions 0-5) with adjacency-
color pre-filter AND piece-uniqueness, all candidates per cell. Produced
587,808 piece-unique adjacency-feasible cubes.

First 50 cubes with 60s/cube kissat timeout:
- 12 UNSAT (~1-3s each)
- 38 UNKNOWN (full 60s timeout)

**Conclusion: smart-cube generation kills the speed of the initial
576-cube experiment.** The initial cubes were fast BECAUSE adjacency
was violated (kissat unit-prop catches color mismatch in <1s). Once
adjacency is pre-filtered, the remaining cubes require deep SAT
reasoning, mostly hitting 60s timeouts.

At 60s/cube × 587k cubes / 4 cores = ~100 days wall. Not feasible.

Implication: **cube-and-conquer with vanilla kissat on this encoding is
not viable**. The vol-124 finding stands: kissat cannot decide canonical
E2 in reasonable time at any cube size that leaves the instance "hard".

Paths still open:
- **Better SAT solver heuristics**: VSIDS-priority cubing (AlphaMapleSAT's
  actual idea — pick decision variables based on solver-internal scores
  after a warm-up run).
- **Different SAT encoding**: tighter symmetry breaking, super-block
  encoding (W14), permutation encoding (W16 Codognet 2025).
- **Approximate methods**: SLS solvers (probSAT, YalSAT) instead of CDCL.
- **Don't use SAT for the 480 search**: revert to constraint
  satisfaction at the engine level + invent better algorithms.

## Linked

- [[w-sat-459-unsat-findings]]
- [[459-basin-halo-10-rigidity]]
- [[vol-125]]
