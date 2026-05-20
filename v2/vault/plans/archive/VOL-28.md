# VOL-28 — Variable-size learned value-order toward canonical 16×16

**Opened**: 2026-05-13 (vol-27 close).
**Status**: drafted; awaits open.
**Gated on**: vol-27 PASS. Imitation policy + in-process ONNX inference
beats MRV+LCV by 5.5× wall-clock at 6×6/5c. The direction is alive at
small scale. Now we test whether it transfers up.

## Why this volume exists

Vol-26 + vol-27 together shipped:
- Working synthetic E2-family puzzle pipeline (Rust gen → JSONL → Python
  training → ONNX export).
- `ValueOrder::Learned` with in-process ORT inference.
- Gate PASS at 6×6/5c under 100ms budget: 16/16 recovery of MRV failures,
  540× algorithmic node reduction, 5.5× median wall-clock win.

The current model is grid-size-specific because `GridConv` registers a
fixed neighbour-index buffer at construction. Canonical 16×16 needs
either:
(a) A separately-trained 16×16 model — requires 16×16 training data,
    which our generator produces SLOWLY (5 puzzles/sec at 8×8/5c, will
    be much worse at 16×16/22c).
(b) A size-invariant model architecture that can be trained on small
    puzzles and inferred on larger ones.
(c) A hybrid that uses Learned at small scales (joining frame-first
    decomposition) and a hand-crafted heuristic at large scales.

This vol picks ONE.

## Audit-at-open

Items aged ≥ 3 volumes by vol-28 open (incremented from vol-27's deferred
list):

- `piece-orbit-as-atom` — `wont-do` at vol-27.
- `multi-cell-bound-ascent` (6 vols, ALNS-axis). Deferred at vol-27 with
  reason; re-evaluate.
- `bound-floor-alns-with-per-step-check` (6 vols, ALNS-axis).
- `kissat-rc2-maxsat` (5 vols, bound-axis).
- `diverse-457-search` (6 vols, overnight job).
- Any items created during vol-26 or vol-27.

Action at vol-28 open: read each, decide in writing.

## Binding items

Pick ONE of T1A, T1B, T1C. ONE binding item only (CLAUDE.md discipline).

### T1A — Variable-size GNN

Rewrite the model to accept (W, H) at inference time instead of baking
it at construction. Use graph attention with explicit edge indices
instead of `GridConv`'s fixed-buffer pattern. Train on a mixture of
6×6 / 7×7 / 8×8 / 10×10 puzzles. Evaluate transfer to 12×12 and
canonical 16×16.

- **Honest cost**: ~3-5 days build (architecture rewrite, training
  infra changes for variable batch shapes, ONNX export with dynamic
  shapes) + ~1 day training compute.
- **Risk**: ONNX dynamic shapes are fragile in our `ort` version;
  validate export early.

### T1B — 16×16-specific model

Train a separate model directly on canonical 16×16 puzzles. Skip the
generator — use the actual canonical 5-clue E2 instance as the only
"training" puzzle, with expert trajectories from our existing cold-start
solver runs. Imitation gives marginal lift; the model effectively
memorizes the structure of canonical E2's hard regions.

- **Honest cost**: ~1-2 days build (data pipeline from existing engine
  runs).
- **Risk**: training set is one puzzle (massively underfit).

### T1C — Learned-on-ties hybrid

Add a `ValueOrder::LearnedOnTies` variant that defers to LCV's score
first and uses Learned ONLY when LCV produces ties (same score for ≥ 2
candidates). On canonical E2 with `joe_depth150_bp`, ties are common
and breaking them well could improve cold-start depth.

- **Honest cost**: ~2 days build (engine wiring) + ~1 day evaluation.
- **Risk**: cross-domain transfer (model trained on 6×6/5c, applied at
  16×16/22c) may produce garbage scores → no signal in ties.

## What this vol explicitly does NOT do

- ❌ Diffusion. Imitation passed the gate; diffusion is an open question
  for a later vol if T1 succeeds and the lift is small.
- ❌ Multi-task training across sizes simultaneously. T1A trains on a
  mixture but the loss is the same imitation loss.
- ❌ Engine architecture changes beyond plumbing the new ValueOrder.
  Variable-size search is a deeper refactor.

## Discoveries during the vol → log, don't pivot

If we discover mid-vol that, e.g., 8×8/5c training data costs an
unaffordable amount of compute, log to BACKLOG with `since: vol-28` and
adapt the binding item scope — don't expand to additional builds.

## Vol-close protocol

Standard:
1. Update BACKLOG status of chosen T1.
2. Amend [[learned-value-order]] with the new measurement.
3. Write `sessions/vol-28.md`.
4. Draft `VOL-29.md` gated on T1 result.
5. Memory entry if the result is gate-significant (PASS at canonical →
   a finding worth caching for fresh agents; FAIL → close note).

## Honest cost estimate

- T1A: 4-6 days.
- T1B: 2-3 days.
- T1C: 3-4 days.
- Audit + writeup: 0.5 day.

## Why this is the right shape

Vol-26 → vol-27 closed the small-scale gate cleanly. Vol-28's question
is squarely "does this scale up?" — a single binding item picks the
cheapest path that meaningfully answers that question.

T1C is the lowest-risk lower-EV move (engineering work, lower expected
lift). T1A is the highest-EV highest-cost (proper variable-size model,
proper training infrastructure). T1B is in between but has the smallest
training set problem.

**Recommendation: T1C.** It's the move that produces a definitive
canonical-E2 measurement without the variable-size architecture rewrite.
If T1C lifts cold-start by even +1 (from 457 to 458), the ML direction
is permanently alive and vol-29 commits to T1A. If T1C is a null, we
have evidence that the imitation signal doesn't transfer cross-scale
and the direction is harder than vol-26's lift suggested.

## Linked concepts

- [[learned-value-order]] — vol-26 + vol-27 measurement.
- [[scan-order]] — variable-order families.
- [[edge-bp-marginals]] — earlier learned-from-data attempt.

## Linked sessions

- [[vol-27]] — direct predecessor.
- [[vol-26]] — the original gate.
