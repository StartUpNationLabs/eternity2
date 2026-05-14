# Vol-40 — ALNS-diverse from canonical 457 (honest null)

**Theme**: Test if "diverse" preset (winning5 + BottomBandDestroy) lifts
canonical 457 → 458 like vol-39's lift of 454 → 455.

**Status**: Done. **Honest null at vol close.**

## What was attempted

24 ALNS-diverse runs:
- 3 source boards × 8 seeds × 5min each
- Sources: vol-32 blackwood_mrv 5min seed 7, seed 10, 30min seed 4
- Ops: "diverse" (winning5 + BottomBandDestroy)

## What was measured

**24/24 stayed at 457**. Not a single seed produced 458.

| Source | Best seed score | Range |
|---|---:|---|
| blackwood_mrv 5min seed 7 | 457 | all 8 at 457 |
| blackwood_mrv 5min seed 10 | 457 | all 8 at 457 |
| blackwood_mrv 30min seed 4 | 457 | all 8 at 457 |

## What this confirms

Vol-22 was right: **canonical 457 is ALNS-locked**, including under
the "diverse" preset with BottomBandDestroy. The local move set
(WorstWindow, ConflictDriven, MwpmDefectPair, WorstBand, BottomBandDestroy,
etc.) cannot find a 457 → 458 transition from these 3 basins.

The diverse-preset 454 → 455 lift (vol-39) was a smaller hop that
happened to be within reach; 457 → 458 requires a longer-range cluster
move that ALNS doesn't have.

## What this differs from vol-22

Vol-22 used "winning5" preset only. Vol-40 used "diverse" (which adds
BottomBandDestroy). Same null result. So adding BottomBandDestroy to
ALNS doesn't help on saturated 457 basins.

## Records ledger (no change)

| score | canonical | source |
|---:|:---:|---|
| 458 | 3/5 | vol-32 vanilla_fast → ALNS (unchanged) |
| 457 | 5/5 | vol-32 blackwood_mrv × 3 (unchanged) |
| 456 | 5/5 | vol-32 blackwood_raw seed 2, 4 (unchanged) |
| 455 | 5/5 | vol-39 diverse seed 1, 5 (NEW × 2, from vol-39) |
| 454 | 5/5 | vol-36 make-canonical → ALNS seed 5 |

## Open at close

**The vol-37-40 series has measured the local-ALNS ceiling:**
- canonical 454 → ALNS-diverse: max 455 (25% rate)
- canonical 455 → ALNS-diverse: not tested
- canonical 456 → ALNS-diverse: not tested
- canonical 457 → ALNS-diverse: 0/24 lift (this volume)

Suggests the "ALNS ceiling per basin" is ~+1 score. To go from 454 to
458, we'd need 4 chained lift events (each ~25% rate × increasing
difficulty). Statistically: P(454→458) ≈ 0.25^4 ≈ 0.4% per "chain".

Per the vol-38 finding (canonical 454's 38-cell mismatch region has
CP-ceiling 431), there are fundamental structural limits to local
moves. To break canonical 458, need:
- **Community-class compute**: McGavin's 469 was a 2-week Blackwood
  pre-prune + 11-hour SAT solve.
- **Or new algorithm**: RL self-play, exact MaxSAT, gradient + neural projection.

Both are 1-2 week builds with no record-break guarantee.

## Next direction (vol-41+)

Honest assessment: with ~6 days of M1 compute remaining, **realistic
ceiling is 458-459**. The vol-37-40 series produced:
- Tools: structural_scan, make_canonical, gh_e2, vanilla_path, vanilla_fast
  --extra-hint
- Records: canonical 454 (NEW), canonical 455 ×2 (NEW)
- Honest nulls: documented prune-restart, ALNS-diverse, gradient ceilings

Recommend vol-41 = **stabilization + documentation**, not more lottery.
Polish existing tools, write up findings clearly, leave the project in
a state where future researchers can pick up. The records are unlikely
to break without a fundamentally new approach.
