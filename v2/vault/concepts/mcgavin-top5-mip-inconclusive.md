---
name: mcgavin-top5-mip-inconclusive
description: Top-5-rows MIP on McGavin 469 didn't finish — 600s time limit hit with 0 B&B nodes explored, 1745% gap. Best feasible = current 144 (no improvement) but NOT a proof. Honest null result.
metadata:
  type: project
---

# Top-5-rows MIP on McGavin 469 — INCONCLUSIVE (vol-84)

**Status**: `partial` — time-limited, did NOT prove optimality.
**Origin**: vol-82 found basin asymmetric → top-5-rows is the hard
sub-problem; vol-83 proved halo-1 optimality; vol-84 attempted to
extend to the 80-cell top-5-rows region.

## Setup

- Board: `output/vol-65/mcgavin_469.json` (score 469/480).
- Cluster: rows 0-4 = 80 cells.
- Tool: `repair_region` (cluster_repair under the hood).
- MIP size: **28,674 binary vars**, 6,292 rows, 139,342 nonzeros.
- Time limit: 600s HiGHS.

## Result

- Best feasible solution: obj=144 (identical to McGavin's current
  top-5 contribution). **delta = +0**.
- Dual bound: 2657 (LP relaxation, very loose).
- **Gap: 1745%** at termination.
- **B&B nodes explored: 0** (still in root LP/simplex phase).
- HiGHS status: Warning (time limit hit).

## What this means

**NOT a proof.** Unlike vol-83's halo-1 result (which finished with
+0 in 895s and proved optimality), this 80-cell MIP:
- Found NO improvement (delta=+0 best feasible)
- But ALSO did not prove +0 is the maximum

The dual bound 2657 is the LP relaxation; 1745% gap means the LP
can't even bound the integer optimum to within 50× of the
feasible. HiGHS spent all 600s in the root LP simplex.

## Why so slow

- 28k binary vars vs vol-83's ~6k → 5× more vars.
- 6.3k constraints vs vol-83's ~1.5k.
- Single MIP node not even started.
- Edge-matching MIP has weak LP relaxation (the "color must match"
  constraint is naturally fractional-friendly).

## What this leaves open

- **McGavin's top-5 MIGHT be improvable** — vol-84 only ran 10 min.
  An hours-long run, OR a tighter formulation, OR a smaller
  sub-cluster could resolve this.
- **Strong indirect evidence top-5 is locally optimal** — combined
  with vol-83 (halo-1 +0), the search inside the 37-cell joint
  region around mismatches found nothing. Top-5 contains that
  region plus extra; finding improvement OUTSIDE the joint region
  but INSIDE top-5 would be a non-local-yet-localized move.

## Sharper version to try

- **Top-3-rows MIP**: 48 cells × 256 pieces × 4 rotations ≈ 17k
  binary vars. ~30% smaller. Might finish in 10 min.
- **Per-row MIP**: rows 0, 1, 2, 3, 4 individually (16 cells each).
  5 small MIPs, each 4k binary vars. Tractable.
- **Lagrangian decomposition**: split top-5 into 5 row-MIPs with
  Lagrangian penalties for row-row matching. Tractable.

These would give a sequence of progressively tighter bounds,
narrowing whether the top-5 can be improved.

## Provisional read

Combined with vol-83's halo-1 proof: **likely** McGavin's top-5 IS
optimal under current configuration. But not yet proven. Marking
as `partial` for vault discipline.

## Linked

- [[mcgavin-mip-local-optimal-halo1]] (parent: halo-1 PROVEN)
- [[mcgavin-basin-top-bottom-symmetry]] (motivated this experiment)
- [[mcgavin-469-mismatch-geometry]]
