---
name: j1-chain-hinted-band-12-failure
description: "J1-hinted: J1 chain with 5 canonical hints baked in as fixed_top/fixed_bot constraints. Reaches band 11 (208/256 placed) but fails at band 12 col 2 where hint piece 180 rot 1 at (13,2) is no-state-feasible under accumulated piece supply."
metadata:
  type: project
status: refuted
---

# J1-hinted — Band 12 failure

## Setup

`j1_chain_hinted` bin. Same J1 chain algorithm with FLH (consider=100),
but injects the 5 canonical hints as `fixed_top` (if hint at top_row)
or `fixed_bot` (if hint at bot_row) in each band.

5 canonical hints:
- pos 34 (r=2, c=2) piece=207 rot=1 → bands 1 (rows 1,2) bot or band 2 (rows 2,3) top.
- pos 45 (r=2, c=13) piece=254 rot=1 → bands 1 or 2.
- pos 135 (r=8, c=7) piece=138 rot=0 → bands 7 or 8.
- pos 210 (r=13, c=2) piece=180 rot=1 → bands 12 or 13.
- pos 221 (r=13, c=13) piece=248 rot=2 → bands 12 or 13.

## Result (beam=100k)

| Band | Score | Notes |
|---|---|---|
| 0 (rows 0,1) | 46/46 | perfect (top border) |
| 1 (rows 1,2) | 44/46 | 2 hints in bot row (cols 2, 13) |
| 2 (rows 2,3) | 46/46 | hints in top row already placed |
| 3-6 | 46/46 | perfect |
| 7 (rows 7,8) | 44/46 | 1 hint in bot row (col 7) |
| 8 (rows 8,9) | 46/46 | hint already in top |
| 9 (rows 9,10) | 46/46 | |
| 10 (rows 10,11) | 44/46 | -2 |
| 11 (rows 11,12) | 42/46 | -4 |
| 12 (rows 12,13) | FAILED | NO STATES at col 2 |

Band 12 hint at (13, 2) is piece 180 rot 1. Beam-search fails to find
ANY state at col 2 that:
- Has top_piece at row 12 col 2 matching col-1's required-right color
- Has bot_piece = piece 180 rot 1
- Top-bot vertical color match available

The hint piece 180 rot 1 has fixed left edge color (its rotated $L = e[1]$
in the original = $e[2]$ in rot 1). The piece in column 1's TOP row 12
position has a right edge that must match the top of column 2's row 12.
That top piece must satisfy:
- $L = $ col-1-row-12 piece's right
- Other constraints

The piece-supply at this point has 208 pieces used (208 of 256). 48
remaining. The hint requires a specific color profile, and apparently no
remaining piece + piece 180 rot 1 combination at col 2 satisfies the
state transition.

## Significance

This is the FIRST experiment that demonstrates **J1 with hint constraints
can still solve the upper 75% of the board**: 208/256 placed cells,
3/5 hints obeyed.

Score at point of failure: 373/480 matched edges across 208 cells. If we
could fill the remaining 48 cells with ANY ALNS or CSP and get the
remaining 2 hints (rows 13), we'd have a 5/5 hint board.

## Possible fixes

1. **Larger beam** — beam=200k or 500k might find the elusive col-2 state.
   Beam=300k timed out at band 0 (cost too high). Need targeted increase
   only for band 12 col 2.
2. **Alternative band 11/12 schedule** — different prior band selections
   leave a different piece supply.
3. **CSP-fill the bottom 2 rows** — pass the J1-hinted partial as Hints,
   then CSP-fill rows 13-15. The 2 row-13 hints at cols 2, 13 are
   constraints on CSP-fill, not on J1.
4. **Multi-start** — randomize beam tie-breaking to explore different
   J1 trajectories.

## Implication for goal

J1-hinted partial board at 208 cells with 3/5 hints obeyed is a NEW
seed for the existing CSP-fill + ALNS pipeline. The interesting
property: it has J1's mathematically-perfect structure for rows 0-7 and
hint compliance for the 3 hints in rows 2 and 8.

Next step: use this partial as a seed for vol-122 A1 pipeline
(`border_to_csp_fill` → ALNS basic 30min × multi-seed) and see if it
reaches ≥458 with 5/5 hints (strict-canonical record).

## Status

`built` — algorithm correct; one-band failure observed; pipeline-ready
partial saved.

## Linked

- [[j1-rust-beam100k-first-complete-board]]
- [[j1-forward-look-heuristic]]
- [[j1-loss-localization-math]]
