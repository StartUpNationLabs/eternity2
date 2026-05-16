---
name: mcgavin-halo3-percomp-proven
description: McGavin per-component MIP-optimality EXTENDED to halo r=3. Both components proven +0 (42-cell region in 329s, 47-cell in 600s). Rigidity proven at every halo radius tested up to 3.
metadata:
  type: project
---

# McGavin per-component halo-3 — PROVEN (vol-94)

**Status**: `built` — PROVEN 2026-05-16 ~02:38.
**Tool**: `vol62_cluster_mip_bound --radius 3`.

## Result

| comp | core | r | size | delta | obj | time |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 8 | 3 | 42 | **+0** | 93 | 329s |
| 1 | 8 | 3 | 47 | **+0** | 98 | 600s |

Both components delta=+0 at halo r=3.

## McGavin local-optimality progression

| vol | tested | cells | result | time |
|----:|---|---:|---|---:|
| 83 | halo-1 joint | 37 | +0 PROVEN | 895s |
| 92 | halo-2 per-comp | 29+34 | +0 PROVEN | 153s |
| 94 | halo-3 per-comp | 42+47 | +0 PROVEN | 929s |

**McGavin's 469 is rigorously proven rigid at halo r=3 per-component
(89-cell coverage).**

## Strategic implication

The basin's MIP-rigidity extends through halo r=3 without any
break. This is the largest local-optimality region ever proven on
canonical E2.

To find a 470 via local moves would require:
- Halo r=4 per-component (untested)
- OR cross-component swaps not coverable by single-component
  halo-3 (vol-91's halo-2 joint failed; cross-comp coverage is
  an open question)
- OR board-spanning σ-cycle moves (per
  [[vol-65-oracle-sigma-indecomposable]])

## Linked

- [[mcgavin-mip-local-optimal-halo1]]
- [[mcgavin-halo2-percomp-proven]]
- [[why-records-are-mip-rigid]]
