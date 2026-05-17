---
name: j1-rust-beam100k-first-complete-board
description: "J1 Rust chain with beam=100000 produces FIRST COMPLETE 256/256 board: 444 matched. 8 perfect bands (0-7), decay through band 14, but completes. Verified LEGAL_COMPLETE-shape (no border violations)."
metadata:
  type: project
---

# J1 — First complete board (beam=100000)

## Setup

Rust J1 chain with $\text{beam} = 100\,000$, 60s/band budget.

## Result

**256/256 placed cells**, **444/480 matched edges**, **0/5 hints obeyed**.
verify_board: status `ILLEGAL` only due to hint mismatches (0/5).
No border violations.

This is the FIRST completed canonical 16×16 board from the pure J1
algorithm without ALNS post-processing.

## Per-band scores

| Band | Rows | Score | Notes |
|---|---|---|---|
| 0 | 0,1 | 46/46 | perfect |
| 1 | 1,2 | 46/46 | perfect |
| 2 | 2,3 | 46/46 | perfect |
| 3 | 3,4 | 46/46 | perfect |
| 4 | 4,5 | 46/46 | perfect |
| 5 | 5,6 | 46/46 | perfect |
| 6 | 6,7 | 46/46 | perfect |
| 7 | 7,8 | 46/46 | **perfect** (+1 vs beam=50k) |
| 8 | 8,9 | 45/46 | -1 |
| 9 | 9,10 | 45/46 | -1 |
| 10 | 10,11 | 43/46 | -3 |
| 11 | 11,12 | 42/46 | -4 |
| 12 | 12,13 | 40/46 | -6 |
| 13 | 13,14 | 36/46 | -10 |
| 14 | 14,15 | 35/46 | -11 (final) |

Sum: $46 \times 8 + 45 \times 2 + 43 + 42 + 40 + 36 + 35 = 654$.

Final-board matched: 444 (sum minus double-counted horizontals).

## Why beam=100k succeeded where beam=50k failed

With beam=50000, band 14 had NO STATES → infeasible.
With beam=100000, band 14 found 35/46 feasible.

The extra beam capacity at band 14 = more piece-supply / color-profile
combinations to search.

## Beam=500000 result

Too large: band 0 timed out at column 8 in 138s. Beam-prune by score
becomes O(beam × log(beam)) = $5 \times 10^5 \cdot 19 \approx 10^7$
per column × 16 columns = $1.6 \times 10^8$ ops just for sort.

**Optimal beam: $\sim 10^5$** for canonical E2.

## Comparison

| Method | Result | Time |
|---|---|---|
| J1 Python beam=5000 chain | 240/256 cells, 423/449 matched | ~85s |
| J1 Rust beam=50k chain | 240/256, 424/449 (failed band 14) | 17s |
| **J1 Rust beam=100k chain** | **256/256, 444/480** | **35s** |
| Standing 459 (vol-60) | 256/256, 459/480 | many hours |
| Standing 457 strict-canonical | 256/256, 457/480 (5/5 hints) | many hours |
| Best vol-122 (bf_bw+ALNS) | 256/256, 452/480 (5/5 hints) | 35 min |

The J1 444 board is **8 points below our best 452**, but takes only **35
seconds**. It also has **0/5 hints** — the canonical hints are NOT enforced.

## Why the J1 board doesn't beat 452

The greedy chain (top-down with beam=100k) commits to decisions early
that constrain later bands. Bands 12-14 lose 11+11+10 = 32 edges below
perfect. Multi-band beam at the chain level (chain_K > 1) should fix
this — already tried in Python with K=20 but Rust port to do.

## Next steps

1. **Rust multi-band beam**: tracks K-chain alternatives at each band.
   Should preserve more bands 0-7 perfect while improving bands 8-14.
2. **J1 444 + ALNS**: feed this board to ALNS basic 30min. The board
   has good band-0-7 structure that ALNS shouldn't break.
3. **Bottom-up Rust chain**: anchor on bottom border.

## Status

`milestone-complete-board-from-J1` — first complete canonical board
from the J1 algorithm. 444/480, 35s.

## Linked

- [[j1-column-dp-design]]
- [[j1-poc-perfect-band-results]]
- [[j1-chain-band-decomposition-math]]
- [[j1-band-14-failure-analysis]]
