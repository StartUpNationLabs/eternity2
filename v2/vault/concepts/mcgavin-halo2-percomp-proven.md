---
name: mcgavin-halo2-percomp-proven
description: McGavin per-component MIP-optimality EXTENDED to halo r=2. Component 0 (29 cells, 5.4s) and component 1 (34 cells, 147.6s) both delta=+0. Each component's halo-2 region rigid.
metadata:
  type: project
---

# McGavin per-component halo-2 — PROVEN (vol-92)

**Status**: `built` — PROVEN 2026-05-16 ~02:21.
**Tool**: `vol62_cluster_mip_bound` with `--radius 2` (no joint).
**Files**: `output/vol-92-mcgavin-percomp-halo2/log.txt`.

## Result

McGavin's 469 has 16 defect cells in 2 components of 8 each.
Per-component MIP at halo radius r=2:

| comp | core | r | size | delta | obj | time |
|---:|---:|---:|---:|---:|---:|---:|
| 0  | 8  | 2 | 29 | **+0** | 65 | 5.4s |
| 1  | 8  | 2 | 34 | **+0** | 74 | 147.6s |

Status: "This basin is MIP-locally optimal at every tested radius."

## Significance

Extends vol-83's halo-1 joint proof in a different direction:
- **vol-83 halo-1 joint**: all 16 defects + halo r=1 = 37 cells,
  delta=+0 (895s).
- **vol-92 halo-2 per-component**: each component + halo r=2,
  delta=+0 (max 147s).

vol-92 proves that **each component's halo-2 neighbourhood is
independently rigid**. Combined with vol-83, McGavin's 469 is
rigid against:
- Any halo-1 joint move across both components.
- Any halo-2 move WITHIN a single component (does not allow
  cross-component swaps at radius 2).

## What vol-92 does NOT prove

- **Joint halo-2**: would require cross-component swap at radius 2.
  Vol-91 attempted this (54-cell joint region) and FAILED — HiGHS
  stuck at root LP for 55 min. Joint halo-2 question remains open.
- Halo-3 per-component would test larger neighbourhoods.

## Combined McGavin local-optimality proofs

| vol | what | cells | delta | time |
|----:|---|---:|---:|---:|
| 83 | halo-1 joint | 37 | +0 PROVEN | 895s |
| 85 | top-3 rows | 48 | +0 PROVEN | 70s |
| 92 | halo-2 per-component | 29+34 | +0 PROVEN | 153s |
| 86 | top-4 rows | 64 | bounded ≤ 123 | 1200s |
| 91 | halo-2 joint | 54 | FAILED (stuck) | killed |
| 84 | top-5 rows | 80 | FAILED (stuck) | timeout |

**Local-optimality regions proven**: 37 ∪ 48 ∪ (29 + 34) cells, plus
the top-4 bounded above by 123.

## Linked

- [[mcgavin-mip-local-optimal-halo1]]
- [[mcgavin-top3-mip-proven]]
- [[mcgavin-top4-mip-bounded]]
- [[why-records-are-mip-rigid]]
