---
name: vol122-random-path-sweep-result
description: "Vol-122 T1 random-path massive sweep result. 11 seeds completed: placed counts 87-136 cells, far from full board. Random scan order is much weaker than border-first MRV for basin discovery."
metadata:
  type: project
status: built
---

# Vol-122 T1 — random-path massive sweep (result)

## Setup

`vanilla_path --path-mode random --path-seed {1,2,3,5,7,11,13,17,19,23,29}` on canonical 16×16/22c/5h, depth budget targeting maximal scan-order randomization. Each seed produced one partial.

## Measured

Placed count distribution across 11 seeds:

| Seed | Placed | Matched |
|------|--------|---------|
| 11 | 136 | 134 |
| 2 | 120 | 111 |
| 17 | 119 | 115 |
| 7 | 115 | 105 |
| 13 | 114 | 98 |
| 23 | 106 | 99 |
| 19 | 102 | 95 |
| 29 | 94 | 85 |
| 5 | 93 | 86 |
| 3 | 87 | 68 |
| 1 | — | — |

**Best: 136 placed / 134 matched edges (pseed=11).**

## Interpretation

Random scan-order CSP plateaus at ≤ 136 placed cells under the budget given. This is roughly **half** the board, far short of what ALNS needs as starting state (≥ 200 placed is rule of thumb).

In contrast:
- **Border-first MRV** baseline reaches 240+ placed in seconds.
- **vol-122 INVENTION 3 border-DP** seeds 60 cells, then CSP-fill reaches 176 placed (still short).

So random-path is REFUTED as a basin-discovery seed source under canonical engine budgets. Pivot is **invention 3 border-DP → CSP-fill → ALNS** (vol-122 A1).

## Why random-path is bad here

The CSP search benefits from **constrained-first** scan order: corners (4 rotation choices) before borders (60 piece-rotation choices) before interior (764 piece-rotation choices). Random scrambling forces the engine to encounter high-domain cells early, before any propagation can shrink them. Resulting depth-walls are much earlier.

This isn't a refutation of "random helps escape basin lock-in", just of "random as primary scan order". A finer-grained variant (random within layer, layers in MRV order) might still have value but is a different invention.

## Status

`refuted-as-seed-source` (random scan-order at canonical depth budget cannot produce useful basin starting points).

## Linked

- [[vol-122]]
- [[INVENTIONS_BACKLOG]]
- [[inv3-border-dp-seed]] — the pivot
