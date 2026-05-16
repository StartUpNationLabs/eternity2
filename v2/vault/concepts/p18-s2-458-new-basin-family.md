---
name: p18-s2-458-new-basin-family
description: "Vol-119 T1 discovered a NEW 458 basin (sweep_p18_s2_alns.json) from corner perm p18 (3,0,2,1) — exact REVERSAL of vol-32 458's (0,3,1,2). 3/5 hint compliance. Only 1.6% cell agreement with vol-32 458. Structurally distinct basin family. Demonstrates basin space includes mirror-symmetric corner perms not yet exploited."
metadata:
  type: project
---

# p18_s2 458 — NEW basin family (vol-119)

## Discovery

Vol-119 T1 sweep ran ALNS basic 5min on vol-60 corner-sweep partials.
One partial (p18, corner perm 3,0,2,1) with seed=2 reached 458/480 —
not previously documented as a record basin.

## Structural characterization

**Cell comparison with vol-32 458**:
- Only 4/256 cells match (1.6%).
- Borders: 0/56 match.
- Corners: 0/4 match (DIFFERENT CORNER PERMUTATIONS).
- Interior: 4/196 match.

**Corner permutations**:
- vol-32 458: (TL,TR,BL,BR) = (piece 0, piece 3, piece 1, piece 2)
  → corner perm (0,3,1,2)
- p18 458: (TL,TR,BL,BR) = (piece 3, piece 0, piece 2, piece 1)
  → corner perm (3,0,2,1) — **EXACT REVERSAL** (swap TL↔TR, BL↔BR)

**Hint compliance**: 3/5 (same family as vol-32 458, not strict-canonical).
Mismatched hints at pos 210 (piece 180 expected, found 150) and pos
221 (piece 248 expected, found 209).

## Significance

1. **First documented 458 basin at corner perm (3,0,2,1)**. Prior 458s
   were all at vol-32's (0,3,1,2) perm.
2. **Confirms corner-perm-basin coupling**: the 24 corner perms partition
   basin space into structurally disjoint regions. Vol-60 found 4
   tiers; this adds detail to the basin-tier mapping.
3. **Reachable in 5min winning5 ALNS** from vol-60's p18 corner-sweep
   partial — i.e., basin is not "isolated", just under-sampled.

## Implications for record-breaking

Adding p18_s2 458 to the corpus enlarges the cell-choice space at
~252 cells. Vol-119 T5 region MIP still locked 459 across this
enlarged corpus, but the analytical insight is: **corner-perm
diversity matters**. Future basin hunts should sweep across ALL 24
corner perms with good ALNS budgets, not just a handful.

## Verified

- `verify_board`: 256/256 placed, 458/480 matched, 3/5 hints, ILLEGAL
  (hint mismatch, not piece-uniqueness or border violation).
- `diff_boards vs vol-32 458`: 4/256 cells match — DISTINCT BOARDS.

## Linked

- [[corpus-restricted-region-mip-locked]]
- [[basin-mix-mip-refuted]]
- [[../sessions/vol-119]]
