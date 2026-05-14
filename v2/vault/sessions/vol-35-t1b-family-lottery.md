# Vol-35 T1b — family lottery results

**Date**: 2026-05-14.
**Setup**: 46 productive thread_ids from vol-35 T1a sweep (offsets 0-450,
8 threads each = 80 thread_ids tested, 46 productive).

Each family represented by its deepest snapshot (all depth=200, the
snapshot threshold). Ran 1 ALNS seed × 60s × winning5 ops per family.

## Top 10 results (rescore-verified)

| Family | Score | Bound | Gap |
|---:|---:|---:|---:|
| 4 | 455 | 459 | +4 |
| 255 | 455 | **463** | +8 |
| 257 | 455 | 461 | +6 |
| 452 | 455 | 461 | +6 |
| 150 | 454 | 460 | +6 |
| 256 | 454 | 463 | +9 |
| 400 | 454 | 461 | +7 |
| 402 | 454 | 462 | +8 |
| 55 | 453 | ? | ? |
| 205 | 453 | ? | ? |

## Observations

- **Max score = 455** with 1-seed × 60s, distributed across multiple
  families. No 458 break, but 455 is in the recoverable range
  (vol-32 lottery reached 454-457 with longer ALNS).
- **Family 255 has bound 463** — highest among tested. If a deep
  lottery can find a board near its bound, this family could
  potentially reach 458-463.
- Bound gaps range from +4 to +9. The families with highest bound
  (255, 256) tied with families of lower bound — implying the
  RECOVERABLE ceiling depends on more than just bound.

## Next step (deep family-255 lottery)

Running 12 seeds × 4 ops × 3min = 48 runs, ~18 min on 8 cores.
If family 255 can reach its bound 463, that's +5 from current
record 458.

## Implication

Vol-35 T1 hypothesis CONFIRMED: thread-id-offset sweep discovers
new basin families beyond the original {0..7} set. **46 distinct
productive thread_ids** found in {0..457}. Each represents a
structurally distinct basin family.

However, **basin diversity alone doesn't yield records**. Even with
46 families × winning5 ALNS, max = 455 (below 458). The bound is
the structural ceiling, but ALNS recovery falls 4-9 below it.

To break 458 we need either:
1. A family with bound > 463 (more sweep effort)
2. Stronger ALNS recovery (different operators, longer time)
3. Both

Deep family-255 lottery is testing #2. If it pushes past 455, we have
a new tool. If it caps at ~455, the structural barrier holds.
