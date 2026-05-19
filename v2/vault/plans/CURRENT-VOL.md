# Current Volume — Vol-156

**Theme**: V155→ALNS hybrid pipeline. Take the 456/480 from-scratch
board produced by V155 PRIOR beam-search, feed to ALNS for 30min
across multiple seeds and operator presets.

V129-T12 lifted 462 → 463 from a McGavin-basin start. From a 456
from-scratch start, ALNS COULD reach:
- 458-459 (strict-canonical records)
- 460+
- 463+ (current matched-edges record)
- Maybe higher

This is the cleanest test of "can a generic from-scratch builder + ALNS
post-process beat per-basin attacks?"

## Concrete experiment (running)

- Base board: `output/vol-155/best.json` (456/480, V155 K=4096+prior).
- 7 ALNS runs × 30min each = 3.5 CPU-hr.
- Seeds: {42, 1, 7, 13} × ops {basic, basic_lkh} = 8 total. One seed
  shared (42 basic) on both bin-prefixes for redundancy.
- Output: `output/vol-155/alns_runs/seed_<N>_<ops>.log`

## What we expect

V129-T12 from a 462 base: +1 (→463).
From a 456 base (-6 floor): more room for improvement.
- Best plausible: ALNS finds new basin near 459-462. Unlikely to break
  463 without basin-anchoring.
- Honest expectation: 459-461 range across seeds.

## Binding items (3 max)

1. Run 8 ALNS jobs in parallel × 30min. (RUNNING)
2. Verify any ≥459 result with `rescore_board`.
3. Document outcome.

## Days budget

1 day (30min compute + analysis).

## Linked

- [[../sessions/vol-156]] (to create)
- [[../sessions/vol-155]] (parent: 456 from-scratch)
- [[../concepts/prior-data-augmented-beam]]
