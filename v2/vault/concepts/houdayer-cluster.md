---
name: houdayer-cluster
description: Two replicas X, Y of a search state. Define overlap function qi = 1 if X and Y agree at cell i, else 0. Cluster = con...
status: refuted
metadata:
  type: concept
---
# Houdayer cluster swap

**Status**: `refuted` (vol-22)
**Origin**: vol-22 attempt
**Files**: `crates/bench-audit/src/bin/oracle_cycle_swap.rs` (the existing operator)

## Definition

Two replicas X, Y of a search state. Define overlap function q_i = 1 if X and Y agree at cell i, else 0. Cluster = connected component of q=0 cells. Swap that cluster between X and Y. For E2, this is realizing a σ-cycle derived from a pair of boards.

The existing `OracleCycleSwap` operator IS this — it applies σ-cycles from (current, oracle) pair.

## What got tested (vol-22)

Cross-basin oracle cycle swap on (457, 456_k) pairs for k=a,b,c:
- 456_a (= 456_b byte-identical): 6 σ-cycles, all Δ<0, full swap drops 457 → 453 (or 456 with rotation fixup)
- 456_c: 4 σ-cycles, all Δ<0, full swap → 456

None of the (457, 456_k) σ-cycles produce a net-positive move. **Refuted as score-improving operator on this pair.**

## Why it failed

Our 457 and the 456_k boards are in *different basins* but the cross-basin σ-cycles all flow in the wrong direction (456 → 457 region adds errors). The 456 basins' good regions don't align with our 457's mismatch zone.

## What's still potentially valid

The same operator applied to (440/469, ???) pairs where the second board has score ≥ 469. We don't have such a board today; would need a known-better-than-our-best partial.

## Linked concepts

- [[basin-escape-recipe]] — different cross-basin operator that DID work
- [[operator-lock]] — the lock this operator was meant to break
