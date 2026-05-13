# Session — vol-17

**Theme**: Blackwood schedule calibration. ALNS portfolio of 10 ops. Cold-start record 455/480.
**Raw**: [[../sessions/archive/raw/RESEARCH_NOTES_17|RESEARCH_NOTES_17.md]], [[../sessions/archive/raw/RESEARCH_NOTES_17_PLAN|RESEARCH_NOTES_17_PLAN.md]], [[../sessions/archive/raw/RESEARCH_NOTES_17_REFRAMING|RESEARCH_NOTES_17_REFRAMING.md]], [[../sessions/archive/raw/RESEARCH_NOTES_17_OVERNIGHT|RESEARCH_NOTES_17_OVERNIGHT.md]]

## What was attempted

- `calibrate_blackwood` bin (469 LoC corpus mining) → schedules `calibrated_v17a/b/c`.
- 10 new ALNS destroy operators: WorstBand, WorstRow, ComponentDestroy, ComponentPlusHaloDestroy, HingeDestroy, ConflictDriven{K up to 80}, polish_rotations, piece_swap_hillclimb.
- `BoardZobrist` module (pre-tabu hash infrastructure).
- `alns_portfolio` parallel chains with temperature ladder.
- `alns_pt_multi_init` with Metropolis exchanges.
- `lex_break_isoscore` tiebreak.
- 21-chunk overnight portfolio + analysis.
- 12 idea-track plan (A–L) including 7 cross-domain reframings (R1–R7).

## What was measured / kept

- **[[blackwood-schedule-calibration]]**: v17b outperforms v17a by **+4.3 matches mean** across 21 chunks.
- **COLD-START RECORD**: **455/480** (vol-17 seed 1) via `calibrated_v17a` + WorstBand + ConflictDriven{80} ALNS.
- **[[basin-447-top-row]]**: `calibrated_v17a` 447 board has all 33 mismatches in rows 0-3 (single 51-cell connected component). Matches community 469 geometry, INVERTS vol-6/vol-14.
- **H22 Blackwood tie-shuffle**: +2-3 CP improvement (iso-score tiebreak).
- **F2 ALNS nondeterminism**: parallel `gacolor_ac3` inside `cp_repair` causes up to 11-match variance.
- **F6 ALNS lift**: stable +86 ± 3 across 21 chunks.

## What was refuted

- **H5**: CP-primary repair regressed vs SA-primary (−8 matches).
- **H6 op-dilution**: 11 ops > 5 ops gives −1 matches. Op selection must be tight.
- **H7**: polish_rot + swap_hillclimb post-ALNS = 0 gain.
- **H9 temperature-insensitivity**: t ∈ [0.5, 5.5] all produce identical scores. **ALNS plateau is iso-score**.
- **H10**: 10min ALNS = 5min ALNS, plateau by iter ~33.
- **456/480 reproducibility**: prior hand-tuned 456 never reproduced under n ≥ 3 (oracle artifact?).
- **R3 OT/Hungarian**: standalone valley-finder (later subsumed in [[basin-escape-recipe]]).
- **R4 piece-side MI**: interior-only signal 0.27 bits / 6.6% (much smaller than initial "1+ bit" claim on full board; the original signal was frame-structure dominated).

## Concepts touched

- [[blackwood-schedule-calibration]] (introduced)
- [[alns]] (10-op portfolio shipped, H6 dilution learned)
- [[cold-portfolio]] (introduced)
- [[parallel-tempering]] (Zobrist infra pre-staged)
- [[mismatch-geometry]] (top-row geometry on calibrated_v17a)
- [[basin-447-top-row]] (new basin page)

## Open at vol-close → vol-18

The 455/480 cold record IS the right kind of incremental progress within "Blackwood class". Beyond: cross-domain reframings (R1–R7) and the [[basin-escape-recipe]] family.

## Linked memory

- `project_e2_vol17_session_summary`
- `project_e2_vol17_blackwood_then_csp`
- `project_e2_vol17_447_top_mismatch`
- `project_e2_vol17_r4_piece_mi`
