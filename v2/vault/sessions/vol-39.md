# Vol-39 — large-window basin-escape from canonical 454 (modest lift)

**Theme**: After vol-38 showed local prune-restart cannot lift canonical
454, try larger destroy operators (drop-100, ALNS-diverse with BottomBandDestroy).

## What was attempted

T1a — `drop-k=100` prune-restart from canonical 454, 60s MaxScore CP:
  - dropped 138 cells (38 mismatch + 100 halo), 118 pinned
  - CP partial: 238/256 placed, score 398 (no full fill in 60s).

T1b — ALNS-diverse 8 seeds × 5min from canonical 454:
  - 2 seeds → 455 (NEW canonical record class, +1 over starting)
  - 6 seeds → 454 (unchanged)

## What was measured / kept

**Two NEW verified canonical 455 boards** (5/5 hints, piece-unique,
distinct from each other — 54 cells differ):
- `output/vol-39/records/RECORD_CANONICAL_455_vol39_diverse_seed1.json`
- `output/vol-39/records/RECORD_CANONICAL_455_vol39_diverse_seed5.json`

Both produced by ALNS-diverse (winning5 + BottomBandDestroy etc.) from
canonical 454. **+1 score over starting 454.** Still below canonical
456 record (vol-32 blackwood_raw seed 2).

## What this confirms

- Canonical 454 basin's ALNS-escape ceiling under "diverse" ops ≈ 455.
- 2/8 = 25% hit rate for the 455 lift — modest but reproducible.
- The BottomBandDestroy ops in "diverse" preset DO help (vs vol-36
  "winning5" preset which capped at 454).
- drop-100 prune-restart needs more compute than 60s — the 138-cell
  refill is too big a CP problem.

## What's NOT a null

- Canonical 455 is a **new record-class** for vol-37-39 work (made-canonical
  pathway from vol-32 458). Doesn't beat existing canonical 456-457 records.
- But it shows the pathway from canonical 454 → canonical 455 is
  reproducible at ~25% rate.

## Records ledger (UPDATED)

| score | canonical | source |
|---:|:---:|---|
| 458 | 3/5 | vol-32 vanilla_fast → ALNS (unchanged) |
| 457 | 5/5 | vol-32 blackwood_mrv × 3 (unchanged) |
| 456 | 5/5 | vol-32 blackwood_raw seed 2, 4 (unchanged) |
| **455** | **5/5** | **vol-39 diverse seed 1, 5 (NEW × 2 distinct)** |
| 454 | 5/5 | vol-36 make-canonical → ALNS seed 5 |

Cold-start canonical-best: still 457.
Cold-start absolute-best: still 458 (3/5).
NEW canonical pathway: vol-36 make-canonical → vol-39 ALNS-diverse → 455.

## Open at close

The vol-37-39 series produced:
- Real tools: structural_scan, make_canonical, gh_e2, vanilla_path
- Real records: 2× canonical 455 (NEW), canonical 454 (NEW)
- Honest nulls: prune-restart-mismatch-drop can't lift canonical 454; gh_e2
  relaxation gap dominates; pos 161 hint helps +4 only.

Realistic ceiling for our stack: ~458 (existing) or 459 with luck. To
materially break 458→469, need community-class compute or new algorithm.

## Linked

- [[vol-38]] — predecessor (local prune-restart can't lift)
- [[basin-escape-recipe]] — what we sort-of did, with smaller K
