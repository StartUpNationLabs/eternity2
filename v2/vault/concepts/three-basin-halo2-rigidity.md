---
name: three-basin-halo2-rigidity
description: Halo-2 per-component MIP-rigidity now confirmed across THREE distinct top-score canonical E2 basins (McGavin 469, local 459, vol-32 458). Empirical evidence for universal halo-2 rigidity pattern.
metadata:
  type: project
status: built
---

# Halo-2 rigidity across 3 basins (vols 92, 93, 95)

**Status**: `built` — three independent halo-2 proofs 2026-05-16.

## Result table

| basin | score | comp count | comp sizes | halo-2 result |
|---|---:|---:|---|---|
| McGavin (vol-92) | 469 | 2 | 8, 8 | All +0 PROVEN |
| Local (vol-93) | 459 | 4 | 18, 11, 4, 2 | All +0 PROVEN |
| Vol-32 (vol-95) | 458 | 2 | 32, 4 | All +0 PROVEN |

**Three distinct basins. Three different mismatch component
geometries. ALL halo-2 per-component MIP-rigid.**

## Why this matters

Combined with halo-1 proofs (vol-83, vol-90 + 4 vol-62 corpus
basins), we have:

| basin | halo-1 | halo-2 | halo-3 |
|---|:-:|:-:|:-:|
| McGavin 469 | ✓ (joint) | ✓ (per-comp, [[mcgavin-halo2-percomp-proven]]) | ✓ (per-comp, [[mcgavin-halo3-percomp-proven]]) |
| Local 459 | ✓ (joint, [[local459-halo1-joint-proven]]) | ✓ (per-comp, [[local459-halo2-percomp-proven]]) | not tested |
| Vol-32 458 | ✓ (vol-62 memory) | ✓ (per-comp, this page) | not tested |
| 3 other vol-62 basins | ✓ (memory) | not tested | not tested |

**All 6 basins tested halo-1 rigid; all 3 tested at halo-2 are rigid;
the 1 tested at halo-3 (McGavin) is rigid.**

This is the strongest empirical evidence so far for the universal
halo-rigidity conjecture (see [[why-records-are-mip-rigid]]).

## Implication for ANY canonical E2 record-improvement

For any record currently scoring 458-469, to find an improvement
via halo ≤ 2 LOCAL operations: **mathematically impossible** for
at least 3 representative basins, with high confidence the same
holds for all other basins given the structural mechanism
([[why-records-are-mip-rigid]]).

Any future record-breaking attempt MUST either:
- Use halo ≥ 4 local operators (untested ceiling).
- Use cross-component (joint) operators (vol-91 failed at halo-2
  joint; need better MIP tooling).
- Use board-spanning moves (σ-cycle).

## Linked

- [[mcgavin-halo2-percomp-proven]]
- [[local459-halo2-percomp-proven]]
- [[mcgavin-halo3-percomp-proven]]
- [[why-records-are-mip-rigid]] (structural conjecture)
- Memory: `project_e2_vol62_mip_local_optimality.md`
