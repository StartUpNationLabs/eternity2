---
name: j1-fragment-anchor-design
description: "J1-fragment-anchor: instead of strict top-down chain, solve the 3 hint-containing bands first (bands 1, 7, 12) as independent column-DP fragments, then connect them via top/middle/bottom J1 sub-chains. Addresses the cascade penalty observed in J1-hinted v2."
metadata:
  type: project
---

# J1-fragment-anchor (design only)

## Motivation

[[j1-hinted-v2-band-score-decomp]] showed the J1-hinted v2 loss is
*cumulative*: bands 6-13 each drop 1-7 points because the upstream
pieces consumed in band 0 (with hint reservation already applied) leave
a worse pool for downstream bands. The cascade is the issue.

## Idea

The 5 canonical hints lie at rows 2, 8, 13. They divide the board
into 4 strata:
- **Stratum A**: rows 0-1 (above row-2 hints)
- **Stratum B**: rows 3-7 (between row-2 hints and row-8 hint)
- **Stratum C**: rows 9-12 (between row-8 hint and row-13 hints)
- **Stratum D**: rows 14-15 (below row-13 hints)

The 3 "hint-bands":
- Band 1 (rows 1, 2) — contains row-2 hints.
- Band 7 (rows 7, 8) — contains row-8 hint.
- Band 12 (rows 12, 13) — contains row-13 hints.

## Algorithm

1. **Solve hint-band 1** independently: 16-col DP, top row free, bot row
   constrained by 2 hints at (2,2) and (2,13). Use ALL 256 pieces.
   Result: best row-1 and row-2 piece assignment maximizing band 1 score.

2. **Solve hint-band 7** independently: 16-col DP with top free, bot
   constrained by 1 hint at (8,7). Use the 256 - (pieces from band 1)
   pool. Save the result for several seeds.

3. **Solve hint-band 12** similarly with 2 hints at (13,2) and (13,13).

4. **Now connect fragments via sub-chains.**
   - **Top sub-chain** (rows 0, 1): band 0 with row 1 from step 1 as
     bot constraint. Pieces left = 256 - bands 1 - bands 7 - band 12.
   - **Mid sub-chain B** (rows 3..7): start with row 2 (= band-1 bot)
     as top constraint; end at row 7 (= band-7 top) as bot constraint.
     This is a 5-row interpolation: rows 3, 4, 5, 6, 7 ← 5 bands.
   - **Mid sub-chain C** (rows 9..12): start with row 8 (= band-7 bot)
     as top; end with row 12 (= band-12 top) as bot. 4 bands.
   - **Bottom sub-chain** (rows 14, 15): row 13 = band-12 bot is top
     constraint; row 15 has border constraint.

5. The connection has TWO color-vector constraints at each fragment
   boundary: a top color-vector AND a bottom color-vector. This is
   STRICTLY HARDER than top-only J1. But the pieces available may be
   more abundant than in the cascade case.

## Combinatorial reasoning

J1-hinted v2 cascade has the fundamental problem that early bands
"forget" they constrained the lower bands. Fragment-anchor pins the
hint rows upfront, so the algorithm KNOWS at all times which pieces
are needed where.

This is similar to McGavin's break-index algorithm: enumerate the hard
parts first, then complete. Difference: McGavin's "hard parts" are
runs of similar colors; ours are hint-anchored bands.

## Cost estimate

- 3 hint-band solves: O(beam × 16) each = ~10^7 ops, ~1 min total in Rust.
- 4 sub-chain solves: 5+4+1+1 = 11 bands, each O(beam × 16) = ~50 min
  for beam=100k. **Total: 1 hour**.

## Expected gain

- Bands 1, 7, 12: each solved with FULL 256-piece pool (initially).
  Score per band likely 44-46 vs current 36-45.
- Sub-chains: 5+4+2 = 11 bands. Each has TWO color vectors constraining
  the DP. Likely score = 40-44 each.
- Total board edges: ~ band-perfect (46 × 3 hint-bands = 138) + 44 ×
  11 sub-chain bands = 138 + 484 = 622 sum of band-scores
  → ~622 - 14*15 = 412 matched edges.

Hmm, theoretical estimate is about the same as J1-hinted v2 (414).

## Honest scoping

Fragment-anchor's gain comes from saving the "wrong-piece-too-early"
errors. But the **sub-chains have stronger constraints** (two color
vectors). Net is unclear without implementation.

**Pre-estimate: 5-10 point improvement over J1-hinted v2** (414 → 420ish).
Probably NOT enough to beat the standing 459 record. But:
1. Tighter ablation: tells us if the hint-cascade is the dominant cost.
2. Better seed for ALNS.

## Status

`design-complete-not-yet-built`. Implementation deferred while ALNS jobs
run. Worth doing if v2-ALNS fails to beat 458.

## Linked

- [[j1-chain-hinted-v2-fix]]
- [[j1-hinted-v2-band-score-decomp]]
- [[j1-loss-localization-math]]
