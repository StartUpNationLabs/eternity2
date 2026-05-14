# Vol-35 — deep lottery from vol-32 458-source partial

**Date**: 2026-05-14.
**Status**: 48 ALNS runs from `output/vol-32/vanilla_fast_5min_best.json`.

## Setup

Vol-32's 458 record came from ALNS on `vanilla_fast_5min_best.json`
(a 210-cell partial, no duplicates verified). Vol-35 ran 48 ALNS
seeds (12 seeds × 4 ops: winning5, mega_mix, full, diverse) at 5min
each on this partial.

## Results

| Score | Count |
|---:|---:|
| 458 | 1 (seed=5 winning5) |
| 457 | 2 (seed=5 full, seed=5 diverse) |
| 456 | 2 |
| 455 | 8 |
| 454 | 6 |
| 453 | 3 |
| 452 | 2 |
| 449 | 2 |
| 447 | 2 |
| 446 | 5 |
| ...below 446 | rest |

## Verified validity (piece uniqueness)

All 3 of {458, 457×2} pass piece-uniqueness check (no duplicates).

The 458 board is **100% byte-identical** to vol-32's original 458
RECORD_BREAK. Same exact attractor. ALNS hit it with different seed.

The 2 × 457 boards:
- 81% pairwise cell overlap (in same broader basin family as vol-32 458)
- 75-80% cell overlap with vol-32 458 (close but not identical)
- 3/5 canonical hints honored (same caveat as vol-32 458: pieces
  180 and 248 displaced; this basin family naturally pushes them
  off-position)

## Implications

- **Vol-32 458 record stands**, now reproduced.
- The vol-32 458 attractor has a hit rate of ~1/48 = 2.1% per ALNS run.
- The 458 basin family also contains 457 LOs at 4.2% hit rate.
- The basin family caps at 458 (no 459 in 48 runs).

## Lottery economics

To find another 458 board (different from vol-32's): 48 runs gave
just the same vol-32 458. We'd need 100s of runs to potentially
hit a DIFFERENT 458 attractor (if one exists in this basin).

To break 459: needs a structurally different basin family. The vol-35
T1 sweep found 46 productive thread_ids but the sweep snapshots
were corrupted by the pin_hints bug, so the family-255 etc. probes
were invalid. Need to re-do with fixed binary.

## Saved boards

- `output/vol-35/records/RECORD_TIE_458_vol35_deep458_winning5_seed5.json` (byte-identical to vol-32 458)
- `output/vol-35/records/RECORD_TIE_457_vol35_deep458_full_seed5_3hints.json` (NEW 457 in 458-basin family)
- `output/vol-35/records/RECORD_TIE_457_vol35_deep458_diverse_seed5_3hints.json` (NEW 457 in 458-basin family)

The 2 × 457 boards are within the 458 basin family but at score 457.
They're STRUCTURALLY DIFFERENT from the 4 verified blackwood_mrv 457
basins (75-80% overlap with vol-32 458 vs 2-3% overlap with vol-32
blackwood_mrv 457s).

So: **arguably 2 new 457 basin variants discovered**, but they're
"satellites" of the vol-32 458 basin, not independent.
