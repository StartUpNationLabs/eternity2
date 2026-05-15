# McGavin N-row pinning scaling — vol-68 (2026-05-15)

**Status**: `built` (empirical) — vol-68.
**Result**: SHARP threshold at N=14 rows.

## Experiment

Pin McGavin's top N rows (16N pieces) and run our alns_only with
winning5 ops for 60s seed=1. Record final score.

| N rows pinned | pieces | score | gap to 469 |
|---|---|---|---|
| 1 | 16 | 400 | -69 |
| 2 | 32 | 382 | -87 |
| 4 | 64 | 401 | -68 |
| 8 | 128 | 418 | -51 |
| 12 | 192 | 450 | -19 |
| 13 | 208 | 455 | -14 |
| 14 | 224 | **469** ★ | 0 |
| 15 | 240 | 469 | 0 |

## Sharp threshold

Score jumps from 455 at N=13 to 469 at N=14. **The last 2 rows
are uniquely determined by the top 14 rows under our ALNS**, but
the last 3 rows have an ALTERNATE 455-completion basin that traps
ALNS at N=13.

At N=13, ALNS finds a 31-cell-diff completion using McGavin's same
pieces but swapped within rows 13-15. Local color matching admits
multiple completions; ALNS picks the wrong one.

At N=14, only row 15 (16 pieces) is free. The constraints from
above force the unique 469 completion.

## What this proves

1. **Our ALNS pipeline IS capable of reaching 469** — given enough
   pinned structure. No fundamental algorithmic incompleteness.
2. The bottleneck is **finding the first 224 pieces of McGavin's
   structure**. Top-row pinning alone (16 pieces) is far too thin.
3. **There's an alternate "455 basin" reachable from 13 of McGavin's
   rows**. This basin doesn't extend to 469. ALNS can't tell which
   completion to pick at N=13.

## What this means for vol-66+ algorithms

To break 459, our algorithm must construct ~224 of McGavin's pieces
without his algorithm's help. The 47-component basin landscape
shows our pipeline samples ~47 of >10⁹ valid top-rows. Reaching
McGavin's top-14-rows specifically is exponentially unlikely under
our heuristics.

**Open question**: is there a SHORTER pin-list (e.g., specific cells
spread across the board) that uniquely determines McGavin's
completion? If 100 well-chosen cells force the rest, that's a
"skeleton" of McGavin's structure.

## Linked

- [[top-row-determines-basin]] (parent — refuted strong hypothesis)
- [[basin-component-landscape]]
- [[../sessions/vol-68]]
