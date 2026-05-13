---
tags: [concept, structural-invariant, diagnostic]
status: built
origin-vol: 4
---

# Mismatch geometry (where errors live)

**Status**: `built` (vol-4 universal mismatches, vol-14 cluster geometry, vol-17 top-row, vol-19 fracture threshold, vol-20 scan-order correction)
**Origin**: vol-4
**Files**: `scripts/universal_mismatches.py`, `scripts/v4_plateau_analyze.py`, `scripts/measure_betti.py`, `scripts/measure_components.py`, `scripts/analyze_mismatch_geometry.py`

## Vol-4: universal mismatches

29 plateau boards across 6 solver families: top-6 universal-mismatch edges occur in **47-63% of boards**. Hot spot: **rows 10-13, columns 4-13** (south-central). Strain-cascade hypothesis: the asymmetric (7,8) hint warps the search backwards toward this region.

## Vol-14 cluster geometry on our 443

All 37 mismatches in BP-seeded 443/480 board form **ONE connected cluster** in rows 4-14 × cols 2-12 (perimeter + upper interior + bottom row are perfect). k=5 ALNS repair was too small for this cluster.

## Vol-14 mismatch geometry is search-order-determined

| Board source | Score | Hard region |
|---|---:|---|
| Vol-14 BP-seed | 443 | center-BOTTOM |
| Vol-6 PT-warm | 454 | center-BOTTOM |
| Community 469/468 | 469 | TOP |

**Same puzzle, different hard regions** depending on whether the search is top-down or bottom-up. The cluster geometry is **scan-order-determined**, not a property of the puzzle. Community 469s won't warm-start our top-down stack.

## Vol-17 top-row geometry

`calibrated_v17a` 447/480 (cold-start record): all 33 mismatches in **rows 0-3** forming one 51-cell connected component; rows 5-15 perfect.

**Inverts vol-6/vol-14**. The calibrated Blackwood schedule (row-major bottom-up scan) pushes failures to the TOP, matching the community 469 geometry. The unbuilt ALNS operator for this regime: band-destroy on rows 0-3, or k=80 ConflictDriven.

## Vol-19 fracture threshold

- 441/480 boards: **single massive 70-cell mismatch component**.
- 454/480 boards: **5-7 small mismatch islands**.

The structural transition between "stuck" and "near-solution" is a fracture event: the giant component breaks into islands. β_1 = 0 on all boards (no topological cycles); the component count is the diagnostic.

## Vol-20 backbone correction

Cross-scan-order TD vs BU portfolio:
- Vol-17 claimed an 18/17-cell "backbone" of cells with cross-board consensus.
- Vol-20 measured: only **5 canonical hints** have true structural cross-source agreement. The 12 "bottom-left backbone" cells are basin-specific scan-order artefact, not puzzle-structural.

## Vol-20 backtrack distribution (instrumented engine)

| Region | % of backtracks |
|---|---:|
| Corners | 0% |
| Border | 5% |
| Layer 1 (just-inside-border) | high |
| **Layer 3 (shoulder)** | **peak 124 bt/cell** (12× perimeter) |
| Deep interior | ~5% |

→ Border-ring ambiguity is NOT the bottleneck. The **shoulder region (layer 3)** is. This re-aimed vol-21+ at layer-3-targeted operators.

## Vol-20 initial domain map (the 764-plateau)

After hints+AC3:
- ~175 interior cells **all have domain = 764** (max).
- Border 56 cells: domain ~56.
- Corners 4: domain 4.
- Hint-adjacent 42-48.

The 764-plateau **IS** the search problem. Hint-centric scan order failed (vol-14) because deep center has HIGH intrinsic domain (764), not low. Pre-search propagators that chip the plateau (lookahead-1, k-consistency, Blackwood color schedule) are the only known lever.

## Linked concepts

- [[scan-order]] — why mismatch geometry depends on it
- [[blackwood-algorithm]] — why community boards have TOP-region failures
- [[mismatch-homology]] — vol-19 β_1 measurement that ruled out cycle-destroy
- [[r5f-cooperativity]] — the 76-cell first-order barrier discovered

## Linked memory

- `project_e2_vol14_443_mismatch_geometry`
- `project_e2_vol14_mismatch_geometry_universal`
- `project_e2_vol14_backtrack_distribution`
- `project_e2_vol14_initial_domain_map`
- `project_e2_vol17_447_top_mismatch`
- `project_e2_vol18_r5f_cooperativity`
- `project_e2_vol20_backbone_correction`
