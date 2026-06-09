---
name: watershed-frontier-flow
description: WATERSHED (vol-204) — diagnosed canonical E2 DFS deaths as 90% PIECE THEFT from brutal (N,W)-pair scarcity (33% of color-pairs have a UNIQUE serving piece). Global Hall/flow fires 0 levels early (deaths are local resource-misallocation, not global supply). Scarcity-aware value ordering gives +12 greedy single-descent but is backtrack-neutral. Crux = global assignment respecting edge-consistency.
status: partial
metadata:
  type: concept
---

# WATERSHED — frontier color-flow & piece-scarcity (vol-204)

**Origin**: vol-204 (2026-06-09). User-chosen direction from the vol-203
decision fork (after PARQUET bound capped + 2×2 patch-consistency too weak).
**Files**: `scripts/v204_watershed/` (diag_deaths, diag_flow, diag_death_cause,
scarcity_structure, scarcity_maxscore, scarcity_depth).

## What we set out to test
Whether a GLOBAL incremental check (Hall / max-flow on the frontier) prunes
canonical E2 DFS dead-ends EARLIER than edge-strict, attacking the depth ~150-210
wall where the vault's vanilla DFS plateaus.

## What we found (a connected chain of measurements)

### 1. Death location (diag_deaths)
Edge-strict row-major DFS deaths concentrate sharply at rows 8-11 (cells
128-191), peak row 9 (cells 144-159). Death depth p25=150 / median=157 / p75=163;
max depth 195 in 3M nodes. Confirms the vol-125 depth-150 phase transition at
cell granularity. The board fills ~7 rows "for free", then a wall.

### 2. Death CAUSE = piece theft (diag_death_cause) — the key finding
At a dead cell D (no available piece fits its determined (N,W) demand):
- # pieces that EVER fit D's (N,W): mean **1.98**, median 2, range 0-5.
- **90% of deaths = PIECE THEFT**: the 1-5 servers were ALL already used
  elsewhere (and ~long ago — only 0.27 placed in the last 16 steps).
- 10% = rare-color demand (zero servers ever — unavoidable shortage).

### 3. WHY global flow fails (diag_flow) — measured 0 levels early
Constrained-Hall over remaining pieces↔cells stays feasible at the death depth.
The branch is doomed by a *specific* scarce piece spent on a cell that had
alternatives — NOT a global supply deficit. So global flow/Hall lookahead is
USELESS here (0/120 deaths detectable earlier). In row-major, a future cell's
(N,W) demand isn't even determined until its above+left neighbors are placed, so
the theft is invisible at placement time.

### 4. The scarcity structure (scarcity_structure) — E2's combinatorial heart
For interior (N,W) color pairs: **121 of 362 pairs (33%) are served by exactly
ONE piece**; 81 by 2; 75 by 3. The (N,W) demand is brutally tight — most pairs
have ≤2 servers. This is *why* piece-theft is pervasive: placing the unique
server of a pair "wrong" dooms every future cell needing that pair. This is a
sharper statement of Selby-Riordan adversariality at the (N,W)-pair level.

### 5. Scarcity-aware value ordering (scarcity_maxscore, scarcity_depth)
- **Single greedy descent** (no backtracking): reserving scarce pieces
  (`rare_last`) gives mean matched **314** vs random **302** vs spend-scarce-first
  **288**. A real, directional **+12 / −26** effect — scarcity is an exploitable
  value-order signal.
- **Edge-strict DFS with backtracking**: max-depth is **backtrack-neutral**
  (~192 for all policies). Backtracking re-tries dead paths regardless of value
  order, so value order doesn't change the ceiling.

## Conclusion
The scarcity signal is REAL but its leverage is narrow: it improves single-shot
CONSTRUCTION quality, not exhaustive-search depth. Global flow lookahead does not
help (deaths are local misallocation). The crux E2 obstruction is now precisely
characterized: **pervasive (N,W)-pair scarcity → piece-theft, which is a GLOBAL
ASSIGNMENT constraint that (a) local value-ordering can't resolve, (b) edge-strict
backtracking can't exploit, (c) global Hall can't see early.** The right
formulation is a global assignment/flow that RESPECTS edge-consistency — the
strong-CP/MIP regime, intractable at 16×16 by exact methods.

## What this implies for a new algorithm (vol-205 candidate)
**Constraint-centric branching**: branch on the SCARCEST color-pair demand first
(place the forced unique-server pieces and propagate), i.e. most-constrained
*constraint* first, not cell-position order. Genuinely different from all E2
scan orders (row/border/spiral are all cell-position). Plus: scarcity ordering
belongs in any CONSTRUCTION-heavy stage (greedy seeds, beam value-ranking) where
the +12 applies — wire into the V155/beam ranker.

## Linked
- [[depth-40-wall-math]] — the wall this explains at cell level
- [[streamlining-for-e2]] — parent technique (this is a sound structural finding)
- [[parquet-overlapping-patch]] — bound side (capped)
- [[forbidden-patch-theorem-2026-05-19]] — 2×2 structure (separate scale)
- memory: `project_e2_v204_death_mechanism_2026_06_09`

## FORGE follow-up (vol-205 prototype, same session) — MRV is counterproductive

Tested constraint-centric branching (MRV = most-constrained empty cell first)
vs position order, greedy MaxScore (`scripts/v205_forge/forge_proto.py`,
`pos_value_order.py`):

| variable order / value order | mean matched (greedy) | max |
|---|---:|---:|
| position order + random value | 381.3 | 396 |
| **position order + reserve-scarce value** | **385.3** | **399** |
| position order + scarce-first value | 376.2 | 393 |
| MRV (most-constrained cell) + random | 371.5 | 381 |
| MRV + reserve-scarce (FORGE) | 376.2 | 387 |

**Findings:**
1. **MRV variable-order HURTS E2** (−7 to −10 vs position order). Fail-first CSP
   wisdom backfires: filling tightest cells first fragments the board into many
   partial regions, multiplying interface constraints. Clean-frontier
   (position / border-first) orders win — consistent with the vault's path-order
   findings. **Constraint-centric branching is REFUTED for greedy E2.**
2. **Scarcity value-order helps modestly** (+4 mean / +3 max under position
   order; directional vs scarce-first −5). Real but small, and backtrack-neutral.

**Net conclusion of WATERSHED/FORGE (vol-204/205):** the (N,W)-scarcity structure
is real and now well-characterized as E2's combinatorial heart, but the
algorithmic levers it suggests (MRV branching, scarcity value-ordering) give only
modest single-shot construction gains that do NOT lift the search ceiling. Piece-
theft is a GLOBAL assignment constraint that greedy/local ordering cannot resolve.
The only thing that could exploit it is a global exact method respecting
edge-consistency at scale (intractable by current exact methods at 16×16) OR a
Lagrangian/assignment relaxation used as a SCARCITY-AWARE constructive seed
generator (vol-22 bound-ascent reframed constructively — open, not yet tried).
