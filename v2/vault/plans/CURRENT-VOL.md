# Current Volume — Vol-214 — LADDER (prefix racing)

**Opened at vol-213 close (2026-06-10 night). Strict bar: 461 original
board (5/5 hints).**

## Context from vol-213 (all measured)

The unguided 444-450 band is UNIVERSAL across 55 frames; the witnesses
are 1-deviation-locked across [60:182); double-break is REPLAY-only;
LEDGER/CAIRN are overhead-dominated as in-search depth tools at 60 s;
choke auto-gates move walls (+34 depth) and the hinted wall is 139.
⇒ 461 paths: (a) much deeper unguided prefixes, (b) k≥2-deviation
witness enumeration, (c) new witness-class sources. Vol-214 attacks (a)
with the strongest unplayed cards.

## Binding items (≤3)

1. **LADDER — successive-halving prefix racing** (user idea + Verhaard
   + LEDGER-as-score; the vol-214 invention):
   - Progress-based early aborts (kill epochs below the choke-derived
     depth-vs-nodes envelope; Verhaard claims ~5× over fixed restarts).
   - Hundreds of 5 s probes → bank deepest prefixes with their LEDGER
     deficits → promote top-k DIVERSE prefixes (piece-overlap dedup;
     score = depth − λ·deficit) → 30 s from-prefix restarts
     (`--init-prefix`: pin first K scan cells as forced) → top few at
     300 s+ with et14/choke gates.
   - Metrics: hinted wall distribution vs 139/153; unguided strict
     totals vs the 444-450 band; ≥8 seeds min/med/max at every rung.
2. **Verhaard piece-class quotas**: tilability partition (2×3-box
   completion counts; set-SA groups) + per-depth usage constraints
   (consume bad pieces early). A/B on the v1 recipe and inside LADDER
   rungs. If it moves the band, compose with item 1.
3. **Discipline**: ≥8 seeds min/med/max; verify+rescore ≥458; UTC
   timestamps + history CSV; honest negatives same-day; hinted runs
   NEVER use the default gate spread (choke-derive or ≤120 explicit).

## Audit-at-open notes

- `prefix-vault` (since vol-212) is ABSORBED into item 1.
- `verhaard-markov-schedule-optimizer` stays backlogged (item 2 takes
  the cheaper quota idea first; the optimizer is the follow-up if
  quotas show signal).
- `weft-row-lb` stays deferred (LEDGER/CAIRN miner nulls lower its
  prior further).
- `triple-break-census`, `perturb-multi-deviation`, `silent-cap-audit`
  remain open; `unguided-mcb2-ab` → CLOSED (null, both lanes).

## Linked

[[replay-prior-over-cost]], [[ledger-color-deficit]],
[[framegen-chain-feasibility]], [[cloister-ii-border-anchored]],
session [[vol-213]]
