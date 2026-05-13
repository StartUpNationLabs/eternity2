---
tags: [concept, diagnostic, topology]
status: built-loose-signal
origin-vol: 19
---

# Mismatch homology (β_1 of mismatch graph)

**Status**: `built` (vol-19); signal is small
**Origin**: vol-19 (R5 reframing)
**Files**: `scripts/measure_betti.py`, `scripts/measure_components.py`

## Definition

Build the **mismatch graph** of a partial board:
- **View A**: vertices = cells; edges = mismatched edges between cells.
- **View B**: vertices = mismatched edges; edges = shared-cell adjacency.

Compute β_0 (component count) and β_1 (cycle rank).

## Vol-19 measurements

- **View A β_1 = 0** on all boards examined. Mismatch edges form a forest. No topological cycles.
- **View B β_1 = 5–12** on plateau boards (measures region cyclomatic complexity).
- Interior perfect-cell islands: **1–2 per board**.

## Verdict

The β_1=0 result rules out **CycleDestroy** (an ALNS operator targeting topological cycles in the mismatch graph). If there are no cycles, there's nothing to destroy.

The signal is smaller than initially hoped. β_0 (component count) carries more information: the [[mismatch-geometry]] fracture threshold uses component count, not β_1.

## What's still potentially useful

- View-B β_1 as a complexity diagnostic when comparing boards.
- Higher-dimensional homology on a 3D lift (depth × position × orientation)? Unbuilt, speculative.

## Linked concepts

- [[mismatch-geometry]] — the geometry layer that absorbed this finding
- [[r5f-cooperativity]] — the actual physics signal at the 447→456 barrier

## Linked memory

- `project_e2_vol18_r5_homology`
