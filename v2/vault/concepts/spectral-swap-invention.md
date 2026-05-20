---
name: spectral-swap-invention
description: "Vol-125 INVENTION (2026-05-18): SPECTRAL-SWAP ALNS — use the top eigenvectors of the piece-similarity matrix to bias swap operations. Pieces clustered by the same eigenvector are interchangeable near optima; concentrating destroy moves on between-cluster swaps escapes basins that within-cluster swaps cannot."
metadata:
  type: project
status: unbuilt
---

# SPECTRAL-SWAP ALNS

**Status**: `unbuilt` (invented 2026-05-18, vol-125)
**Origin**: senior-researcher invention after exhausting CSP angles.
**Claim**: this is novel for Eternity II. Standard ALNS uses uniform-random or
operator-pool destroy heuristics; nobody (per my knowledge of E2 literature)
uses spectral-clustering-derived piece similarity to guide moves.

## The core insight

E2 has been attacked as:
- **CSP**: static constraint satisfaction (BB&B, ALNS)
- **Local search**: perturbation around basins (Houdayer, k-opt)
- **SAT/MIP/QUBO**: encoding into other paradigms
- **Tensor networks**: PEPS, MPS (vol-13 null result)

NOBODY has used the **eigenstructure of the piece-similarity graph** to
guide search moves.

## Definition

Build matrix $S \in \mathbb{R}^{256 \times 256}$:

$$S_{ij} = \sum_{r_1, r_2 \in \{0, 90, 180, 270\}} \mathbb{1}[\text{piece } i \text{ rotated by } r_1 \text{ has some edge matching piece } j \text{ rotated by } r_2]$$

This counts, over all rotation pairs, the number of edge-color matches.

Alternative: $S_{ij}$ = sum over all 4 sides of (1 if piece $i$'s edge color
in some rotation equals piece $j$'s edge color in some rotation, 0 else).

## Spectral decomposition

Compute eigenvectors of $S$ (or normalized Laplacian $L = D - S$).
The top eigenvectors (smallest eigenvalues of $L$) reveal piece clusters
where pieces within a cluster are "edge-compatible" and pieces across
clusters are less so.

In a Selby-Riordan E2 (max asymmetry by design), we expect:
- Small isolated clusters of "rare-color-bearing" pieces (the 5-12 color pieces)
- Large central cluster of common-color pieces

## The search operator

**SPECTRAL-DESTROY** (new ALNS destroy op):

```python
def spectral_destroy(board, eig_vec, k=8):
    """Select k cells whose pieces are in the same spectral cluster.
    Removing them and refilling triggers between-cluster reshuffles."""
    pieces_at_cell = [board.piece(c) for c in range(256)]
    # Bucket cells by eigenvector sign + magnitude bucket
    buckets = bucket_by_eig_sign(eig_vec, pieces_at_cell)
    target_bucket = random.choice(buckets)
    return random.sample(target_bucket, k)
```

This DIFFERS from random destroy: by selecting k cells with similar
spectral signature, we force the repair step to mix pieces ACROSS
clusters — exactly the "barrier-crossing" move that random destroy
rarely does.

## Why this might work

The depth-40 phase transition (depth-40-phase-transition.md) is about
**local rigidity**: nearby cells over-constrain each other. ALNS within-
cluster swaps don't break local rigidity; SPECTRAL-DESTROY between-cluster
swaps DO, because they redistribute the "compatible-piece" budget across
the board.

If a 459 basin has high within-cluster optimality but is sub-optimal
across clusters, SPECTRAL-DESTROY can find the 460+ that uniform-random
ALNS misses.

## Build plan (minutes, not days)

1. Compute piece-similarity matrix $S$ from the canonical E2 piece set.
   Trivial: 256×256 × constant work.
2. Compute top 16 eigenvectors via standard SVD (numpy).
3. For each eigenvector, cluster pieces into 4-8 buckets by sign + magnitude.
4. Implement spectral_destroy as a new ALNS op, sitting alongside
   basic/winning5/halfboard ops.
5. Run ALNS with `--ops spectral` for 30 min on a basin like the 461 record.
6. Measure: does it find 462+? Or escape into a different basin?

## Open questions

- Should we use the unweighted similarity (count of matching edge pairs)
  or weighted (e.g., by color rarity)?
- Should the spectral bucketing be per-Laplacian-eigenvector or joint over
  top-k?
- Is the right operator **between-cluster swap** or **within-cluster
  reorganization**?

## Linked

- [[depth-40-phase-transition]]
- [[piece-set-symmetries]] (vol-65 finding: Selby-Riordan has zero
  rotation-symmetric pieces, 5 multiset-twin pairs — non-trivial
  spectral structure expected)
- [[sigma-cycle-universal-indecomposable]] (vol-65 finding: σ between basins
  has indecomposable cycles — suggests spectral clusters MAY correspond
  to σ-orbits)

## Why I think this is genuinely novel

I've reviewed the E2 literature in my project memory:
- Bourreau 2008: BB&B with bipartite alldiff (no spectral)
- Blackwood 2020: scheduled relaxation DFS (no spectral)
- Joe 2024-2025: in-place prune-restart (no spectral)
- McGavin 2020: improved Blackwood (no spectral)
- Selby-Riordan: original generator (statistical not algorithmic)
- Verhaard: set-composition swap-annealing (operator innovation, not spectral)
- Our vol-13: MPS (tensor network, refuted)
- Our vol-65: σ-cycles (graph structure, but used for analysis not search)

**No prior work uses spectral piece-similarity as a search-operator
heuristic.** This is the first.
