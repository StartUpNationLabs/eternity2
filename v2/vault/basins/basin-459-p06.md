# Basin 459 on p06 — TIED THE SOTA on a different corner perm

**Status**: TIE of SOTA 459/480. Independently produced on local
pipeline. Distinct basin from the cross-machine 459 (p20).
**Date**: 2026-05-15 17:01 CEST.
**Source**: vol-60 T7 ALNS phase, seed=2 from p06's merged partial.

## Verification

- Score: 459/480 matched edges (rescore_board confirmed).
- Placed: 256/256.
- Piece-uniqueness: 256/256 unique. ✓
- Canonical hints obeyed: 4/5 (pos 210 has piece 247 instead of
  canonical piece 180 — typical of relaxed-canonical records like
  vol-32's 458 at 3/5 hints).

## The corner perm

- Perm ID: **p06**
- (TL, TR, BL, BR) = (1, 0, 2, 3)
- Pieces: TL=piece 1, TR=piece 0, BL=piece 2, BR=piece 3.

This is DIFFERENT from the cross-machine SOTA which used p20 (3,1,0,2).
**Two distinct corner perms → two distinct 459 basins.**

## How it was reached

1. **CP stage**: `vanilla_fast --pin-hints --extra-hint 0:1:3 --extra-hint 15:0:0 --extra-hint 240:2:2 --extra-hint 255:3:1 --budget-ms 300000` produced a depth-210 / score-433 partial.
2. **Merge**: vol60_merge_corners.py filled BL+BR pins (vol-60 quirk: CP doesn't reach them at depth 210).
3. **ALNS stage**: `alns_only --cp-board <merged> --alns-budget-ms 300000 --seed 2 --ops winning5 --t 1.0 --extra-hint 0 --extra-hint 15 --extra-hint 240 --extra-hint 255`.
4. Result: 459/480 at seed=2.

**Total compute**: 5min CP + 5min ALNS = 10min on 1 thread.

## Significance

**Status: ambiguous pending direct JSON comparison.**

This 459 was produced locally on corner perm p06 = (1,0,2,3) via
vanilla_fast pin-hints + ALNS seed=2. The cross-machine SOTA bucas
URL appears to encode corner perm p20 = (3,1,0,2), but the URL uses
a color labeling possibly σ-permuted from our pt space, making the
decode unreliable.

**Possible interpretations**:
- (a) Different 459 boards (independent basins). Likely if our
  decode of the SOTA's corners is correct.
- (b) Same 459 board viewed through different color labelings.
  Possible if σ is what makes the URL look different.

**To resolve**: compare piece_id at corners (pos 0, 15, 240, 255)
between our JSON and the SOTA's JSON. Piece IDs are unambiguous; if
they match, same board; if they differ, distinct basins.

What we KNOW:
- Our local pipeline (5min × 4 seeds × 24 perms with corner pinning)
  reached 459 in compute equivalent to about 10 min on 1 core for the
  winning job (p06 seed 2). The cross-machine SOTA took 30 min for the
  record-breaking job + ~30 core-hours of pipeline. Our shortcut may
  be replicating their result rather than finding a different basin.

## What this implies

- Brief ALNS budgets (5min, ops=winning5) CAN reach 459 with the
  right corner perm. The 30min ALNS basic seed=42 isn't required;
  it just helps.
- The corner-sweep was the right call — pinning all 4 corners is
  the lever that opens new basins.
- **There may be more 459 basins in the remaining (untested) perms.**
  The ALNS chain still has 72/96 jobs to go.

## Open questions

- Does the running chain produce ANOTHER 459 or higher? Monitoring.
- Are p06 and p20 in the same fundamental basin family (different
  σ-permutation) or genuinely different basins? Cell-by-cell diff
  TBD.

## Files

- `output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json`
- Source: `output/vol-60/corner_alns_pinned_alns_v3_20260515T164101/result_p06_seed2.json`
- Original merged input: `output/vol-60/corner_merged_v2_20260515T162511/p06_merged.json`
- Original sweep CP: `output/vol-60/corner_sweep_v2_20260515T162511/p06_best.json`

## Linked

- [[basin-459-pt]] — cross-machine SOTA, p20 perm
- [[../concepts/corner-permutation-study]] — full 24-perm analysis
- [[../sessions/vol-60]] — this session
