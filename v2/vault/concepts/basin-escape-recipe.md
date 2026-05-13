# Basin-escape recipe (bound + Hungarian + ALNS)

**Status**: `built` (vol-22)
**Origin**: vol-22 (composite of vol-21 building blocks)
**Files**: `scripts/v22_basin_jump_recipe.sh`

## The recipe

1. **Bound-ascent** N iters from any board → output/v21_bound_ascent_b<bound>_s<score>.json
2. **Hungarian bipartite matching** against the bound-ascended state's relaxed target → output/v21_target_match_<score>.json (preserves high bound)
3. **ALNS recovery** from the matched board (60s) → score-climb in new basin

## What it does

Escapes the [[operator-lock]] at 457. Produces NEW basins with ceilings up to 471 (Hamming 72+ from our 457).

## The vol-22 ALNS-saturation gap

| Basin start | Bound | ALNS-PT plateau (15-30 min) | Gap |
|---|---|---|---|
| 457 (ours, saturated by hours) | 461 | 457 | -4 |
| 440/469 (fresh, vol-22) | 469 | 442 | -27 |
| 426/458 (fresh) | 458 | 426 | -32 |
| 414/454 (fresh) | 454 | 414 | -40 |

Saturation gap = (basin ceiling) − (ALNS-PT plateau).
Our 457 basin has the smallest gap because it was ALNS-saturated by hours of search.

## What WORKED (vol-22)

- Recipe consistently produces high-bound basins.
- 440/469 basin verified: 256 unique pieces, valid placement, basin ceiling 469 = community record.

## What DIDN'T WORK

- 60s ALNS recovery: 440 score.
- 5-min hot-PT: 442 score, bound dropped 469 → 462.
- 15-min hot-PT: 442 score, bound 462.
- 30-min hot-PT: 442 score, bound 463.
- Bound-floor ALNS on the basin: 0/15 attempts preserved bound floor.

**Conclusion**: ALNS-PT can't push the 469 basin past 442 in 30 min. Either need hours (overnight test PID 66809 ongoing) or stronger repair ([[prune-restart]]).

## Linked concepts

- [[bound-ascent]] — step 1 of the recipe
- [[relaxed-bound]] — the metric being preserved
- [[prune-restart]] — the missing repair that should close the saturation gap
- [[operator-lock]] — what gets escaped

## Linked basins

- [[basin-440-469]] — the breakthrough vol-22 basin
- [[basin-457-pt]] — our locked starting basin
