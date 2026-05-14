# Vol-35 — pin_hints duplicate-piece bug + retraction of vol-34 records

**Date**: 2026-05-14 (vol-35 mid-vol).
**Status**: bug found, 3 save paths fixed, 2 record claims retracted.

## The bug

`vanilla_fast --pin-hints` writes board snapshots/saves. When the
algorithm reaches max_depth but hasn't yet placed the canonical
hint pieces at their target positions, the snapshot-writer FILLS
those positions with the canonical hints — without checking whether
the hint piece is ALREADY placed somewhere else in the board.

E2 hints: pos 34=pid207, 45=254, 135=138, 210=180, 221=248.

If the algorithm has placed piece 180 at some non-hint position
(say pos 178) by depth 200, and we save with hints filled in:
- snap[178] = (180, r) — placed by algorithm
- snap[210] = (180, 1) — pin_hints fill

Duplicate piece 180 in saved board.

ALNS started from this duplicate-piece partial produces a "256
piece" board with the same duplicate, scoring "matched edges" as
if all edges count. The score is INVALID as a canonical-E2 claim.

## Discovery

Found by piece-uniqueness check on records during vol-35 mid-vol
record-chase. 221/225 sweep snapshots had duplicates. The 7th-457
basin claim from family 255 was actually the bug's artifact.

## Fix sites (vol-35)

Three places in `vanilla_fast.rs` that fill pin_hints had the bug:
1. Periodic snapshot writer (`--snapshot-dir` path) — fixed earlier.
2. Per-thread save-best (`--save-best` with multi-thread) — fixed now.
3. Single save-best (`--save-best` with single-thread) — fixed now.

All three now check `already_placed` HashSet before filling.

## Retractions

| Record | Vol claimed | Verdict |
|---|---|---|
| vol-32 458 RECORD_BREAK | vol-32 | VALID — stands |
| vol-32 457 blackwood_mrv ×3 | vol-32 | VALID — stand |
| vol-34 #1 "457 record-tie" | vol-34 T3 | RETRACTED (dup 180+248) |
| vol-34 #2 "457 record-tie" | vol-34 T3 | RETRACTED (dup 180+248) |
| vol-35 family 255 "457×3" | vol-35 T1c | RETRACTED (dup 180+248) |
| vol-35 458 reproduce | vol-35 T-deep458 | VALID — stands |

## Implication for project state

- Vol-32's 458 record still stands as the all-time cold-start best.
- Vol-32's 3 distinct 457 basins still verified.
- Vol-34 added ZERO new valid record claims. Its T1+T2+T3 work
  remains useful as infrastructure (snapshot probe, encoding
  reconciliation, polish_swap bug fix) but the "record discovery"
  was a measurement artifact.
- Vol-35 successfully reproduced the vol-32 458 (1/16 ALNS hits 458
  on the same partial with different seed/ops). Same basin, valid.
- Vol-35's "7th 457 basin" claim retracted.

## Vol-35 next steps

- Re-run probes WITH the bug-fixed binary (snapshots now valid).
- Re-verify any post-bug-fix records by piece-uniqueness.
- Total count of distinct verified 457 basins is 4
  (vol-18 + vol-32-seed7 + vol-32-seed10 + vol-32-seed4-30m), not 7.
