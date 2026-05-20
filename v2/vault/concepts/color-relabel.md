---
name: color-relabel
description: Joint search space: (placement, color-permutation π ∈ S23). Apply π to all piece edges. Physics unchanged (score is p...
status: unbuilt
metadata:
  type: concept
---
# Color-relabel as search variable

**Status**: `unbuilt`
**Aged**: since vol-20 (catalog N2), vol-21 (T4)
**Files**: would extend `gacolor` propagator

## Definition

Joint search space: (placement, color-permutation π ∈ S_23). Apply π to all piece edges. Physics unchanged (score is permutation-invariant), but BP/gacolor heuristics rerank cells differently under π.

## Why it might help

- At plateaus, fan out across π choices; one π may make our heuristics escape.
- Symmetry breaking that the current stack doesn't use.

## Why it might NOT help

Score IS invariant under π. So bound is invariant. Only the path-dependent heuristics change. If our heuristics are roughly optimal already, π doesn't matter.

## Build plan

Extend `gacolor` propagator to test multiple π in parallel. At a plateau, run K different π's in parallel, pick the one whose CP makes more progress.

Est. 4-8 hrs.

## Linked concepts

- [[bound-ascent]] — π is independent
- [[prune-restart]] — same composition opportunity
