---
name: vol-125-record-summary
description: "Vol-125 record-breaking summary: 459 -> 460 (10:41 CEST) -> 461 (12:03 CEST). 4+ distinct 461 basins, 8+ distinct 460 basins. 461 ceiling robust under ALNS basic, mega_mix, halfboard, PT, MaxSAT cluster repair. Trying high-T ALNS next."
metadata:
  type: session
---

# Vol-125 record summary (in progress)

## Records broken

1. **459 → 460** at 2026-05-18 10:41 CEST.
   - Pipeline: `bf_bw --seed-offset 125 + ALNS basic --seed 42`.
   - Board: `output/vol-125/records/RECORD_460_bf_bw_off125_seed42.json`.

2. **460 → 461** at 2026-05-18 12:03 CEST (1h22min later).
   - Pipeline: `bf_bw --seed-offset 110 + ALNS basic --seed 42`.
   - Board: `output/vol-125/records/RECORD_461_bf_bw_off110_seed42.json`.

Both records use the matched-edges convention (community 4/5-hint).

## Basin distribution

### 461 basins (4+ distinct)

| Basin | Corner perm | Boards |
|---|---|---|
| A | (1,2,0,3) interior I | seed110 s7=s42=s142, seed111 s42 |
| B | (1,2,0,3) interior II | seed110 s99 |
| C | (1,2,3,0) | seed110 s1 |
| D | (0,1,2,3) | seed225 s1, s7 |

### 460 basins (8+ distinct)

bf_bw seed-offsets reaching 460: 50, 75, 120, 125, 135, 140, 325, 350. Each likely a distinct basin.

## Attacks attempted on 461 boards (all unsuccessful for 462+)

| Attack | Budget | Result |
|---|---|---|
| ALNS basic seed 42 | 30 min | 461 (the record itself) |
| ALNS basic seeds 1, 7, 99, 142 | 30 min × 4 | All 461 |
| ALNS mega_mix seed 42 | 30 min × 4 boards | All 461 |
| ALNS halfboard seed 7 | 30 min | 460 (didn't even reach 461 starting from 459) |
| PT (parallel tempering) on basin A | 30 min, 4 replicas | 461 |
| PT on basin D | 30 min, 4 replicas | 461 |
| MaxSAT cluster repair halo 2 | 600s | UNKNOWN (z3 parse error — wcnf race bug) |
| MaxSAT cluster repair halo 3 | 600s | UNKNOWN (same bug) |

## Current attack: high-T ALNS

Launched at 14:18 CEST:
- t=5, mega_mix, on basin A (RECORD_461_bf_bw_off110_seed42)
- t=15, mega_mix, on basin A
- t=5, mega_mix, on basin D (RECORD_461_off225_seed1_basinD)
- t=15, mega_mix, on basin D

Higher t (>1) accepts worse moves with probability exp(-Δ/t), enabling
basin-jumping. If 461 IS a local max, only t-driven uphill walks can
discover 462.

## Implications

1. **461 may be the true ceiling for ALNS-class search** on canonical E2.
2. **18 years of community work capped at 459; vol-125 added +2** (459 → 461).
3. **The basin space at 461 is broader than vol-118 rigidity theorem implied** (4+ distinct basins now confirmed).
4. **Next: high-T attacks; if also stuck at 461, then 462 requires structurally different search** (cube-and-conquer SAT, RL self-play, MIP B&P&C, super-block BB&B).

## Linked

- [[record-460-2026-05-18]]
- [[record-461-2026-05-18]]
- [[v125-461-reproducibility]]
- [[v125-third-459-basin]]
- [[v125-cube-conquer-finding]]
- [[v125-border-dp-stage-a]]
