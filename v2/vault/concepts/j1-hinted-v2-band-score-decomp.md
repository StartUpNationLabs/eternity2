---
name: j1-hinted-v2-band-score-decomp
description: "J1-hinted v2 band-by-band score decomposition on canonical E2: hint constraints + downstream piece reservation cost (J1-FLH 447 → J1-hinted v2 414, Δ = -33). Band-13 hint is the largest single drag."
metadata:
  type: project
status: built
---

# J1-hinted v2 — band score decomposition

## Setup

Same J1 chain (Rust, beam=100k, FLH=100) as J1-FLH, but with the 5
canonical hints locked at their (position, piece, rotation) AND with
downstream hint pieces reserved in `initial_used` upstream.

## Per-band scores (canonical 16×16)

| Band | Hint row? | J1-hinted v2 | J1-FLH (no hints) | Δ |
|---|---|---|---|---|
| 0 (rows 0,1) | - | 46 | 46 | 0 |
| 1 (rows 1,2) | r2 (cols 2, 13) | **43** | 46 | -3 |
| 2 (rows 2,3) | - | 46 | 46 | 0 |
| 3 (rows 3,4) | - | 46 | 46 | 0 |
| 4 (rows 4,5) | - | 46 | 46 | 0 |
| 5 (rows 5,6) | - | 46 | 46 | 0 |
| 6 (rows 6,7) | - | 45 | 46 | -1 |
| 7 (rows 7,8) | r8 (col 7) | 45 | 46 | -1 |
| 8 (rows 8,9) | - | 45 | 46 | -1 |
| 9 (rows 9,10) | - | 45 | 46 | -1 |
| 10 (rows 10,11) | - | 43 | 45 | -2 |
| 11 (rows 11,12) | - | 42 | 45 | -3 |
| 12 (rows 12,13) | r13 (cols 2, 13) | **36** | 43 | -7 |
| 13 (rows 13,14) | - | 35 | 42 | -7 |
| 14 (rows 14,15) | - | FAIL | 38 | -38 |

Sum (J1-hinted v2 bands 0-13): 609. J1-FLH bands 0-14: 654.

J1-FLH matched-edges 447, J1-hinted v2 matched-edges 414 = Δ -33.
Loss explanation:
- Band 1: -3 (hint at row 2 forces 2 non-optimal piece assignments)
- Band 6-9: -1 each = -4
- Band 10: -2
- Band 11: -3
- Band 12: -7 (hint at row 13 forces 2 non-optimal assignments + the
  downstream piece reservation has cascaded constraint mass into here)
- Band 13: -7
- Band 14: failed (row 15 empty, board has 240 cells, missing 16)

**Total accounted loss: 27 from bands + 16 missing cells (row 15) =
33 (matches 447 - 414).** Wait that's not right — 447 is FLH FULL board,
414 is v2 PARTIAL board. Let me reconcile.

Actually:
- J1-FLH full: 447 matched on 256 cells.
- J1-hinted v2: 414 matched on 240 cells.
- Per-cell density: 447/256 = 1.746 edges/cell; 414/240 = 1.725 edges/cell.

Slightly worse per-cell. The dominant loss is the 16 missing cells
(row 15), each potentially contributing 2 horizontal edges + 1 vertical
edge ≈ 30 edges if all were perfect. Plus band-internal degradation
~6 edges.

## Where is row 15 stuck?

Band 14 col 15 failed: "NO STATES". Let's analyze:
- At band 14 col 14, the col-13 prev state had its (top.R, bot.R) =
  required (top.L, bot.L) for col 14.
- Col 14 has the col-14-top constraint AND piece 248 is at pos 221
  (r=13, c=13) which is NOT in this band (band 14 = rows 14, 15) —
  but wait, row 13 was already fully placed in band 13.

The hint reservation at this point: all 5 hints are placed in rows
2, 8, 13. Row 14 has no hint. Row 15 has no hint. So band 14 has no
hint constraints. The failure is from PIECE SUPPLY EXHAUSTION:
240 placed, 16 pieces left for row 14 = the row was placed but row 15
is stuck.

Wait — the algorithm uses 2-row bands. So band 14 = (row 14, row 15).
Both rows are FILLED in band 14 if it succeeds. The failure must be
at col 15 = state-transition infeasible.

## Implications

1. The hint constraints cost ~6 in-band edges total across the affected
   bands (1, 7, 12 = 3 hint-bands).
2. The 16 missing cells of row 15 represent the lion's share of loss.
3. ALNS basic on this 240-cell partial should be able to fill row 15
   (CSP-fill or random-fill + ALNS). Expected lift: ~30-40 edges from
   the missing-cell fill, plus 5-10 from ALNS smoothing of bands 10-13.
4. Target after ALNS: 414 + 30 = **~444**. Slightly above J1-FLH's 447
   would be 447-450. Need ALNS to do better than the open-row fill.

## Comparison to J1-FLH+ALNS

J1-FLH 447 + ALNS basic 30min s=42: **450** (+3).
J1-hinted v2 414-PARTIAL + ALNS basic 30min s=?: TBD.

If ALNS lifts to ≥458, **NEW strict-canonical record**.
If ALNS lifts to ≥460, **NEW matched-edges record** (since 5/5 ≥ 4/5).

## Linked

- [[j1-chain-hinted-v2-fix]]
- [[j1-loss-localization-math]]
- [[j1-forward-look-heuristic]]
- [[j1-rust-beam100k-first-complete-board]]
