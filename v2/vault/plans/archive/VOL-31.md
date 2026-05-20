# VOL-31 — does the LearnedOnTies depth lift translate to a score lift?

**Status (post-close)**: T1 PASS — +10 at weak pipeline, +8 at strong
pipeline. Vol-32 candidate `learned-on-ties-basin-escape` could break
the 457 record by combining LearnedOnTies-174 with vol-22's
basin-escape recipe.


**Opened**: 2026-05-13 (drafted at vol-30 close, before vol-30 T2
completes). Will be revised based on vol-30 T2 result.

**Gated on**: vol-30 T1 (+9 depth lift on canonical via LearnedOnTies).
That lift is on the CP cold-start axis (depth), not the score axis
(matched edges). Vol-23/24 measurements showed CP-deeper partials
don't always produce higher post-ALNS scores. Vol-31's job is to
measure this directly for the depth-174 partial.

## Why this volume exists

Vol-30 T1 demonstrated **the first Δ > 0 from ML at canonical scale**:
`joe_depth150_bp + LearnedOnTies` reaches depth 174 vs baseline 165
(+9, +8 at 5min) on canonical 5-clue E2. But our records are scored
in *matched edges*, not depth. Vol-31 closes the loop: take the
depth-174 partial, feed it to ALNS, measure final score.

Two possible outcomes:
1. **>457 score** → ML breaks the cold-start record. Vol-32+ scales up.
2. **≤457 score** → depth lift didn't translate; ALNS recovery
   saturates earlier than the depth gain. Useful negative; informs
   what the score-axis next-step needs.

Either way the measurement is cheap (~1 hr) and unambiguous.

## Audit-at-open

(Filled at vol-31 open. Likely defer ALNS-axis items again; vol-31 is
ML-axis follow-on.)

## Binding items

ONE only.

### T1 — Depth-174 partial → ALNS-fill → score measurement

1. Modify `canonical-eval` to dump the best_partial board to JSON when
   the run ends (max_depth_seen partial — already in `Sink.solved` /
   `TimedOut.best_partial`).
2. Use `joe_depth150_bp + LearnedOnTies` at 5-min budget on canonical
   E2 with seed=1; dump the depth-174 partial.
3. Feed it as Hints to existing ALNS / PT pipeline (`crates/localsearch`
   or `bench-audit` driver of choice). Use vol-22's basin-escape
   recipe or vol-22's prune-restart for the recovery.
4. Measure the final score after 5 min / 30 min ALNS.
5. Compare to vol-22's baseline: cold-start `joe_depth150_bp` (depth
   ~165) → ALNS → best 457/480 (our current record).

**Gate condition** (set before running):
- ALNS-fill from depth-174 partial reaches **score ≥ 458** → **first
  ML-driven score lift on canonical 5-clue E2**.
- Score ≥ 457 → matches existing record (no regression, depth lift
  doesn't help post-ALNS).
- Score < 457 → depth lift hurt the ALNS recovery (deeper CP partial
  pinned the wrong pieces).

Honest cost: ~1 day. Mostly engine plumbing to dump partial + driver
script.

## What this vol explicitly does NOT do

- ❌ Hyperparameter sweep of `LearnedOnTies` (separate BACKLOG entry,
  ~5 min compute, low priority since the +9 is already a clean signal).
- ❌ Variable-size architecture / RL self-play (vol-32+).
- ❌ Re-run T1 with different models (vol-30 T2 already does this).

## Vol-close protocol

Standard:
1. Update T1 status in BACKLOG.
2. Amend [[learned-value-order]] with the score-axis
   measurement.
3. Write `sessions/vol-31.md`.
4. Draft VOL-32 conditional on T1 result.
5. Memory entry if score record broken or ML direction closed on score
   axis.

## Linked concepts

- [[learned-value-order]] — vol-26..30 history.
- [[prune-restart]] — vol-23 ALNS-from-CP-partial baseline.
- [[score-optimizing-cp]] — vol-24's depth-vs-score split.

## Linked sessions

- [[vol-30]] (or vol-30-DRAFT.md until vol-30 close) —
  the +9 depth lift.
