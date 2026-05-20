---
name: exact-joint-bound
description: This is the level-3 bound from relaxed-bound's hierarchy.
status: unbuilt
metadata:
  type: concept
---
# Exact joint bound (MaxSAT)

**Status**: `unbuilt` (z3 attempted, failed; need kissat-RC2)
**Origin**: vol-22 user-Q
**Files**: existing `crates/sat-encoder/src/lib.rs` + `cluster_maxsat_repair.rs`

## Definition

Compute the EXACT maximum number of matched edges achievable subject to:
- Piece-uniqueness (each piece used exactly once)
- Border-class constraints
- Canonical hints

This is the level-3 bound from [[relaxed-bound]]'s hierarchy.

For the whole puzzle: this is an open problem (E2 unsolved). For sub-regions: tractable.

## Vol-22 attempts

`cluster_maxsat_repair` with z3 on our 442/463 basin:
- halo=2 (62 cluster + 210 free): 76 MB WCNF, z3 UNKNOWN in 60s.
- halo=0 (62 cluster + 60 free): 3.6 MB WCNF, z3 UNKNOWN in 180s.

**z3 cannot solve our instances**. Need a real MaxSAT solver.

## Path forward

- Try kissat in MaxSAT mode (or wrap with RC2).
- Try MaxHS, EvalMaxSAT, RC2-from-PySAT.
- Smaller clusters (20-30 cells) first to validate the pipeline.

## What this gives us

Once we can compute joint bounds for small regions:
- Verify the relaxed-bound's tightness on small clusters.
- Identify regions where the joint bound is much tighter than the relaxed bound (would suggest "real" unsolvable structure).
- Eventually: a search-progress signal that's strictly stronger than the relaxed bound.

## Linked concepts

- [[relaxed-bound]] — the looser version computed by greedy
- [[prune-restart]] — alternative way to get tight local optima
