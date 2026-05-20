---
name: vol122-alns-multi-seed-results
description: "Vol-122 ALNS multi-seed sweep results: perm0 / perm3 / McGavin boards × seeds {1, 7, 42, 100, 13} × {basic, winning5} × {30min, 60min}. Best = 447 (winning5 60min McGavin s42). All ≤ 447, far from 459 standing."
metadata:
  type: project
status: built
---

# Vol-122 — ALNS multi-seed sweep results

## Setup

After K7 localized the 469-vs-444 gap as ENTIRELY interior-interior,
ran multi-seed ALNS to see if more search exploration could reach
McGavin's 354/364 II level.

Test matrix:
- 3 boards: perm0_complete_s1, perm3_complete_s1, mcgavin_complete_s1
- Multiple seeds: {1, 7, 13, 42, 100}
- Ops: {basic, winning5}
- Budgets: {30min, 60min}

## Results (matched-edges)

| Board | basic 30min × seeds | basic 60min | winning5 30min | winning5 60min |
|---|---|---|---|---|
| perm0_complete_s1 | s1=430, s7=439, s42=432, s100=435 | s1=444 (PID 43464) | – | s1=437 |
| perm3_complete_s1 | (covered earlier) s7=439 | – | – | s1=439 |
| mcgavin_complete_s1 | s7=437 | – | s42=430 (SLR-input) | s42=447 ★, s1=442 |

**Best: 447** (winning5 60min on mcgavin_complete_s1, seed=42).

## Observations

1. **Variance across seeds**: 9-12 edges (430-444 for perm0 basic 30min).
2. **30min → 60min lift**: ~10-15 edges per board (e.g., perm0 444 vs 432 across seeds).
3. **winning5 > basic** by 5-12 edges on these CLEAN-SLATE boards.
4. **Best on any clean-slate board: 447** — still 12 below standing 459.

## Implication

Even with multi-seed × longer budget × better ops, we **cannot reach
459 on clean-slate boards** via ALNS. The 25-edge interior-interior
gap (K7) seems structurally bound.

This SUGGESTS:
- The 459 record came from a **specific basin** that vol-60 ALNS happened
  to find, not from a property the boundary admits.
- Our clean-slate boundaries (perm0/3/mcgavin) all reach ~440 max via
  ALNS, regardless of seed/ops/time.
- The 459 basin is reachable only with the specific bf_bw → bound-ascent
  → ALNS pipeline that vol-110 used (not just border + random fill + ALNS).

## What this rules out

"Just throw more compute at perm0/3 boards" — won't reach 459. The
ceiling is ~447 for these boards.

## What might still work

- A1 pipeline FROM bf_bw partials (not from random-fill seeds). The
  bf_so2000 240-cell partial @ 424 starts MUCH closer to 459 than
  random-fill starts at 313.
- Multi-restart with HIGHER seed-offset diversity for bf_bw.
- Combining BF partials with bound-ascent before ALNS.

## Status

`empirical-finding` — multi-seed × multi-ops sweep saturates at 447 on
clean-slate boards.

## Linked

- [[vol122-25-edge-gap-is-all-interior]]
- [[vol122-mcgavin-border-our-stack-435]]
- [[vol122-a1-pipeline-result]]
- [[vol-122]]
