---
name: crossing-oracle
description: "Vol-217 named invention: 3-row break-profile transfer over interior rows 10-12 conditioned on the prefix's ACTUAL placed frontier (exact N targets from placed row 9 — no free-N relaxation). PRE-REGISTERED GATE PASSED DECISIVELY: witness d146 pools floor 3/4 vs trio 7/8/8 (prediction 3-4 vs 7-11 hit exactly); witness softs +4 to +5.7 log10 above ours. First static instrument that sees the witnesses as special (band oracle scored witness A BELOW our 452). 0.8 s/prefix."
status: built
metadata:
  type: concept
---

# Crossing oracle (frontier-conditioned 3-row break profile)

**Origin**: vol-217 binding 1 — the instrument demanded by vol-216's
★★ witness-pool localization (the entire 452→460 gap lives in
wall-crossing rows ~10.5-12; all static instruments capped at ρ≈0.3
because they measured endgame-pool health, not crossing cost).

**Files**: `scripts/v217_crossing/crossing_oracle.py` (oracle +
exact brute-force selftest), `scripts/v217_crossing/attribution.py`
(realized-break region attribution),
`output/vol-217/crossing_oracle_20260612T095808/` (preregistration,
gate results, sweep scores).

## Definition

Transfer DP over interior rows 10-12, state $(e_{10}, e_{11}, e_{12},
b)$, processed cell-by-cell within columns (carried $s$-dimension for
vertical coupling; match/mismatch marginal contractions for
horizontal coupling — exact, verified vs brute force). Conditioning:

- **N targets of row 10 = exact south colors of placed row 9** (the
  frontier; this is the sharpening over [[band-oracle]]'s free-N).
- Placed cells in rows 10-12 (partial row 10 at d146) FORCED.
- Clue hints at interior (12,1), (12,12) pinned; S of row 12 free
  (row 13 unknown at prefix time — uniform); W/E rim from frame.
- All counted edges break-tolerant; counted set = exactly the 87
  "crossing" edges (V full-rows 10-11/11-12/12-13 + H full-rows
  11/12/13).
- Repeats-allowed incl. within-column (declared relaxation vs band
  oracle; sanity A/B pre-registered).

Scores: floor = bmin; soft = $\log_{10}\sum_b N_b\,\gamma^b$, γ=0.3.
Cost **0.8 s/prefix** (faster than the 2-row band oracle: forced
cells collapse the candidate sets).

## Realized-break anatomy (attribution.py, before the oracle ran)

On the crossing 87-edge set: witness A pays 7 of its 20 breaks,
witness B 8/20 — **all confined to interior 11→12 verticals + interior
row-12 horizontals; ZERO at N-of-row-10, rows 10-11 H, 10→11 V.**
Our 452 pays 14/28, our 451s 11/29 — spread from the frontier
downward (the 452 has 4 breaks on N-of-row-10 alone). Witnesses cross
rows 10-11.5 perfectly; we start bleeding at the frontier.

## Validation (vol-217, pre-registered gate)

Preregistration written 09:58 UTC before any score; results 10:0x:

| pool | crossing floor | soft (γ=0.3) | realized crossing |
|---|---|---|---|
| witness A (460) | **3** | **15.20** | 7 |
| witness B (460) | **4** | **14.87** | 8 |
| d146-seed63 (451) | 7 | 11.09 | 11-14 |
| d146-seed24 (446) | 8 | 10.67 | — |
| d146-seed36 (446) | 8 | 9.49 | — |

- **PRIMARY GATE PASS** (registered: both witness floors ≤ min trio
  floor − 2): 3,4 ≤ 5, margin 1-2 beyond the bar. Numeric prediction
  (witness 3-4, banked 7-11) hit exactly.
- **TERTIARY PASS**: witness softs above all trio softs by +3.8 to
  +5.7 log10 (an enormous margin for this family of scores — LP/band
  separations were ~1-3 units).
- Star check: seed63 still tops the trio on floor AND soft.
- prefix_breaks = 0 for all five pools (perfect-walk verification).

**Reading**: the witness frontiers ADMIT cheap crossings; ours don't.
Crossing cost is to first order a property of THE FRONTIER ROWS 8-10
PRESENT — measurable statically in 0.8 s, steerable during
construction (the premise of crossing-guided construction).

## Secondary gate (population, n≈75 homogeneous ≥300s)

(pending — sweep of all 257 banked prefixes in flight; protocol
identical to [[assignment-lp-prefix-scoring]]: depth-residualized
Spearman vs max/median finish; bar = beat LP's 0.335.)

## Open

- Population ρ + inter-instrument correlation vs LP/band (does the
  crossing oracle carry the latent factor the 0.644-correlated pair
  measures, or a second factor?).
- Re-rank the full 3,416-prefix bank; race top-k 300 s × 8
  (vol-217 binding 2).
- Crossing-guided construction (binding 3): optimize rows 8-10 FOR
  the frontier the oracle scores.
- 4-row variant (couple row 13) if floor sharpness needs it.

## Linked

[[band-oracle]], [[assignment-lp-prefix-scoring]],
[[midden-damage-geometry]], [[ladder-prefix-racing]], session
[[vol-217]]
