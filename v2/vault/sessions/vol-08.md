# Session — vol-08

**Theme**: Community-export mining. Verification of canonical-5-clue SOTA = 469 (McGavin 2020).
**Raw**: [[../sessions/archive/raw/RESEARCH_NOTES_8|RESEARCH_NOTES_8.md]]

## What was attempted

- Mine 11,511 groups.io messages (2000-2026) + 1,198 Discord messages (2021-2026).
- Decode 123 bucas URLs to JSON boards.
- Identify and verify the actual community ceiling on canonical 5-clue E2.

## What was measured / kept

- **[[community-corpus]] built**: `output/v8_grep/corpus.txt` (27.6 MB) + per-pattern hit files + 123 decoded boards.
- **Canonical 5-clue ceiling VERIFIED: 469/480** by Peter McGavin (2020-09-09), using Joshua Blackwood's solver on ~200 cores for "a few days". groups.io msg 172011298. All 256 pieces in IDs 1..256.
- **Previous lore "467 Verhaard" is stale**: correct for 2008, but the community moved to 469 in 2020 and has held.
- **5 unported hobbyist techniques catalogued**:
  - anr_56 Eulerian-cycle border propagator (refuted vol-9)
  - Verhaard set-tilability swap-annealing (porting partial, vol-9)
  - Phase-2 mismatch-allowed endgame (Max/Verhaard "Robby" 2008)
  - Piece-budget warm-start (Hopfer 2021)
  - onesmallstep inter-piece-incompatibility list (2026 Discord, live)

## Confounds rejected

- McGavin's "480" (2023-10-09): mixed Clue1 + Clue2 piece sets, not canonical.
- McGavin's 471 / Razvan 480: on Joe's 17-color and Brendan's 16×16 variants.
- 3 boards labelled 470 (Blackwood 2021-03-30, capiman 2021-12-24, onesmallstep 2025-07-16): all on Blackwood-unframed/0-clue variant. Confirms [[reference-blackwood-decoded]].
- Takahashi 468 (2009): on TopCoder unframed variant.

## Concepts touched

- [[community-corpus]] (introduced)
- [[eulerian-border]] (catalogued, refuted vol-9)
- [[verhaard-set-sa]] (catalogued, ported small-signal vol-9)
- [[blackwood-algorithm]] (algorithm spec mined here, ported vol-14/15)
- [[mcgavin-engine]] (throughput target identified here)

## Open at close

Port the catalogued techniques. Vol-9 starts the port queue.

## Linked memory

- `reference_e2_community_corpus`
- `reference_community_e2_ceiling`
- `reference_blackwood_decoded`
- `reference_verhaard_actual_method`
