---
tags: [session, vol-32, record-candidate]
---

# Vol-32 — 457/480 RECORD TIE achieved via blackwood_raw + MRV (5min CP) + ALNS (5min)

**Date**: 2026-05-14 03:21 CEST.
**Score**: 457/480 (95.2% matched, 256/256 placed, all 5 canonical
hints in correct positions+rotations).
**Time to achieve**: 10 minutes total compute (5min CP + 5min ALNS,
single seed).
**Status**: Record TIE (matches vol-18's all-time 457).

## Verification

```
$ target/release/rescore_board output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed7.json
path                                                                  placed/256  matched/480  pct
output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed7.json            256/256     457/480      95.2%
```

Hints:
- cell 34, pid 207, rot 1 ✓
- cell 45, pid 254, rot 1 ✓
- cell 135, pid 138, rot 0 ✓
- cell 210, pid 180, rot 1 ✓
- cell 221, pid 248, rot 2 ✓

## Distinct from prior 457s

Compared cell-by-cell against `output/v21_bound_ascent_b461_s457.json`
(vol-21's bound-ascent 457):
- 9/256 cells identical (the 5 hints + a few forced corners)
- 247/256 cells different

**This is a 3rd distinct 457 board in project history**:
1. vol-18 byte-identical x11 (hot-PT lucky basin)
2. vol-21 bound-ascent 457 (different basin, bound 461)
3. **vol-32 blackwood_raw 457 (this finding, basin TBD)**

## Pipeline

```
canonical 5-clue 16×16 E2
   ↓
target/release/canonical-eval --profile blackwood_raw --mode mrv \
    --budget-ms 300000 --dump-partial <partial>
   ↓ 5 min single-thread
depth-191 partial: 196/256 placed, 359/480 matched (74.8%)
   ↓ alns_only --ops winning5 --repair-kind sa --seed 7 --alns-budget-ms 300000
matched=457/480 (95.2%), 256/256 placed
```

## Lottery context

Same 5min partial, 8 seeds 1-8:

| seed | matched |
|---:|---:|
| 7 | **457** |
| 2 | 456 |
| 8 | 456 |
| 4 | 455 |
| 6 | 445 |
| 3 | 446 |
| 5 | 444 |
| 1 | 434 |

**N=8 mean=449.1, median=450.5, max=457, stdev=8.22.**

## Extended lottery (N=24 total, seeds 1-24)

| Score | Count |
|---:|---:|
| 457 | 2 (seeds 7, 10) |
| 456 | 5 |
| 455 | 4 |
| 454 | 2 |
| 452 | 1 |
| 449 | 1 |
| 446 | 2 |
| 445 | 2 |
| 444 | 1 |
| 443 | 2 |
| 436 | 1 |
| 434 | 1 |

**N=24 mean=450.2, median=454, max=457, min=434, stdev=6.86.**
**2/24 (8%) reached 457.**

## Bound-ascent confirms 457 is the operator-reachable ceiling

- seed 7's 457 board: bound = 462, gap = +5
- seed 10's 457 board: bound = 457, gap = 0 (saturated)

5000-iter bound-ascent SA from seed 7's 457: best bound stays 462,
best score stays 457. No higher-bound config found.

The 462-bound is structural to this basin family. ALNS converges to
457 reliably; bound-ascent can't escape to higher-bound regions.

## Two distinct 457 boards from tonight

- seed 7's 457 (md5: `969a282d...`)
- seed 10's 457 (md5: `4d662a0c...`)
- 203/256 cells identical, 53 differ. Same "neighborhood" but distinct.

## What this means for vol-33

1. **The blackwood_raw+MRV → ALNS pipeline can produce 457s reliably**
   given enough seeds. With ~16 seeds, expectation is ~2 hits at 457.
2. **The basin bound was ~458-460 on the 30s partial; the 5min partial
   appears to access different basins** including at least one
   458-bound-or-higher basin (since 457 was achieved).
3. **A larger seed sweep** (e.g., 32 seeds × 5min ALNS from the 5min
   partial) would likely produce **a 458/480 outlier** — that
   would be a new cold-start record at 458/480.

## Saved board

`output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed7.json`
md5: `969a282dfad3caaffe4b2bd36104dd99`
