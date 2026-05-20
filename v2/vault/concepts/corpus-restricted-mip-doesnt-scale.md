---
name: corpus-restricted-mip-doesnt-scale
description: "Vol-119 T2 — Vol-112's basin-mix MIP formulation (binary x[c,b] per cell-basin) doesn't scale beyond N=5 basins. CBC at N=9 timed out at 30min with NO feasible integer solution (LP-UB 1094, far from any integer). The REGIONAL formulation (T5, vault/concepts/corpus-restricted-region-mip-locked) is the correct approach: fewer y-vars, much faster."
metadata:
  type: project
status: refuted
---

# Corpus-restricted basin-mix MIP doesn't scale (vol-119 T2)

## Test setup

Goal: find a board with score > 459 by mixing basins from a 9-board
corpus. Each cell c gets a binary x[c, b] for each basin b. y vars
encode adjacent-edge match between any (b1, b2) pair. Objective:
max sum(y).

| Corpus | Vars | Constraints | CBC result |
|-------:|-----:|------------:|-----------|
| N=4 (vol-112) | 1024 + ~4500y | ~9700 | INT=459, 17s |
| N=5 (vol-119) | 1024 + ~9000y | ~17000 | INT=459, LP-UB=491, 86s |
| **N=9 (vol-119)** | 2304 + ~50Ky | ~100K | **NO FEASIBLE solution at 30min** |

The N=9 MIP's LP UB was 1094 (from sum of fractional y indicators);
no integer solution found in 30 min. The basin-pick-per-cell
formulation has too many edge-match variables (quadratic in N).

## The successful alternative

[[corpus-restricted-region-mip-locked]] uses a different formulation:
- One binary x[(pos, pid, rot)] per (cell, piece, rotation) option.
- One y per matched-edge candidate (smaller than vol-112's per-edge-per-basin-pair).
- Pinned cells outside free region as constants.

This formulation scales to:
- 30-board corpus at halo-12 (252 cells free): ~800 x-vars, solves in <1min, PROVES Δ=0.
- 5-board corpus at halo-15 (256 cells free): ~800 x-vars, solves in <30s, Δ=0.

The regional MIP is 10-50× smaller AND has tight LP=INT, while
vol-112's basin-pick MIP has loose LP and explodes in y-var count.

## Why vol-112's formulation explodes

Each cell-pair (c1, c2) adjacent has N² y-variables (one per basin-pair
b1, b2). With N=9 basins and 480 adjacencies, that's ~38K y-vars
just for edge matches. Plus piece-uniqueness constraints couple all
N²×256 = 656K (cell, basin) pairs.

CBC's LP relaxation can't tighten because the y-pair variables don't
correspond to any geometric interpretation — the LP allows fractional
contributions to edge matches that the integer rounding can't preserve.

## Implication

For future corpus-MIP work: USE THE REGIONAL FORMULATION
(`scripts/vol119_region_basin_mix_mip.py`). The basin-pick formulation
is a vol-112 historic, not scalable.

## Linked

- [[basin-mix-mip-refuted]] (vol-112 original)
- [[corpus-restricted-region-mip-locked]] (vol-119 T5 invention)
- [[vol-119]]
