---
tags: [concept, community-port, partial]
status: built-partial
origin-vol: 9
---

# Verhaard set-composition swap-annealing

**Status**: `built-partial` (vol-9 small-signal port); full method unported
**Origin**: Verhaard groups.io 2008-04-11 (message 105190116)
**Files**: `crates/solver-verhaard/`, `crates/benchmark/src/bin/verhaard_e2.rs`

## Verhaard's actual method (verbatim)

> "Take a random group of maybe 180-190 pieces, use some method to determine the overall tilability of this group, and then gradually improve this group using by exchanging 'bad pieces' with better pieces using some appealing/annealing method until some local optimum is reached… From this 'good group' we take the 10-20 'worst performers' and try to find a solution of the initial 80 pieces using as much as possible from the 'loser group' and (as few as possible) 'worst good ones' and use this 80-piece solution as the initial basis for one small search."

## Tilability metric

Count of **2×2 sub-tilings** achievable on the candidate set. O(n⁴). Verhaard validated R² = 65% with `log(total 2×2 tilings)` on random subsets.

**Not 2×3** — vol-7's memory had the wrong granularity (probably picked up from a downstream summary). Corrected in `reference_verhaard_actual_method`.

## Algorithm shape

1. Pick a random ~180-190-piece subset of the 196 interior pieces.
2. Swap-anneal subset composition under the 2×2-count metric until local optimum.
3. The 10-20 *worst performers* of the optimised set form the **loser group**.
4. Backtrack the first ~80 placements preferring loser-group pieces (front-load the hard pieces).
5. Remaining ~170-180 pieces (mostly the "good 180" minus the worst 20) exhaustively searched in the sub-tree under that 80-piece scaffold.

## What we shipped (vol-9, small-signal)

`crates/solver-verhaard/` + `verhaard_e2.rs`:
- `SolveOpts.preferred_pieces` (front-load chosen pieces).
- `SolveOpts.excluded_pieces` (set-subset filter).
- `ValueOrder::PreferredFirst`.
- SA on **2×2-tilability metric** (small subsets, not full 180-piece composition).

Result: seed 42 SA-preferred list reaches depth 181 / 308 edges (30s cold); mean 297.5 across 4 seeds.

**+6.5-edge signal vs random**, confirming architecture but not expressive enough at our scale. Brendan 2008 confirms Verhaard's 180-piece subset is intractably hard by construction.

## What's NOT shipped

- The outer set-composition swap-annealing meta-loop.
- The "loser group" extraction + scaffold seeding.
- The 80-piece + 170-piece phase split.

Estimated full port: **2-3 days**.

## Why this is the attested 469→467 path

This is the **attested algorithm behind the 12-year community ceiling (467 Verhaard 2008 → 469 McGavin 2020 via Blackwood)**. Verhaard's method is composition-level, not temporal-per-piece. It has not been ported to a modern Rust stack to our knowledge.

## Linked concepts

- [[blackwood-algorithm]] — the 2020 successor that pushed 467 → 469
- [[reference-verhaard-actual-method]] — full reference card

## Linked memory

- `reference_verhaard_actual_method`
