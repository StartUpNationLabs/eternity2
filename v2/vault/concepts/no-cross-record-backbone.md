# No cross-record piece-position backbone — vol-68 (2026-05-15)

**Status**: `built` — vol-68.
**Origin**: cross-record agreement analysis of 5 high-score records.

## The finding

Across 5 high-score E2 records:
- McGavin 469
- local-459-p06
- vol-32-458
- vol-61 458 (seed17)
- vol-61 458 (seed200)

For each of 256 cell positions, what's the agreement on (piece, rotation)?

| agreement level | # positions |
|---|---|
| 5-of-5 (universal backbone) | **0** |
| 4-of-5 | **0** |
| 3-of-5 | 5 |
| 2-of-5 or 1-of-5 | 251 |

**ZERO positions have universal agreement.** Even the 5 canonical
hints (which the puzzle generator pinned) don't appear in all 5
records — vol-61 boards use piece 145 instead of canonical 138 at
the center clue.

## 3-of-5 positions

The 5 cells with 3-of-5 agreement:
- pos 15 (r0,c15): piece 3 in 3 records, piece 0 or 2 in others
- pos 119 (r7,c7): piece 71 in McGavin + 2 vol-61
- pos 120 (r7,c8): piece 195 in McGavin + 2 vol-61
- pos 135 (r8,c7): piece 138 (canonical center hint) in 3 records;
  vol-61 uses piece 145
- pos 207 (r12,c15): piece 9 in McGavin + 2 vol-61

The 3-of-5 agreements cluster around **center-row** (pos 119, 120,
135, 207). vol-61 boards + McGavin agree near the center; our
other basins (local-459, vol-32) disagree.

## Bias detected

**vol-61 sister-basins + McGavin show structural agreement on
center cells** that local-459 and vol-32-458 don't. Hamming
distances confirm: vol-61-s200 is at 248/256 from McGavin, the
smallest distance among all our records.

This suggests: **vol-61 pipeline lands in a basin family
"adjacent" to McGavin's in piece-placement space**, while vol-60
and vol-32 pipelines land in DIFFERENT families farther from
McGavin.

## Implications

1. **No "universal" structural backbone exists** — every cell
   admits multiple high-score placements.
2. The 5 canonical hints are NOT preserved by all our records;
   the matched-edges record convention allows hint violations.
3. **vol-61 pipeline geometry is closer to McGavin's** than our
   other pipelines. If we want to reach McGavin's basin, vol-61
   pipeline variants are the right starting points.

## Linked

- [[basin-permutation-group]]
- [[mcgavin-n-row-scaling]]
- [[e2-maximally-adversarial-thesis]]
