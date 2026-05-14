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
