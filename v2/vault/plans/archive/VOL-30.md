# VOL-30 — LearnedOnTies hybrid + the long-imitation experiment

**Opened**: 2026-05-13 (vol-29 close).
**Status**: drafted; awaits open.
**Gated on**: vol-29 PASS at the match condition. Imitation cannot beat
the teacher, but the v3 model produces equally-productive trajectories
with 35% fewer nodes — suggesting it picks better tie-breakers than
EdgeBpMarginals. The cheapest possible test of this is to use Learned
ONLY when LCV ties, leaving EdgeBpMarginals' confident picks alone.

## Why this volume exists

Vol-29 closed cleanly within the imitation ceiling: Δ=−1 vs
`joe_depth150_bp` at same wall-clock, with 35%/37% fewer
nodes/backtracks. The reduction at iso-depth is suggestive: the
model has learned something *informative* about which placements lead
to deep partials, but using it as the SOLE value-order doesn't beat
EdgeBpMarginals' targeted predictions. A hybrid that uses Learned only
when EdgeBpMarginals ties is the cheapest experiment that could
plausibly produce Δ > 0.

The user also requested a "long imitation" run for the sake of science.
Vol-30 includes that as T2 — a single overnight training run with a
bigger model + more data + more epochs to confirm empirically that
imitation does asymptote at the teacher.

## Audit-at-open

Items aged by vol-30 open (after vol-29):

- `multi-cell-bound-ascent` (8 vols, ALNS-axis). Deferred.
- `bound-floor-alns-with-per-step-check` (8 vols, ALNS-axis).
  Deferred.
- `diverse-457-search` (9 vols, partial). Deferred.
- `gap-recording-instrumentation` (8 vols). Deferred twice already;
  worth marking `wont-do` since "diagnostic-only with no record lever"
  has been the rationale every time.

Action at vol-30 open: read each, decide. Likely close
`gap-recording-instrumentation` as `wont-do`.

## Binding items

Two binding items max (CLAUDE.md discipline). Pick **T1 + T2** as
parallel tracks since neither depends on the other.

### T1 — LearnedOnTies hybrid (engine-side)

Add `ValueOrder::LearnedOnTies` variant: score candidates first by
EdgeBpMarginals; among the top-k tied (within some threshold ε), break
ties with the v3 Learned scorer. The engine change is small (~30 lines
in `learned_score_candidates`). Test under `joe_depth150_bp` with
60s budget.

**Gate condition** (set before running):
- Depth ≥ 165 (no regression from baseline).
- Wall-clock ≤ 1.5× baseline.
- AT LEAST ONE seed shows depth ≥ 166 (a productive tie-break that
  the deterministic EdgeBpMarginals wouldn't have made).

If passed: **first Δ > 0 lift from ML at canonical scale**.
If failed: imitation's signal isn't strong enough to break ties
productively. Close the ML direction for canonical 5-clue E2.

Honest cost: ~1 day.

### T2 — Long imitation (overnight)

Per user request "for the sake of science":
- Train a beefier model: hidden=128, color_emb=24, 30+ epochs.
- Capture more trajectories: 100 seeds × 60s = ~1.6 hr.
- Optionally: capture from BorderFirstRandom + BorderFirstMrv + Chess
  for diversity.

**Expected outcome**: asymptotes at Δ ≈ 0..−1 (the imitation
ceiling). This is **a confirmation experiment, not a record attempt**.
If it produces something surprising (Δ > 0), that's a vol-31 lead.

Honest cost: ~3-4 hr build + overnight train. Output is one number +
a writeup section.

## What this vol explicitly does NOT do

- ❌ RL self-play. The single direction that can structurally beat
  the imitation ceiling, but ~1 week build. Vol-31+ if T1 fails or if
  T1 succeeds and we want more lift.
- ❌ Variable-size canonical transfer (vol-28 already refuted this).
- ❌ Anything not on the ML axis (audit defers ALNS-axis items).

## Vol-close protocol

Standard:
1. Update T1+T2 status in BACKLOG.
2. Amend [[../concepts/learned-value-order]] with the new measurements.
3. Write `sessions/vol-30.md`.
4. Draft `VOL-31.md` based on results.
5. Memory entry if the result is gate-significant.

## Honest cost estimate

- T1 build + measure: 1 day.
- T2 build + capture + train + measure: 4-6 hr build + ~4 hr compute.
- Audit + writeup: 0.5 day.

**Total: 2-3 days.**

## Linked concepts

- [[../concepts/learned-value-order]] — full vol-26/27/28/29 history.

## Linked sessions

- [[../sessions/vol-29]] — direct predecessor (distribution-matched
  imitation matches teacher).
