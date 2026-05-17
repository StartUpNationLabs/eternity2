---
name: vol122-j3-spectral-discovery
description: "Vol-122 J3 — spectral piece-graph Laplacian Fiedler vector EXACTLY recovers the border-vs-interior partition (60/196). Higher eigenvectors are degenerate; no deeper interior clustering visible."
metadata:
  type: project
---

# Vol-122 J3 — spectral piece-graph discovery

## Setup

Built piece-compatibility graph:
- Nodes: 256 pieces.
- Edge weight W[i][j] = # of (rotation_i, rotation_j, adjacency-direction)
  combinations where piece_i in rot_i and piece_j in rot_j can be adjacent
  with matching colors.

Computed Laplacian L = D - W and its eigendecomposition.

## Discovery 1: Fiedler vector = exact border/interior split

- Fiedler eigval λ_2 = **152.67** (large = strong 2-cluster structure)
- Fiedler vector partition: **60 positive, 196 negative**
- Inspection:
  - Positive cluster: **4 corners + 56 edges + 0 interior pieces**
  - Negative cluster: **0 corners + 0 edges + 196 interior pieces**

**The spectral algorithm rediscovers the border-vs-interior structure
without being told.** Confirms Selby-Riordan's color-geography design
(rare colors {1-5} on border pieces only) at the algebraic level.

## Discovery 2: Higher eigenvectors are degenerate

- Eigvecs 2-3: interior-only, all-positive or all-negative (trivial).
- Eigvec 4: 194/2 interior split (2 outlier pieces).
- Eigvecs 5+: all eigvals = 800 (degenerate, numerically random splits).

**The puzzle has no deeper spectral sub-structure visible to standard
methods.** Interior pieces are roughly uniformly connected.

## Implication for search heuristics

The Fiedler ordering would put corner pieces FIRST, then edges, then
interior. That matches what border-first MRV already does. **Spectral
ordering doesn't give a new variable-order heuristic** — it confirms
the existing border-first principle.

## What might still work spectrally

- **Per-color sub-graphs**: filter the compat graph to edges of a single
  color, then spectral-cluster each sub-graph. Could reveal color-island
  structure.
- **Weighted Fiedler** by piece-rarity: weight nodes by inverse-color-supply
  to surface rare-pieces sub-structure.
- **Spectral embedding in 3+ dimensions** for cluster visualization.

## Status

`finding-confirmatory` — confirms known structure (border/interior).
Doesn't yield new search heuristic. The 2-level spectral structure
matches the geometric one.

## Linked

- [[../sessions/vol-122]]
- [[../plans/INVENTIONS_BACKLOG]] J3 entry
- [[vol122-pcls-poc-result]] (also color-related)
- [[../concepts/rare-color-geography]] (vol-13 prior finding)
