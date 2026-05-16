---
name: mcgavin-alns-basic-locked
description: "Vol-121 T6 — McGavin 469 is ALNS-basic-locally-optimal under 30-min × 4 seeds. All 4 ALNS runs (basic ops, seeds 1, 7, 42, 100, 1800s each) returned 469/480, no improvement. Consistent with vol-44/95/100 MIP rigidity proofs."
metadata:
  type: project
---

# McGavin ALNS-basic-locked (vol-121 T6)

`alns_only --cp-board mcgavin_469.json --ops basic --alns-budget-ms 1800000`
× 4 seeds (1, 7, 42, 100).

| Seed | Final score | Δ |
|------|-----:|----:|
| 1    | 469 |   0 |
| 7    | 469 |   0 |
| 42   | 469 |   0 |
| 100  | 469 |   0 |

All 4 ALNS runs returned exactly 469/480. McGavin is empirically
ALNS-basic-locally-optimal under 30-min × 4 seeds.

## What this adds to McGavin rigidity

Adds to vol-83/95/100 MIP rigidity proofs (full-piece-freedom halo
≤ 4 per-component) and vol-121 T3 (joint halo-2). ALNS basic 30min
is a different operator class (destroy-and-repair vs joint MIP);
finding the same Δ=0 confirms McGavin's local optimality across
multiple operator types.

## What it does NOT prove

- 4 seeds is a small sample.
- `winning5` and `minimal` ops (T9, also running) may find a basin
  variant.
- Longer ALNS budget (hours) may eventually escape via rare moves.

## Linked

- [[mcgavin-top3-mip-locked]]
- [[mcgavin-joint-halo2-mip-result]]
- [[honest-status-vol121]]
- [[../sessions/vol-121]]
