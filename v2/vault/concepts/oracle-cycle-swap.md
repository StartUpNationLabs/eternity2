---
tags: [concept, operator, partial]
status: built
origin-vol: 18
---

# Oracle cycle swap

**Status**: `built` (vol-18); refuted as cross-basin escape (vol-22)
**Origin**: vol-18
**Files**: `crates/bench-audit/src/bin/oracle_cycle_swap.rs`

## Definition

Given two boards X (current) and Y (oracle): compute the permutation σ such that Y = σ(X). Decompose σ into disjoint cycles. Apply selected cycles from σ to X.

Each cycle is a "Houdayer cluster" in spin-glass terminology (see [[houdayer-cluster]]).

## How it produced 457 (vol-18)

X = our best 447 board. Y = a 456 oracle board (different basin, same canonical hints). Applied σ-cycles from (X, Y) to X plus hot-PT (T_max=30) on the resulting state → **457/480** (current cold-start record).

The 447 → 456 transition is a single 76-cell first-order barrier (see [[r5f-cooperativity]]). OracleCycleSwap+hot-PT crosses it; standard MCMC at T=1 cannot.

## Refuted as cross-basin escape (vol-22)

Tested on (457, 456_k) pairs:
- 456_a (= 456_b byte-identical): 6 σ-cycles, all Δ < 0.
- 456_c: 4 σ-cycles, all Δ < 0.

None of the cycles produce a net-positive move. **Refuted as score-improving operator from our 457.**

## Why it fails from 457

Our 457 and the 456_k boards are in *different basins*. Cross-basin σ-cycles all flow in the wrong direction: 456 → 457 region adds errors. The 456 basins' "good" regions don't align with our 457's mismatch zone.

## What's still potentially valid

Same operator applied to (440/469, Y) pairs where Y has score ≥ 469. We don't have such a Y. Would need a known-better-than-our-best partial.

## Linked concepts

- [[houdayer-cluster]] — the spin-glass framing
- [[r5f-cooperativity]] — why it worked at 447→456 (single barrier)
- [[basin-escape-recipe]] — alternative cross-basin operator that did work

## Linked memory

- `project_e2_vol18_457_record`
- `project_e2_vol18_trajectory_families`
