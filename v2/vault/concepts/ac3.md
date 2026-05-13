---
tags: [concept, propagator]
status: built
origin-vol: 1
---

# AC-3 (arc-consistency)

**Status**: `built` (vol-1), iterated
**Origin**: Bessière & Régin MAC (standard CSP literature)
**Files**: `crates/solver-engine/src/lib.rs` (incremental AC-3 over piece-rotation domains)

## Definition

For every pair of adjacent cells (i, j) with current domains D_i, D_j: remove from D_i any (piece, rotation) tuple whose color on the shared edge has no compatible (piece, rotation) in D_j. Iterate to fixed point.

Standard pairwise arc-consistency, restricted to the adjacency graph of the 16×16 grid (480 edges).

## Vol-1 baseline

Cell-CP with AC-3 alone reaches **449/480** on canonical E2 (~43-44s single-threaded). Adding [[gacolor]] is where the big lift comes from for non-Blackwood searches.

## Vol-16 algorithmic win

Precomputed `same_piece_rots` LUT (which rotations of the same piece share which edges) → AC-3 doesn't re-derive this on every revision call. Headline speedup of vol-16: **2.9× on joe_depth150_par** (~2.4k → ~7k nps).

## Unsound under [[blackwood-algorithm]]

Same reason as [[gacolor]]: AC-3 assumes exact edge matching is required. Under break allowance, it removes tuples that would induce mismatches at non-break depths — but those mismatches might be licensed at a break_index later. Off by default in `BLACKWOOD_RAW`.

## Linked concepts

- [[gacolor]] — strictly stronger global constraint above
- [[ns1-deficit]] — orthogonal necessary condition
- [[bitset-domain-rep]] — vol-12 rep AC-3 operates over

## Linked memory

- `project_e2_vol12_engine_profiles`
- `project_e2_vol16_closeout`
