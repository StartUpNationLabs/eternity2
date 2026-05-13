---
tags: [basin, community, reference, target]
status: external-target
score: 469
variant: canonical-5-clue
---

# Basin McGavin-469 (verified canonical 5-clue community SOTA)

**Score**: 469/480
**Variant**: canonical 5-clue Monckton E2 (the target we work on)

## Discovery

Peter McGavin, posted to groups.io 2020-09-09 (message 172011298, subject "EternityII Solver"). All 256 pieces verified by decoding `board_pieces=` field of bucas URL; IDs in 1..256.

Achieved by running Joshua Blackwood's solver (`github.com/jblackwood345/EternityII_Solver`) on "a couple of hundred cores for a few days".

## Why this is THE target

- **Verified**, decoded, reproducible to inspection.
- **Canonical 5-clue Monckton**: same puzzle we work on (not 0-clue, not 1-clue, not 17-color variant, not 16×16 alt).
- **Held since 2020**: ~5 years, multiple active solvers (reinout_, onesmallstep) chase but haven't exceeded.

## Mismatch geometry

The McGavin 469 board has mismatches concentrated in the **TOP rows** (matches [[basin-447-top-row]] geometry). Same as community 468s. INVERTS our vol-6/vol-14 boards (center-BOTTOM).

→ Bottom-up scan order ([[scan-order|RowMajorBottomUp]] in Blackwood) is the cause.

## Why our stack hasn't reached 469

Per [[mcgavin-blackwood-gap-analysis]]: 4 orthogonal gaps:
1. **Heuristic-color schedule** (vol-15+ partial, vol-17 calibrated).
2. **Break-index allowance** (vol-15 partial).
3. **In-place prune-back-to-T restart** (vol-23 shipped — see [[prune-restart]]).
4. **Per-cell unrolled goto + 4-axis fit_table** (vol-16 partial; ~800× slower than McGavin).

Estimated wall-clock at our throughput to match a single McGavin run: ~40 days. **Cannot brute-force; need the algorithm + engineering.**

## Confounds (NOT canonical 5-clue, do not confuse)

- McGavin's "480" (2023-10-09): mixed Clue1 + Clue2 piece sets (board_pieces > 256).
- McGavin's 471 / Razvan 480: Joe's 17-color and Brendan's 16×16 variants.
- Blackwood's 470 (2021-03-30 + others): Blackwood-unframed/0-clue variant — see [[basin-blackwood-470]].
- Takahashi's 468 (chokudai 2009): TopCoder unframed variant.

## Files

- `output/community_corpus/groups_172011298_469.json` after running `scripts/community_extract_bucas.py`.
- Index: `output/community_corpus/_index.tsv`.

## Linked concepts

- [[community-corpus]]
- [[mcgavin-blackwood-gap-analysis]]
- [[blackwood-algorithm]]
- [[basin-447-top-row]] — same geometry on our smaller-score basin

## Linked memory

- `reference_community_e2_ceiling`
- `project_e2_mcgavin_blackwood_gap_analysis`
