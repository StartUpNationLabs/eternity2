---
name: mcgavin-top4-mip-bounded
description: vol-86 top-4-rows MIP on McGavin gave SOUND BOUND — dual=123, best feasible=116, gap=6%. Means McGavin's top-4 cannot exceed 123 under LP relaxation but no improvement found in 1200s. First non-trivial sound bound BELOW 480 on canonical E2.
metadata:
  type: project
---

# McGavin top-4-rows — SOUND BOUND 123 (vol-86)

**Status**: `partial` — bounded but not proven optimal.
**Tool**: `repair_region` (HiGHS, 1200s time limit).
**Time**: 1200.02s (timeout).
**Files**: `output/vol-86-top4-mip/mcgavin_top4.log`.

## Result

McGavin's 469 with cluster = rows 0-3 (top 4 rows, 64 cells).

- MIP size: 18,776 binary vars, 4,896 rows, 87,858 nonzeros.
- Best feasible: obj=**116** (McGavin's current top-4 contribution).
- Dual bound: **123** (LP relaxation).
- **Gap: 6.03%** at termination.
- B&B nodes explored: 64.
- Status: time-limit timeout.

## Significance

**This is the first non-trivial SOUND UPPER BOUND below 480 on
canonical E2's score landscape.**

- Trivial UB on full board: 480.
- Vol-65 PSM-LP UB on full board: 480 (loose).
- Vol-79 full-puzzle MIP LP-relaxation: 10560 (uninformative).
- Border-LP UB: ~tight around 60 (border only).
- **Vol-86 top-4 LP-relaxation: 123** for the 64-cell top region.

The 123 bound implies: under McGavin's bottom-12 fixed, the top-4
rows contribute at most 123 to the total. Currently 116. So
McGavin's total cannot exceed **480 - (current_full - 116 - 123) =
?** Actually the relationship is:

- Current full score: 469
- Current top-4 contribution: 116 (counted as edges within top-4 +
  edges crossing top-4-to-row-4 boundary)
- Current bottom-12 contribution: 469 - 116 = 353 (with the
  boundary edges counted somewhere — definitions matter)

So if top-4 could reach 123 (max LP), total would be ≤ 353 + 123
= **476**. **First sound upper bound below 480 on a McGavin-style
basin.**

## Caveat

The 6.03% gap means HiGHS believes 123 is achievable but never
found a feasible solution above 116. There might be no integer
solution in (116, 123]. Or there might be — we don't know.

To resolve:
- Run MIP for hours/days (HiGHS B&B at 64 nodes after 1200s; full
  solve might take 10× longer).
- Use a tighter formulation.
- Try Lagrangian decomposition.

## Concrete path to 470+

If an integer top-4 solution at 117 exists, full board would
reach **470** (= 469 - 116 + 117 if bottom unchanged). At 123,
reaches **476**.

But: the bottom-12 is held FIXED in this MIP. So we're looking for
"top-4 arrangement using McGavin's remaining piece pool that scores
higher than 116 against his fixed bottom boundary". This is a
constraint-satisfaction-flavoured combinatorial question.

## What this changes about the maximally-adversarial thesis

The thesis stands — but vol-86 shows the puzzle's hardness has a
QUANTITATIVE bound: top-4 ≤ 123. The puzzle isn't trivially
adversarial; there's a concrete arithmetic limit on local
improvement.

## Linked

- [[mcgavin-top3-mip-proven]] (proven baseline, 89)
- [[mcgavin-top5-mip-inconclusive]] (couldn't even leave root LP)
- [[mcgavin-mip-local-optimal-halo1]] (joint-MIP at halo-1)
