---
name: vol122-prune-restart-bf-bw-partial
description: "Vol-122 prune_restart with MaxScore on bf_bw 5min 236-cell partial (424 start): stagnates at round 2 with 399. The vol-22 'score collapse after bound-ascent' pattern reproduced."
metadata:
  type: project
---

# Vol-122 — prune_restart on bf_bw partial

## Setup

Input: `output/vol-122/restart/bf_bw_v17a_5min_so2000.json`
  (236 placed cells, 424 matched, 5/5 hints obeyed, LEGAL_PARTIAL)

Tool: `prune_restart --rounds 10 --drop-k 30 --max-score --cp-budget-ms 60000`

## Result

| Round | n_pinned | depth | score | bound | time |
|---|---|---|---|---|---|
| 1 | 174 | 39 | 343 | 455 | 60.3s |
| 2 | 213 | 43 | 399 | 446 | 60.1s |
| 3 | — | — | — | — | STAGNATED (no score lift, bound dropping) |

**Final best: 424** (= the starting score; no improvement).
**STAGNATED early** because bound dropped 455 → 446 in 2 rounds (vol-22-memo'd pattern).

## Interpretation

Same as vol-22: prune_restart's MaxScore CP CAN find local re-arrangements
of the dropped cells, but the resulting score is LOWER than the original
because:
1. Dropping 30 mismatch cells + halo (=82 cells total) destroys 50+ existing matches.
2. MaxScore CP on the dropped region only finds 343/399 matches — less than the 82 cells were contributing before.
3. Net negative.

The vol-25 memo notes this; prune_restart's "stagnation detector" stops early.

## What this rules out

prune_restart with MaxScore on bf_bw 236-cell partial doesn't help.
Confirms the vol-22 finding: bound-ascent CP-fill doesn't beat the
starting ALNS-fill score on 234+ partials.

## What might still work

- **Smaller drop_k** (10 vs 30): preserve more existing structure.
- **Pin-mismatch + repair-mismatch-only**: drop ONLY the mismatch cells (52), not the halo.
- **ALNS instead of MaxScore CP**: ALNS handles iso-score plateaus better.
  (= what we're doing in the bf_alns multi-seed runs anyway.)

## Status

`built-tested-confirms-vol22-stagnation`

## Linked

- [[../sessions/vol-122]]
- [[../concepts/vol122-a1-pipeline-result]]
- [[bf-bw-schedule-hinted]] (if exists)
- vol-22 prune_restart-stagnation note (memory)
