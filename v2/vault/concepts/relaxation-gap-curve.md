---
name: relaxation-gap-curve
description: "Vol-218 M1 (pre-registered, 10×10 testbed, 160 real perfect-prefix frontiers, exact ground truth, zero caps): the repeats-allowed transfer count vs the exact distinct-piece count, by band depth and budget. Median overcount ×6-8 at ONE row, ×10^3-10^4 at two rows, infinite (100% phantom) at three. P(exact=0 | relax>0) at b=0: 49% / 100% / 100% / 100% by depth. The microscopic mechanism behind every 'floors lie at the endgame' result (vol-217 gap 38-45; vol-209 area-law)."
status: built
metadata:
  type: concept
---

# The relaxation-gap curve (repeats-allowed vs distinct, by depth)

**Origin**: vol-218 prereg M1 (binding 2, user-directed 10×10 rigor).
**Files**: `mini_lab --mode m1`; data
`output/vol-218/m_run_20260612T140054/m1_*.tsv`; prereg
`plans/archive/vol-218-prereg-bandsaw-10x10.md`.

## Setup

8 instances (`build_puzzle(10, 8, seeds 101-108)`, 5 E2-analog
hints), 20 blind perfect-rows-0-5 entries each (registered
selection-free protocol). Per entry and band depth k = 1..4 (rows
6..5+k), budgets b = 0..3: `N_relax` (repeats-allowed transfer
count, brute-force-selftested) vs `N_exact` (distinct-piece DFS
count, brute-force-selftested). 2,560 measurements, zero node caps.

## The curve (final, all 160 entries)

| k | P(exact=0 \| relax>0) @b=0 | @b=3 | median log10 gap (both>0) |
|---|---|---|---|
| 1 row | 49.2% | 0% | 0.78–0.90 (×6–8) |
| 2 rows | 100% | 81.8% | 3.95 @b3 (×~10⁴) |
| 3 rows | 100% | 100% | ∞ (no exact filling ≤ 3 anywhere) |
| 4 rows | — (relax floors > 3) | 100% | ∞ |

- **P1.1 (registered) CONFIRMED**: the gap grows strictly with depth
  in the measurable range and saturates to ∞ by 3 rows.
- **P1.2 CONFIRMED in conditional form** (registered joint form is
  non-monotone at k=4 only because the relax floor itself exceeds
  the budget grid there; both reported).

## Reading

1. Even ONE free row over a 40-piece pool overcounts ×7 — repeats
   relaxations are not "approximately right with a correction
   factor"; the factor is exponential in depth.
2. "Relax says ≥1 filling exists" is WRONG half the time at one row
   and essentially always at ≥2 rows: phantom feasibility is the
   default, not the exception. Any selection/pruning instrument
   built on repeats-allowed positivity is structurally unsound at
   band depth ≥ 2 (this is the microscopic content of vol-217's
   floors-lie refutation and the vol-209 area-law).
3. Floors (min-cost) survive as PASSAGE bounds (admissible LBs,
   load-bearing in [[bandsaw-band-split-exact]]'s suffix prune);
   counts and feasibility certificates do not survive at all.

## Transfers / does-not-transfer

Transfers: the SHAPE (exponential-in-depth gap; phantom saturation),
instrument ordering implications. Does NOT transfer: absolute
constants (10×10/8c: 22.5 edges/color; E2: 28.2; vol-35 lesson).
The 16×16 anchor point that does exist: vol-217's measured gap 38-45
breaks at the stage-4 boundary; vol-218's real-board bracket [11,52]
([[bandsaw-band-split-exact]]).

## Linked

[[bandsaw-band-split-exact]], [[crossing-oracle]],
[[fugacity-corrected-counts]], [[isentrope-entropy-growth]],
session [[vol-218]]
