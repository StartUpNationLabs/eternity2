---
name: canonical-hint-cost-2-edges
description: "Vol-121 observation — the canonical 5-clue hint constraint costs ~2 edges on our basins. The matched-edges 459 record gives up 1 hint (pos 210) to enable a better local configuration. The strict-canonical 457 record keeps all 5 hints. McGavin 469 keeps only 1/5 hints. Implication: the 5/5-hint search space is structurally MORE constrained than the matched-edges search space."
metadata:
  type: project
---

# Canonical hint cost ≈ 2 edges (vol-121)

## Observation

Comparing our records:

| Record | Score | Hints obeyed | Notes |
|--------|------:|:------------:|-------|
| strict-canonical 457 | 457 | 5/5 | LEGAL_COMPLETE per vol-32 blackwood_mrv |
| matched-edges 459 (vol-60) | 459 | 4/5 | gives up pos 210 (piece 247 rot 2 instead of piece 180 rot 1) |
| matched-edges 458 (vol-32) | 458 | 3/5 | gives up pos 210 and pos 221 |
| 1-clue 460 (bseed9 vol-110) | 460 | 0/5 | gives up all 5 hints |
| McGavin 469 | 469 | 1/5 | keeps only the center hint |

**The "hint cost" pattern**: each hint position obeyed costs roughly 1
edge of slack. The 459→457 transition (gain back pos 210 hint) costs
2 edges. The McGavin 469→hypothetical-canonical-5/5 would be even
costlier.

## Why hints constrain so heavily

Piece 180 at pos 210 has edges (top=9, right=21, bottom=12, left=20).
The 4 colors must match neighbors at pos 194, pos 209, pos 226, pos
211. These constraints propagate.

When pos 210 is free, ALNS can place piece 247 rot 2 (rotated
edges (17, 16, 15, 16)) which matches a different neighborhood
configuration. The freedom changes WHICH neighbors are valid and
shifts the entire basin's piece-set.

## Implication

The strict-canonical 5/5-hint problem is a STRICT SUBSET of the
matched-edges problem. Records that hold for matched-edges (459) may
not transfer to strict-canonical.

This is why:
- McGavin's algorithm reaches 469 on 1-clue but only 396 on
  canonical 5-clue (vol-118 pipeline_corner_perm_specificity).
- Our pipeline reaches 459 matched-edges but only 457
  strict-canonical.
- The "hint cost" is real and quantifiable.

## Hint-neighbor budget analysis (vol-121 follow-up)

For each of the 5 hint positions × 4 edges = 20 hint-edges, computed
the count of puzzle pieces that could match by color on the relevant
side (any rotation), excluding the 5 hint pieces themselves:

| Hint pos | T budget | R budget | B budget | L budget |
|---------:|---------:|---------:|---------:|---------:|
| 34       |       44 |       42 |       42 |       45 |
| 45       |       44 |       46 |       44 |       46 |
| 135      |       42 |       42 |       42 |       42 |
| 210      |       46 |       42 |       43 |       42 |
| 221      |       45 |       43 |       44 |       46 |

**All hint edges have 42-46 candidate neighbors.** NOT particularly
constrained — the hint colors are mid-frequency (50 of each across
the puzzle), and removing 5 hint pieces leaves 42-48 valid candidates
per side per color.

**So why does the hint cost 2 edges?** Not because of supply scarcity
at the hint-edge level. It must come from:
1. **Joint piece-placement infeasibility**: the SPECIFIC combination of
   42-piece options at all 20 hint-edges simultaneously doesn't admit
   a 459+ board layout WITHIN ALNS/CSP reach.
2. **Basin asymmetry**: the canonical hint piece-rotations point
   the basin toward a low-ALNS-ceiling region. ALNS exploring from
   the hint constraints can't escape past 457 — while ALNS freed of
   hints reaches 459.

## Open question

Is the hint cost a fixed 2 edges, or does it scale with basin? If a
SPECIAL basin existed where the canonical hints aligned with optimal
edge structure, the strict-canonical score could LEAP toward 460+
without losing hints. Such a basin would be the canonical 5-clue
record-breaker.

The 24 corner perms × specific border configurations form the
basin-tier structure. McGavin's basin (corner perm 3,2,0,1) reaches
469 on 1-clue; its canonical-projection (vol-44) drops to 477 LP-UB,
and our ALNS lifts only to 443/396. The McGavin basin is NOT
hint-friendly.

The basin-discovery deficit (vol-120) may include the question: **is
there a hint-friendly basin we haven't found?**

## Linked

- [[corpus-restricted-region-mip-locked]]
- [[pipeline-corner-perm-specificity]]
- [[../sessions/vol-121]]
