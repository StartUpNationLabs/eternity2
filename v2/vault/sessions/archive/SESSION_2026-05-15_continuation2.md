# Session continuation 2 (2026-05-15 22:00 — onwards)

User signals received:
- "Continue going on your stuff, mark mine as TODO" (re: 469 vs 470 basin
  question)
- "User is away for 1 month. You are on your own."
- "Invent new stuff that even has no name yet"
- 1h cron at :17 for periodic deep-breath check

## Session 2 progress (22:00 — 22:50, 50 commits cumulative)

### CAS algorithm invented + tested

**Concentric Annular Solving (CAS)**: NEW algorithm, no prior name.
Solves canonical E2 in 8 concentric annular layers via MIP per shell.

Shell-by-shell measurement (CAS-fixed):
- Shells 0-2 (frame + 2 rings): PERFECT 252/252 matched
- Shells 3-7: 71/72, 53/56, 34/40, 16/24, 4/8 (progressive failure)
- Total: 433/480 (verified)

CAS-hybrid (CAS-outer-prefix + ALNS-inner) = 418/480.

Both below standard ALNS pipeline's 459. Greedy-annular suffices
for outer 3 shells but doesn't extend to deep inner.

### NEW 469 board found

Pieces 234↔235 swap at positions 73↔75 of McGavin's 469 = a SECOND
unique 469 on canonical E2. First evidence the 469 score-level set
contains multiple configurations.

Both single and double near-twin swaps on McGavin tested. No 470+
found.

### Δ-invariant corrected

Fixed implementation of NS-1 Δ (excludes corners per vol-11 def):
- McGavin-469: Δ=1
- NEW-469-near-twin: Δ=1 (same)
- local-459: Δ=2
- 458 boards: Δ=3-4

Δ correlates negatively with score. Δ=0 needed for 480.

### Vol-22 471-bound REFUTED

Vol-22 memory claimed "basins with ceiling 471" via bound-ascent
recipe. CLAUDE.md rule 1 warned relaxed_bound is NOT sound. Tested
b471 boards via ALNS 5min × 4 seeds: max 430/480, far below 471.

The vol-22 "ceilings" are heuristic-not-sound. Bound-ascent doesn't
help break 459.

### Top-row + N-row scaling

- McGavin top-row alone (16 cells pinned) → 400/480 via our ALNS
- McGavin top-14 rows (224 cells pinned) → 469 reconstruction
- Cross-basin N-row: only McGavin's basin shows the sharp threshold
- Refutes 'top-row determines basin' strong hypothesis

### Basin landscape confirmed

47 basin-components from 135 records. McGavin = size 1. Min
Hamming to McGavin from any non-clone record = 247.

vol-61-s200 closest to McGavin (Ham 248). Our 4 pipeline basins
all > 248 Hamming from McGavin.

## Standing record

459/480 (unchanged). 2 unique 469 boards on canonical E2 (was 1).

## TODOs and tasks

- Vol-63 Temporal-Rewind-Search (pending, spec only)
- Vol-67 FCD (pending, spec only)
- Vol-69 OA-ALNS (spec only)
- Vol-70 RGS (refuted in part)
- USER TODO #141: find/prove if 469+470 share basin

## Direction

Maximally-adversarial thesis stands. ~20 axes verified. Breaking 469
requires:
- ML/RL with many 469 examples (need more data)
- Long-compute on McGavin-style Blackwood (multi-day)
- Genuine new math (no clear source)

Session 2 has been productive in characterization but no record
break. The cron at :17 keeps the rhythm.
