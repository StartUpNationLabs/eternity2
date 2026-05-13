---
tags: [basin, vol-4, first-break]
status: historic
score: 450
---

# Basin 450-vol4 (first break of the 449 plateau)

**Score**: 450/480 — first basin to score > 449 cold-start
**Discovery**: Vol-4, frame-first decomposition with border-seed `0xCAFEFEEF`
**Representative file**: vol-4 output

## Why this basin matters

Until vol-4, every solver — CP, PT, ALNS, GA — saturated at 449. Vol-4 demonstrated that **changing the border ring** (not the interior search) breaks the plateau.

The result is small (+1) but qualitatively important: it proved [[prefix-determinism]] is the upstream lock, and the [[border-diversity]] axis is the lever.

## Geometry

Fresh basin B with ~19% bucas overlap with the canonical 449-basin family. Different basin family entirely.

## What followed

- Vol-5 GA-cross within this family → 452.
- Vol-5 GA-LARGE 3-hour cascade across 2-3 basin families → 453.
- Vol-6 pt_e2 --pin-perimeter from corpus border + 453 seed → [[basin-454-vol6]] (454 record).

## Sister basins

- [[basin-454-vol6]] — the warm-PT extension of the same line of thinking
- Multiple unnamed 451-452 basins in vol-5 (within this family)

## Linked concepts

- [[frame-first]] — what produced this basin
- [[prefix-determinism]] — what this basin's existence refuted as universal
- [[border-diversity]] — the axis vol-6 systematized

## Linked memory

- `project_e2_state` (vol-4 row)
