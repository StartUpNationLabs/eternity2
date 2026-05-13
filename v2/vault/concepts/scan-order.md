---
tags: [concept, search-order]
status: built
origin-vol: 4
---

# Scan order

**Status**: `built` (multiple variants, refuted alternatives logged)
**Files**: `crates/solver-engine/src/lib.rs` (`ScanOrder` enum)

## Variants shipped

| Variant | Vol | Description |
|---|:--:|---|
| `BorderFirstMRV` | 1 | corners, then border ring (MRV), then interior MRV (default) |
| `RowMajorTopDown` | 1 | (0,0) → (0,15) → (1,0) → …  |
| `RowMajorBottomUp` | 15 | (15,0) → (15,15) → (14,0) → …  (Blackwood) |
| `SpiralFromCenter` | 14 | spiral outward from center cell |
| `HintCentric` | 14 | from canonical hint cells outward |

## Refuted alternatives

### Hint-centric (vol-14, NULL)

A/B at 60s on canonical E2:
- Hint-centric: depth 42 / 62 matched.
- Border-first MRV: depth 164 / 282 matched.

The hint-centric hypothesis (start where information density is highest) was empirically correct in geometry but **causally wrong**: deep center cells under canonical hints have HIGH domain (~764, the 764-plateau), not low. Hint-centric prioritizes high-domain cells, which is exactly wrong for CSP.

**Border-first MRV is the correct CSP strategy.** Scan-order correlation with mismatch geometry is empirical, not causal.

### CHESS heuristic (vol-1, NULL)

Ansótegui et al. 2008 CHESS static order (checkerboard cells, center-spiral). Without full Régin alldiff filter: **600× node explosion**. Requires bounded-width CSP which E2 lacks; not viable.

### X-skeleton, 3-cell-wide diagonals (vol-23, NULL)

User-proposed `PathSkeleton::XSkeleton`: pre-commit two 3-cell-wide diagonals through the 5 canonical hints (TL → centre → BR, TR → centre → BL), then Chebyshev-outward fill. The geometric hypothesis was distinct from rectangle/layered: instead of *wrapping* the 764-plateau, the X **pierces** it in two crossing bands so each diagonal cell has two already-placed neighbours.

A/B at 5min CP + 10min ALNS on canonical E2 (seed 1):

| Stage | X-skeleton | baseline (vol-17 calibrated_v17a cold-start) |
|---|---|---|
| CP depth | 69 | ~164 |
| CP placed | 74/256 | ~280/256 |
| CP matched | 105/480 | ~280/480 |
| Final (post-ALNS) | **396/480** | **447/480** |

**Refuted by 51 matched edges.** The "piercing" geometry did not save it; it made the CP stage *worse* than perimeter-shaped pre-commits because the engine spent its budget thrashing on center cells where domains are widest (the 764-plateau, [[mismatch-geometry]]). The +291 ALNS lift only recovered partial ground.

Files: `crates/solver-engine/src/lib.rs` (`PathSkeleton::XSkeleton`, `build_x_skeleton_path`, `JOE_DEPTH150_BP_X_PAR`), `crates/bench-audit/src/bin/run_e2_x_skeleton.rs`.

**Generalisation**: every static pre-commit through high-domain interior cells has lost — hint-centric (vol-14), rectangle/layered (vol-14, vol-15), X-skeleton (vol-23). The pattern: **static ordering chooses which region becomes the hard region; piercing the 764-plateau makes the hard region the widest-domain cells**. Border-first MRV remains the only ordering that lets the engine attack low-domain cells first.

## Mismatch-geometry consequence

Scan order **determines** where mismatches accumulate (see [[mismatch-geometry]]):
- Top-down → mismatches at center-BOTTOM (vol-6, vol-14).
- Bottom-up → mismatches at TOP (vol-17 calibrated_v17a, community 469s).
- Spiral-from-center → mismatches at corners (vol-14 test).

Choosing scan order chooses **which region is the hard region**. Optimal scan order is still open: it's not a property of the puzzle but of the interaction between scan + propagators + hints.

## Linked concepts

- [[frame-first]] — alternative decomposition that sidesteps the scan-order question on the border
- [[mismatch-geometry]] — what scan order determines
- [[blackwood-algorithm]] — uses `RowMajorBottomUp`

## Linked memory

- `project_e2_vol14_hint_centric_null`
- `project_e2_vol14_scan_order_analysis`
- `project_e2_vol14_mismatch_geometry_universal`
