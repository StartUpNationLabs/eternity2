---
tags: [concept, operator, partial-refuted]
status: refuted-as-standalone, used-in-pipeline
origin-vol: 18
---

# Hungarian/optimal-transport repair

**Status**: `refuted` as standalone (vol-18 R3); USED in [[basin-escape-recipe]] (vol-22)
**Origin**: vol-18 R3 reframing
**Files**: `crates/bench-audit/src/bin/edge_target_match.rs`

## Definition

Given current placement and a target piece-distribution, compute the **Hungarian / Kuhn-Munkres** optimal piece-to-cell assignment under a cost function (edge-mismatch count, or relaxed bound, or distance to target).

Two phrasings:
- **Iterative OT (Sinkhorn-style)**: soft assignment, gradient descent over piece-cell coupling.
- **Hungarian discrete**: exact bipartite matching.

## Vol-18 R3 standalone result — REFUTED

5 seeds × 30s each, starting from CP partials:
- **Strict valley-finder**: always descends, never ascends.
- **Stuck at 453/447 fixed points** across all seeds.
- **1000× faster** than ALNS per iteration, but **useless without barrier-crossing**.

→ Standalone Hungarian repair = local valley-finder. Cannot escape any basin.

## Vol-22 use in [[basin-escape-recipe]]

The Hungarian step IS useful as the **middle step** in the recipe:
1. [[bound-ascent]] (climbs relaxed-bound, drops score).
2. **Hungarian match against bound-ascended target** (preserves high bound, recovers some score).
3. [[alns]] recovery (further score climb in new basin).

The Hungarian step's role: **fast deterministic conversion** from high-bound configuration to high-score configuration within the same basin. Not an escape operator on its own.

## Why both readings are correct

- **Standalone**: deterministic descent. Refuted as escape.
- **In pipeline**: deterministic descent IS the useful property — it gives ALNS a clean starting state with structure preserved from the bound-ascent.

## Linked concepts

- [[basin-escape-recipe]] — where it succeeded
- [[bound-ascent]] — the predecessor step
- [[relaxed-bound]] — the metric Hungarian matches against

## Linked memory

- `project_e2_vol18_r3_ot_null`
- `project_e2_vol22_basin_escape`
