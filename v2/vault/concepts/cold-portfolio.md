---
tags: [concept, infrastructure, portfolio]
status: built
origin-vol: 17
---

# Cold portfolio

**Status**: `built` (vol-17)
**Origin**: vol-17 idea L
**Files**: `crates/bench-audit/src/bin/cold_portfolio.rs`, `overnight_chunk_logs/`

## Definition

Cold-start portfolio runner: fan out N parallel chunks, each running CP + ALNS independently, log per-chunk best score + provenance. Used to:
1. Compare profiles head-to-head (e.g. `calibrated_v17a` vs `v17b`).
2. Measure variance across seeds.
3. Catch tail-of-distribution best scores that wouldn't show in single-shot runs.

## Vol-17 overnight finding

21 chunks × 10+10min CP+ALNS:
- **F4**: v17b outperforms v17a by **+4.3 matches mean**.
- **F2**: ALNS nondeterminism from parallel `gacolor_ac3` inside `cp_repair` — variance up to **11 matches** between repeats.
- **F3**: H22 Blackwood tie-shuffle gives **+2-3 CP improvement** (tiebreak under iso-score).
- **F5**: portfolio trapped in v17a basin; v17c/v17e never ran.
- **F6**: ALNS lift stable **+86 ± 3 matches** across 21 chunks.

Best overnight: **453/480** (chunk 19, v17b, H22=0 tie-shuffle).

## Limitation discovered

The portfolio runner has implicit feedback loops (best-score-broadcasting → all chunks converge on v17a basin). For true diversity, **chunks must be independent** — different schedules, different seeds, different scan orders, no shared best.

→ Backlog: `independent-cold-portfolio` — drop the broadcast.

## Linked concepts

- [[blackwood-schedule-calibration]] — the schedule variants compared
- [[engine-profile-registry]] — profile registry the portfolio iterates over
- [[alns]] — the H6 op-dilution finding was made via this infrastructure

## Linked memory

- `project_e2_vol17_session_summary`
- Overnight chunk logs (vol-17)
