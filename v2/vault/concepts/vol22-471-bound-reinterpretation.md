# Vol-22 "471-bound" basins reinterpretation — vol-73 (2026-05-15)

**Status**: `built` (corrects vol-22 over-interpretation).
**Origin**: 5-min ALNS test on vol-22's `b471` boards.

## Vol-22 claim

Memory entry `project_e2_vol22_basin_escape` claimed:
> Basin-escape recipe (bound-ascent → Hungarian → ALNS) found basins
> with **ceilings up to 471**. ALNS-PT plateau in fresh basins is
> ~25-30 BELOW the ceiling.

The "ceiling 471" comes from `edge_bound_ascent`'s output — relaxed
bound increased to 471 via 2-piece-swap chains.

## Today's test

Took `output/v21_bound_ascent_b471_s360.json` (starting score 360,
"bound 471"). Ran ALNS-only winning5 for 5min × 4 seeds:

| seed | final score |
|---|---|
| 1 | 430 |
| 7 | 411 |
| 42 | 422 |
| 100 | 418 |

Max: 430/480. **NOWHERE NEAR 471.**

## What's wrong

CLAUDE.md rule 1 explicitly says: `relaxed_bound` is NOT a sound
upper bound on integer matched-edge score. It's a greedy-relaxed
heuristic that allows piece-reuse — frequently above achievable.

The vol-22 "ceiling 471" is the relaxed-bound value at that
specific board state. **It is NOT an upper bound on what ALNS can
achieve in that basin.** ALNS achieves 411-430. The actual ceiling
is some unknown lower value.

## Implication for other vol-22 claims

The vol-22 memory's "basins with ceilings up to 471" should be
read as: "bound-ascent produced boards where the heuristic
greedy_relaxed_score evaluates to 471". This is NOT the same as
"these basins admit 471 score under careful search".

The actual reachable scores in these basins are 411-442 (per
vol-22 plateau measurement). 442 max < 459 standing record.

## What this means for breaking 459

Vol-22 basin-escape recipe doesn't help. The "new basins" it finds
have LOWER achievable scores than our standard pipeline's 458-459.

The bound-ascent strategy is REFUTED as a productive direction for
beating 459.

## Linked

- memory: project_e2_vol22_basin_escape (claim to revise)
- CLAUDE.md rule 1: relaxed_bound is NOT a sound bound
- vault: [[e2-maximally-adversarial-thesis]]
