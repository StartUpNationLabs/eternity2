---
name: ledger-color-deficit
description: "LEDGER (vol-214): admissible in-DFS color-accounting prune — per color, frontier demand F_c (rim targets on empty cells + placed sides facing empty cells) vs pool supply S_c (sides among available pieces); prune when spent + Σ max(0, F_c − S_c) > budget. First prune that sees pool starvation (the vol-209 distinctness wall) instead of reordering the walk."
status: partial
metadata:
  type: concept
---

# LEDGER — color-deficit accounting prune

**Origin**: vol-213 evening (2026-06-10), built during the vol-213 batch
window in response to the user's search-space-reduction prompt;
**measurement belongs to vol-214**. **Files**: `crates/cloister/src/dfs.rs`
(`struct Ledger`, `CellPlan.fwd`, `--ledger`).

## Definition

At any DFS state, every *decided-on-one-side* edge (a placed piece's
side facing an empty cell, or a rim target on an empty cell) must
eventually be matched by a pool side of the same color or paid as a
mismatch. With $F_c$ = open demands of color $c$ and $S_c$ = sides of
color $c$ among available pieces (hint pieces included — they deploy at
forced cells):

$$\text{future mismatches} \;\ge\; D := \sum_c \max(0,\, F_c - S_c)$$

since at most $S_c$ demands of color $c$ can ever be met. Prune when
$\text{spent} + D > B$. All updates are O(1) per side
(place/unplace = ~10 increments); $D$ is maintained incrementally.

**Semantics shift (intentional)**: the gate schedule bounds *walked*
breaks; LEDGER bounds walked + tail = TOTAL breaks. Running with
$B = 19$ makes the search exactly record-targeted ($480 - 19 = 461$).
Anytime sub-floor completions are forgone — that is the point.

## Why this is the theoretically aligned attack

[[isentrope-entropy-growth]] (vol-209): E2's hardness is global pool
distinctness, not local matching (interior marginals 95.5% uniform;
area-law $\rho(n) \approx e^{-0.085 n^2}$). Gates/scans/priors/replay
(vols 211-213) all reorder the same tree; nothing prunes it. LEDGER is
the cheapest sound relaxation of distinctness — color-multiset flow —
and it bites exactly in the starved-pool regime that creates the
bordered wall (153) and the row-12/13 damage pile.

## Planned measurement (vol-214 open)

- Perfect-prefix miner: budget 0, LEDGER on/off, 8 seeds × 60 s,
  bordered+hinted strict460a — wall-depth distribution vs the known 153
  median (witnesses prove 171 attainable).
- Record config: budget 19, witness gates, REPLAY+mcb2 — does LEDGER
  shrink the deviate-then-replay search enough to reach k=2 deviations?
- Overhead: nodes/s ratio ledger on/off at equal config.

## Companions (same package, logged in BACKLOG)

- **CAIRN** (frontier nogoods): same incremental structure with
  identity instead of counts — Zobrist over (available pieces ⊕ active
  frontier (cell, side, color)); TT of refuted (frontier, spent);
  sound-insert rule: only on clean candidate exhaustion (no restart
  truncation, no LDS block, no perturb), spent monotonicity gives
  reusability. Avail-mask implies depth, so gates/hint_after are keyed.
- **WEFT** (row DP lower bound): per-row admissible LB with
  color-count-relaxed pool, computed at row boundaries.

## Linked

[[replay-prior-over-cost]], [[cloister-ii-border-anchored]], [[vol-213]]
