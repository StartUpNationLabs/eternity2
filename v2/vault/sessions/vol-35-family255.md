# Vol-35 — family 255 discovery

**Date**: 2026-05-14.
**Status**: confirmed 7th distinct 457 basin; 458 still unbroken.

## The discovery path

Vol-35 T1a found 46 productive thread_ids via offset-sweep (offsets
{0..450}). T1b ran 1 ALNS seed × 5min per family — max=455, no 457.

Suspected family 255 (offset 250, in-offset thread index 5) deserved
deeper probing — its depth-200 partial gave 455 in the first lottery.

T1c: 48 ALNS seeds × 5min on family 255's depth-200 partial. Results:

| Score | Count |
|---:|---:|
| 457 | 3 |
| 456 | 3 |
| 455 | 1 |
| 454 | 1 |
| 453 | 2 |
| ... | ... |

**457 hit rate**: 3/48 = 6.25% per ALNS seed.

## The 3 × 457 boards from family 255

All structurally similar (87% pairwise cell overlap), all in the
same 457-basin of family 255. Different ALNS seeds and ops
(winning5, full) converged to similar but not identical 457s.

vs other known 457 basins: 1-4% cell overlap. **Genuinely new
basin family**.

Bound: 463 (gap +6 from score=457).
Bound-ascent (200 SA iters): stays at 457/463 — basin is locally
saturated, can't reach higher-bound configs via SA.

## 7 distinct 457 basin families known across project

| Basin | Source | Bound | Score-recoverable |
|---|---|---:|---:|
| #1 | vol-18 / vol-32-seed7 | 462 | 457 |
| #2 | vol-32-seed10 | 457 | 457 (saturated) |
| #3 | vol-32-seed4-30m | 465 | 457 |
| #4 | vol-34 #1 | 464 | 457 |
| #5 | vol-34 #2 | 464 | 457 |
| #6 | vol-32 458 | 463 | 458 (record) |
| #7 | vol-35 family 255 | 463 | 457 |

(vol-32 458 is in basin #6, which has score-recoverable = 458 —
the only known 458-recoverable basin. All others cap at 457.)

## Implication for 458 break

Vol-35's family 255 expansion hits 457 reliably but doesn't break it.
Generalizing across all 7 known basins: **the only known
458-recoverable basin is vol-32's via blackwood_raw+MRV → ALNS-5min**.

For vol-35+ to break 458:
- Find an 8th distinct basin with bound ≥ 460 AND
  score-recoverable ≥ 458. The 7 known basins suggest this is rare.
- Run deeper probes (depth-207+ partials) per family. The original 5
  families (vol-34 T3) gave 457 from depth-207-209 partials. Family
  255's depth-200 partial gives 457 too — does its depth-207+ partial
  give 458?

Currently running: vol-35 30-min probe specifically on family 255 with
--snapshot-on-visit at min-depth=200, looking for depth-207+ partials.

## Linked

- [[vol-34-record-class-landscape]] — trimodal Hamming finding
- [[vol-35-basin-family-count]] — the 46-family sweep
