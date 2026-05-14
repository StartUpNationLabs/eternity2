# vol-34 — T1 signal: 457 cold-start (after fixing alns_only bug)

**Date**: 2026-05-14 (mid-vol)
**Status**: 457 confirmed rescored after bug fix

## Bug discovered + fixed

The first attempt at this 457 reported `matched=457` in the ALNS log
but the saved board scored only 453 by `rescore_board`. Investigation
found a bug in `piece_swap_hillclimb` (vol-34 commit `4474987`):
local-delta estimator over-counted on certain non-adjacent swap
topologies that share neighbours; over 200 iterations the cumulative
`total_gain` ballooned to `+400` while the board actually regressed.

Fix: anchor on `score_board()` between swaps, roll back + break if
real score regresses, report gain as `final - start`. Re-running the
same partial × seed now scores **457 confirmed by rescore_board**
(saved at `output/vol-34/t3_signal/REAL_RECORD_TIE_457_vol34_t1signal_seed1.json`).

The vol-32 records (458 RECORD_BREAK, three 457 RECORD_TIE) all
verified intact by `rescore_board` post-fix; the bug only fired on
some partials, not all.

## Original (now-refuted) headline

A new 457/480 canonical-clue-respecting board, fresh basin family,
reached in 60s ALNS from a 207-depth `vanilla_fast` snapshot. 5/5
canonical hints honored (verified). Ties vol-18's all-time cold-start
record.

## How

```
vanilla_fast --threads 8 --pin-hints --budget-ms 3600000 \
  --snapshot-dir output/vol-34/t1_probe \
  --snapshot-interval-ms 60000 --snapshot-min-depth 200
```

24 min into the 1-h probe, snapshot `t00_s002_d207.json` (depth 207,
207 placed cells) was processed through:

```
alns_only --cp-board <snapshot> --alns-budget-ms 60000 --seed 1 \
  --ops winning5 --repair-kind sa
→ matched=457/480
```

Verified hint pinning correct: pos 34=207/1, 45=254/1, 135=138/0,
210=180/1, 221=248/2 — all 5 canonical hints in place.

## Why this is meaningful

- **Cheap**: 60s ALNS from a depth-207 partial. Vol-32's 458 needed
  vanilla_fast + 5min ALNS. Vol-32's 457 record-tie needed
  blackwood_raw + 5min CP + 5min ALNS.
- **New basin**: only 4.3% cells match vol-21's 457 (also a 457
  basin found by bound-ascent); 2.7% match vol-32's 458. The new
  457 lives in a structurally distinct basin family.
- **Verified**: edge_bound_ascent on this 457 gives basin bound = 461
  (+4 over score). Same shape as vol-32's basins (gap +2 to +5).

## Lottery context

Signal test: 10 partials × 2 seeds × 60s ALNS = 20 runs.

| Score | Count |
|---:|---:|
| 457 | 1 |
| 456 | 2 |
| 454 | 4 |
| 453 | 3 |
| 452 | 1 |
| 451 | 1 |
| 449 | 1 |
| 448 | 2 |
| 444 | 1 |
| 443 | 1 |
| 441 | 1 |
| 440 | 1 |
| 439 | 1 |
| 435 | 1 |

Mean=448.5, median=451, max=457.

## ops A/B (single-partial, 60s)

`t00_s002_d207.json` → 4 ops × 2 seeds × 60s ALNS:

| ops | seed=1 | seed=2 |
|---|---:|---:|
| winning5 | **457** | 456 |
| full | 456 | 451 |
| mega_mix | 456 | 411 |
| mega | 431 | 426 |

**winning5 dominates at 60s.** Consistent with vol-32 wake-summary's
finding that "ALL 8 presets give 456" on basin-locked 456 boards.

## Implication for vol-34 T3

The full 1h probe is expected to produce ~75 partials at depth 200+.
T3's planned 100 × 4 × 5min lottery should comfortably produce
multiple 456-457s. The basin-ceiling-at-461 result suggests 458+
remains structurally hard from this family of partials — would need
either a fundamentally different starting partial (bound > 462) or
a stronger ALNS operator not in `winning5`.

## Boards saved

- `output/vol-34/t3_signal/RECORD_TIE_457_vol34_t1signal_seed1.json` (the 457)
- `output/vol-34/t3_signal/board_456_a.json`, `board_456_b.json` (the two 456s)

## Linked

- [[basin-457-pt]] — the vol-18 457 basin (byte-identical x11).
- [[basin-440-469]] — vol-22's 469-ceiling basins (different family).
- [[blackwood-algorithm]] — the alternative cold-start route.
