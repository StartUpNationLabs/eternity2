# Multiple LP UB 478 basins discovered (vol-44)

**Status**: measurement.
**Origin**: vol-44 border-clustering sweep on 4746 boards → 9 distinct
high-score class representatives → LP UB computed for each.

## Finding

There are **multiple distinct basins** (distinct 60-cell border
arrangements) with the same LP UB = 478.

| Class rep | Score | LP UB |
|---|---:|---:|
| vol-32 458 (original class A) | **458** | 478 |
| vol-35 lo_f150_s454 | 454 | 478 |
| vol-35 lo_f452_s455 | 455 | 478 |
| vol-35 lo_00001 (s457) | 457 | 478 |

All four basins share the SAME LP relaxation ceiling. But:
- The vol-32 basin achieves 458 (our record).
- The other three basins peaked at 454, 455, 457 — almost certainly
  because **we never ran sustained ALNS on them**.

## Why the LP UB is a basin-coarse invariant

The LP UB = 60 (B-B) + bi_ub + lp_interior. With bb=60 fixed (perfect
border ring), the UB only depends on:
- The 56 B-I edges' required colors.
- The interior piece-set available after pinning the border.

Many distinct border *placements* can produce the same B-I requirement
multiset (different orderings of the same constraints). Hence many
distinct borders map to the same LP UB.

**Implication**: each LP UB equivalence class likely contains MANY
distinct basin trajectories.

## Action implication

We have a 458 record in ONE basin in the LP-UB-478 family. The OTHER
basins in this family have NEVER been seriously attacked. **The
research path**:

1. Pick the highest-scoring unexplored LP-UB-478 basin (e.g.,
   `lo_00001_t00_s002_d207_s457` with score 457).
2. Run focused ALNS + cluster-repair MIPs to push toward 458 or higher.
3. If it reaches 458, we have a new 458 record (confirms reproducibility).
4. If it reaches 459+, we have a record break.

This is **structurally different** from previous attacks because the
LP UB tells us 478 is the theoretical ceiling. We're not chasing an
unknown — we know the room.

## Within-UB-class structural diversity (measured)

Board-diff between vol-32 458 (basin A) and other LP-UB-478 basin reps:

| Compared to | Same (pos, piece, rot) | Top region piece overlap |
|---|---:|---|
| **lo_00001_s457** | 92 / 256 (36%) | **56 / 56 (100%!)** |
| lo_f150_s454 | 9 / 256 (3.5%) | 11 / 56 (20%) |
| lo_f452_s455 | 8 / 256 (3%) | ~similar to f150 |

**Two distinct families within LP-UB-478:**

1. **Family A* (vol-32 458, lo_00001 s457):** share the *entire* top
   4-row piece-set (56/56). Differ in middle/bottom. lo_00001 looks
   like an "early diverged variant" of the same trajectory.

2. **Family LO (lo_f150, lo_f452, ...):** structurally different
   piece-set from family A*. Only 3-5% same with vol-32 458.

This says the LP UB 478 is shared by ≥2 STRUCTURALLY DISTINCT
families. The LP relaxation captures a coarse invariant (perhaps
total piece-set + adjacency multiset?) that multiple distinct
piece-position assignments share.

**Implication for ALNS push:**

- lo_00001 → likely converges to 458 quickly (same top, "similar"
  trajectory).
- lo_f150, lo_f452 → if they reach 458+, this is more meaningful
  evidence that LP-UB-478 is a robust ceiling across families.

## ALNS push on 3 LP-UB-478 basins (results)

Ran 16 ALNS-diverse seeds, 10 min each, with t=0.5 temperature:

| Basin (start score) | Seeds | Best | Lift |
|---|:---:|:---:|---:|
| lo_00001 / s457 / family A* | 8 | 457 | **+0** |
| lo_f452 / s455 / family LO | 4 | 455 | **+0** |
| lo_f150 / s454 / family LO | 4 | 455 | +1 (2 of 4) |

**Each basin is at or near its ALNS-local-optimum**, regardless of
the LP-UB-478 ceiling. The 478 cap is genuinely LP relaxation slack
+ piece-uniqueness commitment, not achievable headroom for our
search style.

## Implication

To break 458 within LP-UB-478, we need either:
- **Different operators** (mega_mix, kempe chains, etc.) — ALNS-diverse
  has already been tested.
- **Longer compute** per basin (30-60 min) on lo_00001 specifically
  (the closest-related basin to vol-32 458).
- **Higher LP UB basin** — not yet found, but might exist in our
  4746-board archive among lower-score classes (need to test).

The vol-32 458 basin is special: only basin sampled where score
EQUALS the apparent local-opt under our operators.

## Open questions

- How many distinct LP-UB-478 basins are there in our 4746-board
  archive? (Could compute by clustering boards with bb=60 + LP UB 478
  by their border fingerprint.)
- Are there basins with LP UB > 478? (Would require sampling much
  more.)
- Within a single LP-UB-478 basin, does cluster-repair give the same
  delta=0 result as the vol-32 458 basin? (If yes, the basin is at
  its local optimum, which is its score. If no, ALNS can push it.)

## Linked

- [[458-class-A-mismatch-structure]]
- [[border-class-geometries]]
- [[vol-44]] — session
