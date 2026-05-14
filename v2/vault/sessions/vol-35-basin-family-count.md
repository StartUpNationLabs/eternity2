# Vol-35 — basin family count + lottery results

**Date**: 2026-05-14 (vol-35 mid-vol).
**Status**: T1a (sweep) and T1b (lottery) DONE.

## T1a — thread-id sweep

Ran `vanilla_fast --threads 8` at offsets {0, 50, 100, 150, 200, 250,
300, 350, 400, 450} × 5min × `--snapshot-on-visit` × `--pin-hints`.

**Result**: 46 distinct productive thread_ids found across the sweep:
- Offset 0: tids {0, 1, 4, 5, 7} — 5 productive
- Offset 50: tids {50, 52, 53, 54, 55, 57} — 6 productive
- Offsets 100-450: 1 productive each (sparse hit rate at high offsets)

The 8 productive-thread-ids per offset is non-monotonic: 5 (offset 0)
→ 6 (50) → 1 (100+). Some bucket-shuffle seed ranges are much more
productive than others, but the average drops with offset.

Total: **46 distinct basin families** (vs 5 from {0..7} alone — 9.2×
expansion).

## T1b — ALNS lottery per family

For each of the 46 families, picked the DEEPEST snapshot as
representative and ran 1 ALNS seed × 5min × winning5 ops + SA repair.

**Top scores (rescore-verified)**:

| Score | Count |
|---:|---:|
| 455 | 4 |
| 454 | 4 |
| 453 | 3 |
| 452 | 4 |
| 451+ below | rest |

Max = 455. No 457 found despite 9× more families than vol-34 T3.

## Interpretation

The depth-200 vanilla_fast snapshots all cap at 455 via ALNS-5min.
Vol-34 T3's 457s came from deeper partials (207-209) within the
ORIGINAL families {0, 1, 4, 5, 7}. **Partial depth matters more
than family diversity at this scale.**

Hypothesis to test: deepen the new families' partials. Each family
has multiple snapshots at depth 200; with a longer probe per family,
some might reach 207-209. Then re-run lottery from those deeper partials.

## Vol-35 next steps

1. **Re-probe** the top-bound families (4, 255, 257, 452) with longer
   per-thread budgets to find depth-207+ partials. ~30 min per family
   × 4 = 2 hours.

2. **Cross-family combination**: bound-ascent recipe (vol-22) on a
   depth-200 lottery winner (rescore 455). Maybe finds higher-bound
   configs accessible from this family. Earlier b470 attempts capped
   at 400 — but those were from vol-21's SA-walked boards, not
   ALNS-recovered boards.

3. **More seeds per family**: 46 × 4 seeds × 5min = 30 min compute.
   The single-seed-per-family lottery has high variance.

## Caveat

The 8 productive thread_ids per offset have very different histories:
some had 1 deep snapshot, others had many. The "deepest snapshot per
thread" representative may not be the BEST representative.

## Linked

- [[vol-34-basin-clustering]] — original 5-family observation
- [[vol-34-record-class-landscape]] — trimodal Hamming at canonical
