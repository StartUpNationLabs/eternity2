---
tags: [basin, vol-14, post-bug-fix-invalidated]
status: invalidated
score-reported: 443
score-true: ~440
---

# Basin 443-vol14 (BP-seeded — post-bug-fix invalidated)

**Score reported**: 443/480 (broken-binary measurement)
**Score true**: ~440/480 (post [[hint-pinning-bug]] fix)
**Representative file**: `output/alns_e2_1778592162_443of480.json` (invalidated)

## Discovery

Vol-12 baseline cold-start (CP→ALNS) → 443/480. Vol-14 EdgeBpMarginals + ALNS-fill → 443/480 (tie).

## ALNS hint-pinning bug

The vol-14 audit found that `alns_e2` was UNPINNING canonical hints during destroy. All measurements at this score level were on the wrong puzzle. Fixed in commit `afb3dc9`. See [[hint-pinning-bug]].

True post-fix baseline: ~440. The qualitative finding (BP-seeded > baseline in pipeline) still holds; the absolute number was inflated by ~3.

## Mismatch geometry

All 37 mismatches form **ONE connected cluster** in rows 4-14 × cols 2-12 (perimeter + upper interior + bottom row are perfect). k=5 ALNS repair too small for the cluster.

## Why it's documented despite invalidation

Vol-14 used this board for:
- **Backtrack-distribution instrumentation** (layer-3 shoulder peak finding).
- **The 764-plateau** measurement (~175 interior cells at max domain after hints+AC3).
- **PT-from-443 push** test (reached 446 mid-session, but seed itself was buggy).

The structural findings ([[mismatch-geometry]] cluster, [[scan-order]] dependency) are real; the absolute score was wrong.

## Sister basins

- [[basin-457-pt]] — true post-fix cold record
- [[basin-447-top-row]] — vol-17 calibrated-Blackwood record (different geometry)
- [[basin-454-vol6]] — warm record (different scan order)

## Linked concepts

- [[hint-pinning-bug]]
- [[mismatch-geometry]] — cluster + 764-plateau findings
- [[edge-bp-marginals]] — what produced the BP-seeded variant

## Linked memory

- `project_e2_vol14_443_mismatch_geometry`
- `project_e2_vol14_alns_hint_bug`
- `project_e2_vol14_initial_domain_map`
- `project_e2_vol14_backtrack_distribution`
