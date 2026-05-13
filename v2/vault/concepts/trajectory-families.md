---
tags: [concept, structural, key-insight]
status: built
origin-vol: 18
---

# Trajectory families (basin configuration distance ≠ score distance)

**Status**: KEY INSIGHT (vol-18)
**Origin**: vol-18

## Statement

Boards with similar scores can be in **structurally distant basins**. Vol-18 measurement:

| Pair | Score | Hamming (piece-position) | Region overlap |
|---|---:|---:|---:|
| 454 (chunk_0019 CP partial) vs 456 (basin A) | 454, 456 | 88% disagree | 43% region match |
| 457 (our PT) vs 456 (basin B) | 457, 456 | 72 cells | low |

## Implications

1. **Score-distance ≠ configuration-distance.** A 456 board near our 457 in score may be 72 cells away in configuration.
2. **Cross-family σ-cycles are 88-218 cells with Δ up to -171.** These cannot be traversed by local moves.
3. **Only within-family OracleCycleSwap makes sense.** Cross-family swaps put pieces into the wrong half of the board.

## 456 unreplicable on chunk_0019 (vol-18)

3 seeds on chunk_0019 CP partial all landed at 449-454; **456 is not in chunk_0019's reachable basin set**. The 456 board came from a DIFFERENT (pre-overnight) CP partial.

→ Basins are CP-partial-specific. Each CP partial defines a different reachable set.

## Vol-22 ALNS-saturation gap maps onto trajectory families

The vol-22 [[basin-escape-recipe]] table:
- 457 (saturated) gap = −4.
- 440/469 (fresh) gap = −27.
- 426/458 gap = −32.

Saturated basins have small gaps because hours of search have exhausted within-family moves. Fresh basins have large gaps because ALNS has barely started exploring within-family.

## Linked concepts

- [[basin-escape-recipe]] — produces basins in different trajectory families
- [[oracle-cycle-swap]] — operator only valid within family
- [[basin-440-469]] — a fresh-family basin
- [[basin-457-pt]] — our saturated home basin

## Linked memory

- `project_e2_vol18_trajectory_families`
- `project_e2_vol18_456_unreplicable`
