# Spectral analysis of E2 piece-compatibility graph

**Status**: `built` — vol-65 (2026-05-15).
**Origin**: gap-list item 5 from AUTONOMOUS-MONTH-PLAN.
**Files**:
- `scripts/vol65_piece_compat_graph.py` — builds graph + computes spectrum
- `output/vol-65/piece_compat_spectrum.npz` — saved eigenvalues + Fiedler vector

## The graph

Nodes: 256 pieces.
Edges: weight w(p1, p2) = number of (k1, k2, side1, side2) tuples
satisfying color-match and opposing world-direction (any of 4 orientations
per piece × 4 facing directions = 16 possible adjacencies).

Properties:
- Edge weights: min 4, median 4, max 24.
- Degree: min 184, median 768, max 784 (every piece can neighbor many).
- **Connected**: single component (vs the piece-side graph's 86 components).

## Spectrum

Top-10 eigenvalues of adjacency matrix W:
```
λ_1 = 737.36    (dominant)
λ_2 = 249.79
λ_3 = 242.17
λ_4 = 234.31
...
```

**Spectral gap λ_1/λ_2 = 2.95**, (λ_1-λ_2)/λ_1 = 0.66 — strong gap.

Algebraic connectivity μ_2 (normalized Laplacian) = **0.507**.

## Fiedler bisection

Cluster pieces by the 2nd-smallest eigenvector of L_norm:
- Side 0 (negative Fiedler): 186 pieces, **all INTERIOR**.
- Side 1 (positive Fiedler): 70 pieces = 4 corners + 56 edges + 10 interior.

The Fiedler vector **near-perfectly separates frame pieces (corners + edges)
from interior pieces**, with exactly 10 interior pieces leaning toward
the frame side.

## The 10 "frame-leaning" interior pieces

| piece | Fiedler | edges (N, E, S, W) |
|---|---|---|
| 172 | 0.0191 | (9, 15, 15, 15) |
| 178 | 0.0123 | (9, 19, 19, 15) |
| 125 | 0.0060 | (7, 19, 21, 15) |
| 91 | 0.0047 | (6, 19, 13, 15) |
| 100 | 0.0046 | (7, 7, 17, 15) |
| 119 | 0.0031 | (7, 15, 19, 22) |
| 123 | 0.0018 | (7, 18, 18, 15) |
| 107 | 0.0015 | (7, 9, 16, 15) |
| 243 | 0.0006 | (14, 15, 18, 19) |
| 242 | 0.0001 | (14, 15, 15, 17) |

**Common feature: color 15** (an unrotation-asymmetric color from
vol-65 orbit work — 50 sides total). Most of these pieces have
2-3 color-15 edges. Color 15 has E=10 W=21 N=4 S=15 in canonical
orientation — heavily biased toward South.

These 10 interior pieces are "frame-compatible" because their color
profile (especially color 15) matches what the puzzle's frame-adjacent
positions demand.

## Hypotheses

1. **Value-order prior**: in CP search, when filling interior cells
   adjacent to the perimeter (shell-1), PREFER these 10 pieces.
   They have higher color-fit with the frame context.
2. **Destroy operator**: a "frame-aware destroy" could target the
   cells where these 10 pieces sit (or should sit) in records.
3. **Sanity check**: do our 459/458 records actually place these
   10 pieces in shell-1 cells? Probably yes if the Fiedler vector
   is meaningful.

## Sanity check on known records

For each known record, compute the average shell-distance of these
10 pieces. If they're in shell-1 (frame-adjacent), shell-distance ≈ 1.

TODO: run this check. Expected outcome: ~1-3 (frame-adjacent).

## What this finding is NOT

- Not a record-breaking algorithm by itself.
- Not a new bound on E2.
- An **observed structural fact**: the puzzle's piece set has a
  Fiedler-clear "frame vs interior" partition with 10 ambiguous
  interior pieces. This was not predicted by Selby-Riordan rules
  documented elsewhere.

## Linked

- [[piece-side-matching]] (parent PSM concept)
- [[piece-orbit-structure]]
- [[../sessions/vol-65]]
- [[../plans/AUTONOMOUS-MONTH-PLAN.md]] gap-list item 5
