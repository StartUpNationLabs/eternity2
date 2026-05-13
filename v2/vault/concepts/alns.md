---
tags: [concept, local-search, metaheuristic]
status: built-extended
origin-vol: 5
---

# ALNS (Adaptive Large-Neighborhood Search)

**Status**: `built` (vol-5 light, vol-17 portfolio of 10 ops, vol-20 measurement)
**Origin**: vol-5 (initial light variant), vol-17 (multi-op portfolio)
**Files**: `crates/localsearch/src/alns.rs`, `crates/bench-audit/src/bin/alns_e2.rs`, `alns_only`, `alns_pt_multi_init`

## Definition

Destroy-repair local-search metaheuristic:
1. **Destroy**: pick K cells (per a destroy operator), unplace them.
2. **Repair**: rebuild placements (greedy + CP fill, or random restart).
3. **Acceptance**: keep new state if score improves (or under SA temperature).
4. Adapt operator weights from success rate.

## Operators we've shipped

| Op | Vol | Description |
|---|:--:|---|
| RandomCells | 5 | uniform random K cells |
| MismatchedCells | 5 | cells incident to mismatched edges |
| ConflictDriven{K} | 17 | top-K conflicting cells (K up to 80) |
| **WorstBand** | 17 | the row band with most mismatches |
| **WorstRow** | 17 | the single worst row |
| **ComponentDestroy** | 17 | one connected component of the mismatch graph |
| **ComponentPlusHaloDestroy** | 17 | component + halo radius 1 |
| **HingeDestroy** | 17 | Tarjan articulation points of mismatch graph |
| RectangleDestroy | 14 | k×k rectangle of cells |
| LayeredDestroy | 14 | concentric rings of cells |

WorstBand + ConflictDriven{80} composition produced the **vol-17 cold-start record 455/480** (seed 1) on top of `calibrated_v17a` Blackwood seed.

## Critical bug discovered in vol-14

`alns_e2` was UNPINNING canonical hints during destroy. All vol-12/vol-14 ALNS-fill scores (442/443/436) were on the wrong puzzle. Fixed in commit `afb3dc9`. True baseline post-fix is ~440 (not 443). See [[hint-pinning-bug]] / `project_e2_vol14_alns_hint_bug`.

## H6 op-dilution finding (vol-17)

11 operators (vol-17 max) > 5 operators (curated): **−1 matches**. More ops dilutes the adaptive weighting; the algorithm spreads exploration too thin. Op selection should be tight, not exhaustive.

## H9 temperature-insensitivity (vol-17)

`temperature t ∈ [0.5, 5.5]` all produce identical scores end-to-end. **ALNS on E2 plateaus is iso-score**: 100% Metropolis acceptance regardless of T. Temperature is not the lever.

## Saturation behavior (vol-22)

ALNS-PT plateau in fresh basins: −25 to −32 from basin ceiling, depending on basin. ALNS-PT plateau in saturated basins: −4 ([[basin-457-pt]]). See [[basin-escape-recipe]] table.

→ ALNS is a **basin-explorer**, not a **basin-solver**. It saturates short of the bound. The fix is either many more hours per basin (overnight test 2026-05-13) or stronger repair ([[prune-restart]]).

## Saturation plateau hits iter ~33 of 400 (vol-17 H10)

10-min ALNS vs 5-min ALNS: identical final score; best-score history flat after iter ~33. **Wall-clock is not the lever past the saturation point.**

## Linked concepts

- [[parallel-tempering]] — PT chains compose with ALNS as outer loop
- [[basin-escape-recipe]] — the composition that uses ALNS post-Hungarian
- [[hint-pinning-bug]] — the vol-14 critical bug
- [[prune-restart]] — the repair we're missing

## Linked memory

- `project_e2_vol14_alns_hint_bug`
- `project_e2_vol22_basin_escape`
