---
name: vol121-458-corner-perm-2310
description: "Vol-121 T1b: THIRD distinct 458 basin found. Corner perm (2,3,1,0) — different from vol-32 458's (0,3,1,2) and vol-119 p18 458's (3,0,2,1). 0/5 hints (1-clue convention). Source: vanilla_path border-first NO --pin-hints × 8 threads × 30min → 222-cell partial, then ALNS basic 30min seed=42 → 458/480. Verified piece-unique, no border violations. Diff against vol-32 458 = 4/256 same; diff against vol-119 p18 458 = 0/256 same — three structurally disjoint 458 basins now in corpus."
metadata:
  type: project
status: built
---

# Vol-121 458 at corner perm (2,3,1,0) — NEW basin

## Discovery

Vol-121 T1b setup:
1. `vanilla_path --path-mode border-first --threads 8 --thread-id-offset 0
   --budget-ms 1800000` (NO `--pin-hints`) produced
   `partial_off0.json`: 222/256 placed, 395/395 matched, corner perm
   **(2, 3, 1, 0)**, 0/5 hint compliance.
2. `alns_only --cp-board partial_off0.json --alns-budget-ms 1800000
   --seed 42 --ops basic` → **458/480**, 256/256 placed, piece-unique,
   0 border violations, 0/5 hints.

Wall: 30min vanilla + 30min ALNS = 60min on apple-m1.

## Verification

- `verify_board`: LEGAL_INCOMPLETE_HINT (illegal-by-hint only — pieces
  unique, borders clean).
- `diff_boards vs vol-32 458` (`RECORD_BREAK_458_vanilla_fast_alns.json`):
  **4/256 cells match (1.6%)** — distinct boards.
- `diff_boards vs vol-119 p18 458` (`sweep_p18_s2_alns.json`):
  **0/256 cells match (0.0%)** — completely disjoint piece placements!
- Corner perm (2, 3, 1, 0) does not appear in any prior record.

## Corner-perm × score landscape (updated)

| Corner perm | Best score | Hints | Source | Status |
|-------------|-----------:|------:|--------|--------|
| (0,2,1,3) | 457 | 5/5 | vol-32 blackwood_mrv | strict-canonical record |
| (0,3,1,2) | 458 | 3/5 | vol-32 RECORD_BREAK | basin family A* |
| (1,0,2,3) | 459 | 4/5 | vol-60 RECORD_TIE | matched-edges record |
| **(2,3,1,0)** | **458** | **0/5** | **vol-121 T1b-early s42** | **NEW** |
| (3,0,2,1) | 458 | 3/5 | vol-119 sweep_p18 | NEW vol-119 |
| (3,2,0,1) | 469 | 1/5 | McGavin community | 1-clue champion |

**Six distinct corner perms now have known 457+ basins.** Of 24 total
perms, 18 remain unprobed at high-budget ALNS.

## Significance

1. **Strongest evidence yet that corner-perm diversity matters**. Three
   458 basins, three corner perms, near-zero piece overlap. The 458
   "level set" is wide, not a single basin.
2. **Confirms T1b pipeline (no --pin-hints) works at scale**: 30min ×
   8 threads vanilla_path reaches 222-cell partial; basic ALNS 30min
   lifts to 458 on seed=42 (variance: 454/457/458 across seeds 1/7/42).
3. **Vol-119 T5 corpus-restricted region MIP now needs re-running on
   the enlarged corpus** including this 458. Hypothesis: the MIP
   might find a Δ>0 mix because the new basin contributes pieces no
   existing basin had at certain positions.

## Saved

- Master copy: `output/vol-121/early_alns_20260516T220918/alns_off0_s42_alns.json`
- Corpus copy: `output/vol-119/corpus_full_20260516T195224/vol121_off0_s42_458.json`

## Pending

- Repeat MIP-region halo-15 with enlarged corpus.
- Test the other 18 untested corner perms (vol-122+).
- Variance: seeds 1=454, 7=457, 42=458 — basin is reachable but
  seed-sensitive; longer ALNS might lift further.

## Linked

- [[corpus-restricted-region-mip-locked]]
- [[p18-s2-458-new-basin-family]]
- [[vanilla-path-pin-hints-depth-wall]]
- [[vol-121]]
