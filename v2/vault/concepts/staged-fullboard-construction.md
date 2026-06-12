---
name: staged-fullboard-construction
description: "Vol-217 (user-directed): frame-free staged construction of the REAL 16x16 — 4x16 bands, border EMERGES (top edge stage 1, flanks per band, bottom edge last), oracle asks between stages. Built end-to-end in one day: generator (vanilla_fast hint-protected), fb_oracle (counting + tropical), stage-3 builder (--init-board), stage4_finish (B&B). Measured: stage-2 floor-0 rate 16%; passage filter CAUSAL (zero overlap, clue-wall mechanism); pinned stage-3 subtrees EXHAUSTIBLE in seconds; blind entries finish at 44-52 breaks (best verified 436/480 5/5-hints); SOTA anatomy (469/470) = perfect 12-row block + 10-break band in rows 0-4."
status: built
metadata:
  type: concept
---

# Staged full-board construction (frame-free)

**Origin**: vol-217, user-directed mid-vol upgrade of the CROSSING
program: the staged 4-row solver runs on the real 16×16 with all 256
pieces — NO frame; the border ring emerges (top edge in stage 1, W/E
flanks per band, bottom edge chosen LAST against the surviving pool).
The frame objection and the staging merge: the crossing rim targets
become decision variables.

**Files**: `crates/bench-audit/src/bin/fb_oracle.rs` (+ Python
reference `scripts/v217_crossing/fb_oracle.py`),
`vanilla_fast` flags `--init-board/--init-rows` + hint-piece bucket
protection, `crates/bench-audit/src/bin/stage4_finish.rs`,
`scripts/v217_crossing/{run_census2.sh,stage3_bank.sh,
run_stage4_census.sh,census_driver.py,pick_strata.py,bucas_url.py,
attribution*.py}`.

## Architecture

```
stage 1+2 rows 0-7: blind fast DFS (free region), bank states
  ↓ ask: fb_oracle rows 8-10 (tropical filter → counting on tail)
stage 3 rows 8-11: pinned populations (--init-board), never first-found
  ↓ ask: rows 12-14 + bottom-chain  [REFUTED as finishability ranker]
  ↓ NEW ranker: greedy-finish labels (stage4_finish, 1.5 s, measured)
stage 4 rows 12-15: B&B min-break finisher, bottom border last
```

## Measured (vol-217, day one)

- Generator: 207M pp/s aggregate; 23,774 unique stage-2 states/20 min
  (all unique by (frontier, pool) key — diversity free).
- **Hint-piece poisoning** (user-question catch): without bucket
  exclusion, 94% of shallow states consume clue pieces off-hint —
  unfixably non-strict. Fixed (`reserved_pid`).
- Stage-2 rows-8-10 floors: **0: 16% | 1: 14% | 2: 38% | 3: 29%**;
  controls floor-0.
- **Passage filter CAUSAL** (pre-registered penetration, n=16): every
  floor≥1 state dies at exactly d135 = the center clue; floor-0
  passes (no overlap); soft predicts depth in-tier (182-195 vs
  136-159). Letter-of-prereg: partial (registered metric
  underpowered); substance unambiguous.
- **Pinned stage-3 subtrees EXHAUSTIBLE in seconds** (1 thread):
  compute is not the binding constraint on blind stage-3; 3,822
  floor-0 states → only 149 unique 12-perfect-row states.
- **Relaxation gap ≈ 38-45 breaks**: relaxed stage-4-entry floors 6-9
  vs measured finishes 44-52 (greedy labels n=149: min 44, med 52).
  Best verified finish: **436/480, 5/5 hints, fully from scratch,
  emergent border** (`output/vol-217/s4_finish_*/best_f6_open.json`).
- **SOTA anatomy** (corpus reconnaissance): McGavin 469 = 11 breaks
  ALL in rows 0-4; Blackwood 470 ×2 = 10 breaks ALL rows 1-4;
  crossing/band ZERO. SOTA = perfect ~12-row block + ~10-break
  4-row band, band built EARLY in construction order.

## Open / next

- **SOTA-mirrored generator** (presumptive vol-218 binding): ~10
  deliberate stage-1 breaks (rows 0-3, oracle/MIDDEN-placed) → demand
  perfect rows 4-15 (perfect-walk engines are our strength; shape
  feasibility proven by 469/470).
- Label-factory selection/learning: greedy-finish labels at scale
  (millions/night possible) — select on or learn from REALITY, not
  relaxations.
- Finisher upgrades: exact bottom-row DP (memoized), late-release
  gates, parallel B&B.

## Linked

[[crossing-oracle]], [[band-oracle]], [[midden-damage-geometry]],
[[isentrope-entropy-growth]], session [[vol-217]]
