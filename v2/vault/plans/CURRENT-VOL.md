# VOL-40 — ALNS-diverse from canonical 457 (blackwood-family)

**Opened**: 2026-05-14 ~18:06 CEST at vol-39 close.
**Status**: BINDING. ONE binding item.

## Why this volume + this item

Vol-22 measured: canonical 457 is "ALNS-locked" under all prior ops.
That measurement used "winning5" preset.
Vol-39 found "diverse" preset (winning5 + BottomBandDestroy) lifts
canonical 454 → 455 at 25% rate.
Question: does "diverse" preset lift canonical 457 → 458?

If yes: NEW canonical 458 record. Beats existing 3/5-hint 458.

## Vol-40 binding item

### T1 — ALNS-diverse 8 seeds × 5min from canonical 457 (×3 sources)

For each of vol-32's 3 canonical 457 boards, run ALNS-diverse 8 seeds × 5min.
Total: 24 runs. ~30 min wall on 8 cores.

**Gate**:
- Any seed produces verified canonical ≥458.
- Or honest null: 457 is locked under diverse too.

## Out of scope

- ❌ Any new tool/code.
- ❌ Mid-vol pivots.
- ❌ More variants of make-canonical.

## Linked

- [[vol-22]] — original ALNS-locked finding (with winning5)
- [[vol-39]] — diverse lifts 454 → 455 (the precedent for trying diverse on 457)
