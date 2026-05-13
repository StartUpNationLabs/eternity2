---
tags: [concept, propagator, ac]
status: built
origin-vol: 1
---

# GAColor (Régin alldiff per color)

**Status**: `built` (vol-1), iterated rebuilds
**Origin**: Ansótegui et al. CP'08 §4.2, ported vol-1
**Files**: `crates/propagators/src/gacolor.rs`, used by `gacolor_ac3_par` profile

## Definition

For each interior color *c* with 2*k* half-edges, the puzzle is solvable only if the bipartite "color graph" admits a perfect matching:
- Vertices = the 2*k* half-edges of color *c*.
- Graph-edges = currently feasible adjacencies — pairs (h₁, h₂) such that the two host tokens could still be placed in adjacent positions in the current partial board.

A pair of half-edges is pruned if it belongs to **no perfect matching** of this graph (Régin 1994 alldifferent filter, polynomial).

Ansótegui et al. call this **"the most powerful global constraint we have found"** for edge-matching CSPs.

## Why it's powerful

- Catches infeasibility that pairwise AC-3 misses: a piece can be locally consistent at a cell but have no globally-consistent placement for the color it carries.
- Independent of search heuristic; works as a pure propagator.

## Why it's unsound under [[blackwood-algorithm]] breaks

Régin alldiff assumes **exact matching is required** for every color. Blackwood's break-index allowance lets ≤1 edge mismatch land at specific depths. GAColor would prune branches that violate exact matching but are legal under the schedule.

→ Therefore, **GAColor is OFF in `BLACKWOOD_RAW`** profile. Dropping it is part of the 47× single-thread speedup (vol-15/16).

## Performance

Vol-1: standalone GAColor + AC-3 (cell-CP) reaches 449/480 on canonical E2 in ~43-44s single-threaded; 2.5s with RootSplit parallel (8 cores).

Vol-16 win: precomputed `same_piece_rots` LUT was the headline algorithmic speedup for AC-3 inside the gacolor profile; 2.9× single-thread improvement on `joe_depth150_par`.

## When to use vs skip

- **USE**: any non-Blackwood search (CP-baseline, joe_depth150, edge-BP value-order). Sound and strong.
- **GATE**: vol-12 introduced `depth ≥ 150` gating (the gacolor cost > benefit at shallow depths).
- **SKIP**: any search that allows mismatches (Blackwood breaks, MaxSAT cluster repair). Unsound.

## Linked concepts

- [[ac3]] — pairwise consistency, layer below
- [[ns1-deficit]] — orthogonal necessary condition (multiset equality)
- [[blackwood-algorithm]] — incompatible with this propagator
- [[engine-profile-registry]] — which profiles include gacolor

## Linked memory

- `project_e2_vol12_engine_profiles`
- `project_e2_vol16_closeout`
