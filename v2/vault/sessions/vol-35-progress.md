# Vol-35 — progress summary (mid-volume, 13:16)

## Status

### Completed
- ✅ T1a: thread-id-offset sweep (offsets 0-450, 8 threads each = 80 thread_ids)
  - 46 productive thread_ids found
  - All distinct basin families (one per thread_id)
- ✅ T1b: family lottery (1 seed × 60s × winning5 per family)
  - 46 verified runs (rescore_board)
  - Max score: 455
  - Best bound: 463 (family 255)

### In progress
- 🔄 Deep family-255 lottery: 12 seeds × 4 ops × 3min on family 255's partial
  - Goal: test if longer ALNS + diverse ops can push past 455 toward bound 463
  - ETA: ~15 more min

### Vol-34 mid-vol findings preserved
- vanilla_fast 16×16 hardcoded: 124.7M pp/s single-thread (confirmed clean)
- vanilla_fast_n runtime-N: 29.7M pp/s at 16×16 (4× slowdown, OK for non-canonical)
- 5 distinct 457 cold-start basins now known
- 458 record stands

## Hypotheses tested

### Color-ratio hypothesis (user-proposed)
- 6×6/5c (7.2 pp/c) rugged FDC=-0.031
- 8×8/5c (12.8 pp/c, canonical ratio) FDC=0.000
- 10×10/8c (12.5 pp/c, canonical ratio) FDC=-0.086
- 12×12/8c (18.0 pp/c) FDC=-0.104
- Conclusion: color-ratio NOT the determining factor. Size matters
  more than ratio at small puzzles.

### Basin-family-count scaling (vol-35 T1a hypothesis)
- 8-thread {0..7}: 5 productive
- 16-thread {0..15}: 5 productive (saturation under oversubscription)
- 8-thread × 10 offsets {0,50,..,450}: **46 productive** total
- Conclusion: basin-family count scales linearly with sweep offsets.
  No saturation observed.

### Family-bound vs recoverable-ceiling
- 8 top families have bound 459-463
- Recoverable max so far: 455 (with 60s ALNS)
- Gap: 4-9 from bound to recoverable
- Open: does longer ALNS close the gap?

## Open questions

1. **Can deep ALNS on family 255 reach 458+?** Testing now.
2. **Does FDC structure require multiple seeds per partial?**
   The vol-34 T3 trimodal Hamming was within-basin (4 seeds/partial).
   Vol-35 T1b 1-LO-per-basin gave FDC=+0.084 (positive — random).
3. **Is there a family beyond {0..457} with bound > 463?**
   Would need more sweep effort.

## If deep family-255 hits 458+

Record break. Document, save board, run verification.

## If deep family-255 caps at 455

Bound-recoverability gap is a real limit. Vol-36 should pivot to:
- Different operators (vol-22 basin-escape recipe, or new operator development)
- ML-guided ALNS (revisit vol-26-29 with new starting points)
- Stronger CP-partial generation (different scan orders, propagators)
