---
name: local459-halo2-percomp-proven
description: Local 459 PROVEN per-component MIP-optimal at halo r=2 across all 4 components. Matches McGavin pattern (vol-92). Confirms basin asymmetry doesn't affect rigidity.
metadata:
  type: project
---

# Local 459 — per-component halo-2 PROVEN (vol-93)

**Status**: `built` — PROVEN 2026-05-16 ~02:33.
**Tool**: `vol62_cluster_mip_bound --radius 2`.
**Files**: `output/vol-93-local459-percomp-halo2/log.txt`.

## Result

Local 459 has 35 defect cells in 4 components. Per-component MIP
at halo r=2:

| comp | core defects | halo size | delta | obj | time |
|---:|---:|---:|---:|---:|---:|
| 0 | 18 | 35 | **+0** | 72 | 600s |
| 1 | 11 | 35 | **+0** | 76 | 121s |
| 2 | 4  | 13 | **+0** | 30 | 0.1s |
| 3 | 2  | 17 | **+0** | 39 | 0.2s |

**All 4 components delta=+0** at halo r=2.

Status: "This basin is MIP-locally optimal at every tested radius."

## Significance

Combined with vol-90 (halo-1 joint, 59 cells, +0 proven) and
vol-88/89 (bottom-rows, smaller regions, +0 proven):

**Local 459 is rigorously proven rigid against ANY local move with
halo ≤ 2 PER-COMPONENT (joint halo-2 still open).**

This exactly matches McGavin's pattern (vol-83 halo-1 joint +
vol-92 halo-2 per-comp). The structural rigidity is symmetric:
- McGavin 469: 2 components, halo-1 joint + halo-2 per-comp PROVEN
- Local 459: 4 components, halo-1 joint + halo-2 per-comp PROVEN

The maximally-adversarial thesis (per [[why-records-are-mip-rigid]])
extends to halo-2 for both records.

## Linked

- [[local459-halo1-joint-proven]] (halo-1 joint)
- [[local459-mip-bottom-rigid]] (smaller-region proofs)
- [[mcgavin-halo2-percomp-proven]] (matching McGavin pattern)
- [[why-records-are-mip-rigid]] (structural conjecture)
