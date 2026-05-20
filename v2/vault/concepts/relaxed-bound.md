---
name: relaxed-bound
description: For a board B, relaxedbound(B) = iterate cell-by-cell argmax{(piece, rot)} kmatches(pos) WITHOUT piece-uniqueness con...
status: built
metadata:
  type: concept
---
# Relaxed bound (edge-relax)

**Status**: `built` (vol-21)
**Origin**: vol-21
**Files**: `crates/bench-audit/src/bin/edge_relax.rs`

## Definition

For a board B, `relaxed_bound(B)` = iterate cell-by-cell `argmax_{(piece, rot)} k_matches(pos)` **WITHOUT piece-uniqueness constraint**, return the result's score (matched edges).

The gap `gap(B) = relaxed_bound(B) − score(B)` measures basin-local room.

## Levels of bound (vol-22 framing)

1. **Per-edge loose bound** = 480 — every edge has matchable piece pairs. No structural barrier. (Computed by `edge_tight_bound.rs`.)
2. **Per-cell relaxed (basin-local, this concept)** — converges to a basin-dependent fixed point. Ours: 461 from our 457; 469 from the vol-22 440 basin.
3. **Joint piece-uniqueness optimum** — unknown. ≥ 469 (McGavin community); ≤ 480 if E2 solvable.

## Use cases (proven vol-21)

- **Dead-end detector**: `gap = 0` ⇒ provable strict local maximum under relaxed piece-uniqueness. Strictly stronger than K=5 operator-lock test.
- **Basin triage**: compare gap across boards; high-gap = room, low-gap = saturated.

## Measurements

| Board | Score | Bound | Gap |
|---|---:|---:|---:|
| 457 (our PT) | 457 | 461 | +4 |
| 456 (winning5_sa) | 456 | 461 | +5 |
| 456 (diverse_sa) | 456 | 457 | +1 saturated |
| 450 (ocs) | 450 | 465 | +15 |
| 454 (winning5_sa_s1/s2) | 454 | 460 | +6 |
| 440 (vol-22 breakthrough) | 440 | 469 | +29 |
| Random + 5 hints | ~84 | 448 | varies |

## The +4 gap on our 457 is hard-locked

Vol-21 proof: the 4 duplicate pieces {82,146,205,233} and 4 missing pieces {189,204,207,245} have ZERO shared rotation tuples (min hamming 2). Permutation chains K=8-11: 0 improvers in 40M perms.

## Linked concepts

- [[bound-ascent]] — climb the bound landscape (built vol-21)
- [[basin-escape-recipe]] — uses bound + Hungarian + ALNS to find higher-ceiling basins
- [[exact-joint-bound]] — MaxSAT for the true joint level (unbuilt)
- [[operator-lock]] — the K=5 dead-end test this strengthens

## Linked memory

- `project_e2_vol21_edge_relax_bound`
- `project_e2_vol22_basin_escape`
