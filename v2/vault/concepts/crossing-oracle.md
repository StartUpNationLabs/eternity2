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

## Secondary gate (population, n=81 homogeneous ≥300s) — honest split

Same-set comparison (my homog filter keeps 81 rows vs vol-216's 75;
all instruments evaluated on the identical n=81):

| instrument | ρ(resid, max) | ρ(resid, MEDIAN) |
|---|---|---|
| LP (ub_total) | **+0.365** | +0.192 |
| band (soft) | +0.259 | +0.284 |
| crossing (soft) | +0.270 | **+0.381** |
| crossing (−floor) | +0.200 | +0.240 |

- **Registered bar (ρ_max > 0.335): FAIL** (0.270).
- **ρ vs MEDIAN = 0.381 — best median signal ever measured** (band
  0.297 in vol-216 / 0.284 here; LP 0.192). Combined crossing+band
  rank-sum: ρ(med) = 0.413.
- Inter-instrument residuals: crossing↔band only **0.220**
  (band↔LP = 0.627) — the crossing oracle carries a substantially
  NEW factor, not another copy of the endgame-pool latent.
- Star ranks #3/81 by crossing resid; top-quartile enrichment for
  max≥450: 1.6×.

Sanity A/B (pre-registered): band oracle with within-column
distinctness dropped — trio ordering preserved exactly (63>36>24
soft), floors shift ≤1 (7→6 for 63 only). Relaxation benign.

## ★ Floor census: the bank contains ZERO witness-grade frontiers

Across the 255 labeled banked prefixes: floors 6-11 (mode 9), exactly
ONE floor-6, none ≤5. Witnesses sit at 3-4 — **2-3 floor-breaks
outside the entire bank distribution**. This is the 452 ceiling,
mechanistically: the d14x perfect-walk probe stream produces
witness-grade crossings at rate <0.4%. Within-bank ρ is bounded by
class homogeneity (range 6-11) + label noise; the witness separation
is BETWEEN-class. ⇒ the oracle's value = selector for rare frontier
outliers + steering objective for construction, not a within-class
regressor. Bar for binding 2: floor ≤5 interesting, ≤4
witness-grade, ≤3 a 461-grade candidate (crude budget law: witnesses
realize floor+4 in-region).

d139 support (1,666 bank prefixes): missing cell (9,13) handled as a
marginalized pre-cell (N/W/E targets known; candidate souths +
own-edge costs ride along in b). d139 floors thus include up to 3
extra edges — comparable within-d139, offset vs d140+.

## ★ Full-board generalization (fb_oracle) + the row-11 decision point

`scripts/v217_crossing/fb_oracle.py` (same vol, user-directed
full-board pivot): N-row 16-wide bands, frame-free — flank/bottom
candidates from the REMAINING border pieces, border sides structural,
corners handled; exact selftest PASS. Validation produced the
sharpest finding of the day. Floors at the rows-0-10 frontier
(flanks free) vs after each board's own first 6 row-11 cells:

| board | frontier floor | after 6 row-11 commits |
|---|---|---|
| witnesses | **3** (soft 19.1) | **3 / 4** (preserved) |
| seed24 | **3** (witness-grade!) | 8 (destroyed, +5) |
| seed63 / our 452 | 6 (soft 15.5) | 7 (+1) |

**The crossing floor is decided at the row-11 entry cells.** seed24
HAD a witness-grade frontier and wrecked it in six placements;
witnesses preserved theirs; our best banked prefix never had one.
Decomposition: crossing quality = frontier quality × commitment
quality — BOTH measurable, the second steerable cell-by-cell.
⇒ (a) cheap shot: pin seed24 rows 0-10, rebuild row 11
oracle-ranked, race floor-≤4 results; (b) the staged builder's
stage-3 step must be oracle-steered exactly at the row-11 entry;
(c) per-candidate Δfloor needs ms-grade asks → Rust port (incremental
suffix recompute: per-candidate cost ~ms).

Cross-checks that fell out: T452 rows-0-10 EXACTLY equals seed63's
(it is a seed63-basin finish — piece-id identical); ★ **witnesses A
and B share 172/176 cells in rows 0-10** — the two community 460s
are SIBLINGS (one construction to row ~10, two endgames; different
rings below). Honest correction: our witness evidence is ~1
independent frontier, not 2.

## Scope refutation (vol-217 close): floors ≠ finishability

The relaxed floor is REAL for **passage** (penetration experiment:
floor-0 vs floor≥1 separates with zero overlap, causally — every
floor≥1 state dies at the center clue) and for witness-class
SEPARATION (the gate). It is REFUTED as a **finishability**
certificate at the endgame boundary: stage-4 entries with relaxed
floor 6 finish (measured, stage4_finish B&B) at 44+ breaks —
**relaxation gap ≈ 38-45** (repeats-allowed counting cannot see the
distinctness wall; [[isentrope-entropy-growth]] quantified at this
boundary). Successor instrument: **greedy-finish labels**
(stage4_finish, ~1.5 s, measured and distinctness-aware) for entry
ranking; the tropical floor stays as the cheap passage filter.

## Open

- fb-floor-attribution (argmin backtrace) — steering interpretability.
- fb-suffix-incremental — per-candidate Δfloor at ~ms.
- 4-row coupled ask in Rust (k=4) if entry asks return.

## Linked

[[band-oracle]], [[assignment-lp-prefix-scoring]],
[[midden-damage-geometry]], [[ladder-prefix-racing]], session
[[vol-217]]
