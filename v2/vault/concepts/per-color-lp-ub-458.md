# Per-color LP UB on vol-32 458 board (vol-45)

**Status**: measurement.
**Origin**: vol-45 diagnostic. Extended `border_ub.rs` to report
per-color y-sums.

## Per-color I-I LP UB

| Colour | I-I LP UB | Combinatorial cap |
|:---:|---:|---:|
| 1, 2, 3, 4, 5 (rare) | **0.000** | 12 each |
| 6 | 19.918 | 24 |
| 7 | 19.000 | 24 |
| 8 | 20.792 | 24 |
| 9 | 20.922 | 24 |
| 10 | 22.837 | 24 |
| 11 | 23.644 | 25 |
| 12 | 23.000 | 25 |
| 13 | 22.000 | 25 |
| 14 | 21.161 | 25 |
| 15 | 19.000 | 25 |
| 16 | 20.930 | 25 |
| 17 | 23.000 | 25 |
| 18 | 22.286 | 25 |
| 19 | 19.000 | 25 |
| 20 | 21.489 | 25 |
| 21 | 22.000 | 25 |
| 22 | 23.000 | 25 |
| **Total** | **363.978** | (420 hypothetical, 364 grid) |

## Key observations

### Rare colours (1-5) contribute 0 to I-I

This is structural, not a bug. The rare colours appear ONLY on
border-piece interior sides (per [[rare-opposite]] / vol-7 finding).
Rare-colour sides exist only on edge/corner pieces. They cannot
be on I-I edges (where both cells are interior pieces). Therefore
rare-colour I-I matches are *always* 0.

### LP UB on I-I is essentially tight

LP UB(I-I) = 363.98 ≈ 364 = number of I-I edges. The LP barely
admits ANY I-I slack on the 458 border.

### The 2-point gap is in B-I, not I-I

LP UB total = 478 = 60 (B-B) + 54.02 (B-I LP) + 363.98 (I-I LP).
Combinatorial max = 480 = 60 + 56 + 364.

**Gap by source:**
- B-B: 0 (perfect)
- B-I: 56 → 54.02 → **2-point loss**
- I-I: 364 → 363.98 → 0.02 loss

**The LP says: of 56 B-I edges, 2 are structurally unmatchable
on this border.** That's the entire LP-vs-combinatorial gap.

## Why this matters

The 458 board has 4 B-I mismatches empirically (matched 52/56).
The LP says only 54 of 56 can match in any completion = 2
unmatched-forced. The 458 board has 4 unmatched B-I, so 2 extra
B-I are "unforced" — could be theoretically fixed.

But fixing those 2 B-I might require breaking I-I matches, since
the LP I-I UB is essentially tight.

This is the same 20-point integer gap from earlier (LP UB 478,
integer 458). 18 of the 20 are in I-I; 2 are in B-I.

## Implications

To break 458 within this basin: any improvement must come from
fixing B-I edges. Currently 4 unmatched B-I; LP says at most 2
can be improved on this border (the other 2 are structurally
unfixable). So **the maximum theoretical lift within this
border is + 2 score = 460**. But the LP relaxation may overstate
achievable lift (the +2 may not be integer-feasible).

To exceed 460 on canonical 5-clue, we need a **different border**
(different B-I structure).

## Linked

- [[lp-ub-478-basins]]
- [[color-multiset-bound]]
- [[458-class-A-mismatch-structure]]
- [[vol-44]] — predecessor
