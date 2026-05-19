# CONCRETION — Rigid-Molecule Preprocessor

**Status**: `refuted` (Vol-127, 2026-05-19)
**Origin**: Brainstorm reservoir round-3
[[plans/EXTERNAL_BRAINSTORM_2026-05-18]]
**Files**:
- `scripts/v127_concretion_inventory.py` — color inventory
- `scripts/v127_concretion_rare_pairings.py` — rare-color pair analysis
- `scripts/v127_border_hamilton.py` — border-ring out-degree analysis
- `scripts/v127_border_2step_lookahead.py` — 2/3-step lookahead

## Definition

**Idea**: count colors first, board search second. For each rare color
$C$ with $k_C$ piece-side occurrences, in any solution the
$k_C / 2$ matched-adjacency pairings of color $C$ force certain
piece-pair neighbour relationships. Chain these forcings to fixed
point; each chain of forced pairs becomes a "rigid molecule".
Iterate to fixed point. The quotient instance has fewer free pieces.

## E2 measurements (V127)

**Step 1 — color inventory** (V127-T1):
- 22 interior colors: 5 rare ($k=24$), 5 medium ($k=48$), 12 common ($k=50$).
- 60 border pieces (4 corners + 56 edges); 196 interior pieces.
- **All 120 rare-color slots are on border pieces only.**
  Interior pieces have 0 rare sides.

**Step 2 — per-color piece-side counts** (V127-T2):
- Each rare color appears on E and W sides almost exclusively:
  $c{=}1$: E=10, S=2, W=12; $c{=}2$: E=11, S=1, W=12; etc.
- All 60 rare-side pieces have exactly 2 rare sides.
- 2-15 pieces have a rare color on multiple sides (per-color); these
  are the marginal "constraint hubs" but they don't dominate.

**Step 3 — border-ring out-degree** (V127-T3):
- Each edge piece $p$ has exactly 1 canonical-orientation rotation
  $(N{=}0)$.
- Successor relation $p \to q$ (in the top row, $p$'s E-color matches
  $q$'s W-color): 613 directed pairs across 56 edge pieces.
- **Out-degree distribution: 9 (4 pieces), 10 (12), 11 (23), 12 (17)**.
- **In-degree distribution: 9 (2), 10 (16), 11 (21), 12 (17)**.
- **No piece has out-degree 1 or in-degree 1.** No forced single-step
  pairings on the border ring.

**Step 4 — 2- and 3-step lookahead** (V127-T4):
- 2-step extensions per starting piece: minimum 93, median ~118,
  maximum 135.
- 3-step extensions: ~1300-1400.
- Naive 14-step top-row path count: $\approx 10.96^{14} \approx
  3.6 \times 10^{14}$.

## Conclusion

**CONCRETION is REFUTED on canonical Selby-Riordan E2 at the simple
forced-pair level.** Forced molecules of size $\ge 2$ do not exist
under per-pair or per-triple constraints. The piece set is too
uniformly branchy: every piece can plausibly pair with 9-12 others.

The Selby-Riordan generator is **maximally CONCRETION-resistant** by
construction: it avoids forced moves precisely so that no
constraint-propagation preprocessor can collapse the search space.

## What's still open

A *softer* CONCRETION might exist:
- Filter pairings through canonical 5-hint compliance: pin the 5
  canonical pieces in their hint positions, then re-compute
  out-degrees with these pins enforced.
- Score pairings by "soft forcing" — pairs that survive consistency
  propagation through 4-5 steps may be near-forced, even if not
  uniquely forced.

These are higher-effort. **For canonical E2 the simple CONCRETION
yields no wins.**

## Refutation evidence

- 4 separate scripts measure the same outcome from different angles.
- All branching factors are in [9, 12]. No outlier with branching 1
  or 2.
- 3-step extensions ~1300 → CONCRETION cannot localize even within
  4-piece chains.
- Naive 14-step count $\sim 10^{14}$ confirms top-row alone is a
  hard combinatorial object before any interior consideration.

## Vol-127 close

Per [[feedback_e2_one_invention_per_volume]]: vol-127 is CONCRETION-
only. Status set to `refuted`. Vol-128 opens for the next invention
(ATLAS — pattern database — per brainstorm priority).

## Linked

- [[plans/EXTERNAL_BRAINSTORM_2026-05-18]]
- [[concord-difference-map]]
- [[fpl-frozen-pair-lifting]]
- [[sessions/vol-127]]
- [[rare-color-geography]] (vol-13 — first hint that this would be hard)
