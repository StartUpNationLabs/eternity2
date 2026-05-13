---
tags: [concept, propagator, invariant]
status: built-loose
origin-vol: 10
---

# NS-1 deficit (multiset-equality invariant)

**Status**: `built` as propagator (vol-12), measured loose (vol-11)
**Origin**: Hopfer 2022 community post (vol-10 mining)
**Files**: `crates/propagators/src/multiset_equality_check.rs`, `scripts/v11_ns1_verify.py`, `scripts/v11_ns1_deficit.py`

## Statement (Hopfer 2022)

Let:
- `A` = multiset of **inward-facing** colors across the 56 border-edge cells.
- `B` = multiset of **border-facing** colors across the 56 14×14-perimeter interior cells.

For any full 480/480 solution: **A = B**.

For partial placements, the **deficit**
```
Δ(B) = ½ ∑_c |A[c] − B[c]|
```
counts how many border-to-interior interface edges are mismatched.

## Vol-11 measurements (82-board corpus)

| Score | unmatched edges | Δ | 2Δ |
|---|---:|---:|---:|
| 480 | 0 | 0 | 0 |
| 469 | 11 | 0–1 | 0–2 |
| 467 | 13 | 1 | 2 |
| 460 | 20 | 4 | 8 |
| 458 | 22 | 2 | 4 |
| 452 | 28 | 4 | 8 |
| 449 | 31 | 1 | 2 |
| 448 | 32 | 0 | 0 |

All 4 known 480 boards (across 4 different 16×16 piece sets) satisfy A=B exactly. **Necessary condition validated.**

## Vol-12 as propagator

Shipped in `multiset_equality_check.rs` propagator. Empirical lift:
- 10–28% node pruning on canonical E2 at deep search.
- +28.6% at depth-threshold t=150 + NS-1.
- Bitset version (vol-12 final): single-thread ~2,150 nps stable; multi-core ~14k nps.

## Honest scope (vol-11 finding)

On 469-class boards, **≥85% of unmatched edges are interior-to-interior** — NS-1 doesn't see those. The border-interior interface is near-perfect already.

→ NS-1 is necessary-but-loose. It rejects bad late-search states but misses most of the structure.

## When useful

- **Late-stage propagator**: enforce Δ=0 after border ring closure. Cheap: O(56·color_count) per check.
- **Diagnostic on partial-board corpus mining**: where do the 2-deficit edges live? Geographically informative.
- **NOT useful early**: Δ is trivially 0 when many cells are empty (color 0 = BORDER everywhere).

## What's deferred

`project_todo_engine_bitset` flagged "incremental NS-1": current rebuild-each-step is O(56). Incremental update on placement/unplacement is O(1). Vol-12 didn't ship.

## Linked concepts

- [[gacolor]] — sees interior-interior mismatches NS-1 misses
- [[ac3]] — sees neither, sees just edge-pairwise
- [[engine-profile-registry]] — `gacolor_ac3_ns1` profile

## Linked memory

- `project_e2_ns1_deficit_invariant`
- `project_e2_vol12_engine_profiles`
