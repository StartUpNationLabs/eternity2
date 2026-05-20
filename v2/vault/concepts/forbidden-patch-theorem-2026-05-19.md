---
name: forbidden-patch-theorem-2026-05-19
description: For canonical Selby-Riordan Eternity II, for each k-cell patch shape,
status: built
metadata:
  type: concept
---
# Forbidden-Patch Anti-Correlation Theorem

**Status**: `built` (Vols 138-142, 2026-05-19)

## Statement

For canonical Selby-Riordan Eternity II, for each k-cell patch shape,
let $F_k(B)$ be the number of patches in board $B$ that are
FORBIDDEN under any rotation assignment. Then $F_k$ is a strong
inverse rank correlate of matched-edge score.

## Patch forbidden-rates on RANDOM piece tuples

| Patch | Cells | Feasible % | Forbidden % |
|-------|-------|-----------:|------------:|
| 2-horizontal | 2 | 60.8% | 39.2% |
| 3-horizontal | 3 | 17.6% | 82.4% |
| L-shape | 3 | 17.3% | 82.7% |
| 2×2 | 4 | 0.24% | **99.76%** |
| 2×3 | 6 | 0.000% | **100.000%** |

## Real boards (2x3 forbidden count vs matched edges)

| Board | matched | forbidden 2x3 / 210 |
|-------|---------|---------------------:|
| LOW (400) | 400 | 137 (65%) |
| MID (450) | 450 | 66 (31%) |
| HIGH (461) | 461 | 36 (17%) |
| **McGavin (469)** | **469** | **26 (12%)** |

The 461→469 gap (+8 edges) ↔ 36→26 forbidden 2x3 (-10 patches).
Roughly 0.8 score per forbidden-2x3.

## Implications

A perfect 480 has 0 forbidden patches of any shape.
The 461→480 gap (19 edges) corresponds to ~36 forbidden 2x3 patches.

Forbidden-count is a search-progress diagnostic even when matched-
edges plateau.

## V140 + V143 wiring outcomes — ALL INERT from 461 at 5min

| Approach | Result |
|----------|--------|
| V140 lex-break on iso-score (forbidden-2x2 count) | 461 → 461 (no change) |
| V143 ForbidDestroy operator (destroy forbidden 2x3) | 461 → 461 (no change) |

Both approaches yielded zero improvement. The 461 plateau is
impenetrable by these direct integrations. Consistent with σ-cycle
indecomposability (vol-65): 461→469 requires a coupled 255-cell
permutation, not local moves.

Other 5min attacks from 461 in this session:
- FILAMENT-repair (V130, V134): tied with SA, no escape
- TUNNEL PT destroy-aggressiveness ladder (V141): all chains
  converged to 461

The forbidden-patch theorem remains valuable as a DIAGNOSTIC but
does not translate to a search improvement at this integration level.

## What's open

- Forbidden-count as PRIMARY objective (not tiebreaker).
- 2x3 / 3x2 stronger than 2x2 as diagnostic.
- Combine with PALIMPSEST consensus traps.

## Linked

- [[intaglio-forbidden-patterns]]
- [[palimpsest-historical-consensus]]
- [[concretion-rigid-molecules]] (refuted twin)
