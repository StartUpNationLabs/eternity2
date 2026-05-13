# VOL-29 — 16×16-trained model on canonical-E2 expert trajectories

**Opened**: 2026-05-13 (vol-28 close).
**Status**: drafted; awaits open.
**Gated on**: vol-28 result. Cross-domain transfer (6×6→16×16) was
refuted. The remaining ML path that doesn't already have a refutation
is to train on canonical-E2 expert trajectories *from our own engine's
runs*, so the train and inference distributions match by construction.

## Why this volume exists

Vol-28 closed cleanly negative: the v2 size-agnostic model trained at
6×6/5c produces confidently wrong scores at 16×16/22c. Two binding root
causes (train/inference candidate distribution mismatch + color
embedding cardinality) point at the same fix:
**train on canonical-E2 partials that the engine has actually visited**.

## Audit-at-open

Items aged ≥ 3 vols by vol-29 open. By this point:

- `piece-orbit-as-atom` — `wont-do` at vol-27.
- `kissat-rc2-maxsat` — `wont-do` at vol-28.
- `multi-cell-bound-ascent` (7 vols, ALNS-axis). Deferred 2 vols.
- `bound-floor-alns-with-per-step-check` (7 vols, ALNS-axis).
- `diverse-457-search` (7 vols).
- Any items from vol-26-28.

Action at vol-29 open: read each in BACKLOG, decide.

## Binding item

ONE only.

### T1 — 16×16-specific learned model (Lever B from VOL-28)

Train a v2-architecture model directly on canonical-E2 cold-start
trajectories from our own engine, then use it inside `joe_depth150_bp`
as the value-order.

**Data pipeline**:
1. Run `joe_depth150_bp` on canonical E2 for N=100 seeds, each with
   a 60-second budget. Capture every `ValueTried` event the engine
   commits to (i.e., depth increases). Each `(partial_board, position,
   piece_id, rotation)` tuple is a training sample.
2. Each puzzle is the SAME canonical E2 — but each seed produces a
   different trajectory (the engine's tie-breaking + propagator order
   varies). Expected ~500k training samples from 100 seeds × ~150
   depth × ~30 partial states (taking samples at every depth, not just
   the final).
3. Negatives at training time: sample from the engine's *actual
   domain* at each step (we have it; it's the bitset). This kills
   root-cause #1 from vol-28.
4. Color embedding: see all 22 canonical-E2 colors. Kills root-cause #2.

**Honest cost**:
- Data capture: ~1 hour wall-clock × N=100 seeds × 60s budget = ~2 hr
  wall-clock with single-thread (or ~15 min if we parallelize).
- Training: ~1 hr CPU at vol-28 throughput (~30s/epoch × 10).
- ONNX export + engine integration: already shipped from vol-28.
- Measurement: `canonical_eval --profile joe_depth150_bp --mode
  learned` at 5-min budget on N=20 seeds.

Total: 1-2 days.

**Gate condition** (set BEFORE running, to prevent goalpost-moving):
- `joe_depth150_bp + Learned (v3, 16×16-trained)` reaches depth ≥
  `joe_depth150_bp (baseline)` median + 10 on N=20 seeds (i.e., ≥ ~175
  given vol-28 baseline of 165).
- AND wall-clock per seed within 1.5× baseline (model inference cost
  doesn't bury the win).
- AND no regression at 6×6 — keep the v1 vol-27 gate still passing.

If all three hold: vol-30 commits to LearnedOnTies hybrid + multi-seed
deep cold-start campaign on canonical E2.

If any condition fails: the learned-policy direction is **closed** for
canonical 5-clue E2 with our current ML stack. The vault page becomes
the canonical no-go report.

## What this vol explicitly does NOT do

- ❌ Diffusion / RL / multi-task / fancier architectures. T1 is a clean
  test of "does training on canonical-E2 trajectories produce a useful
  in-place value-order?"
- ❌ Variable-size architecture (the v2 model already supports this and
  is preserved). We're training at 16×16 only because the goal is 16×16
  performance.
- ❌ Anything outside the ML axis (audit defers vol-22's bound items
  and `diverse-457-search`).

## Discoveries during the vol → log, don't pivot

Vol-28's "training on synthetic doesn't transfer" finding is the kind
of mid-volume surprise vol-29 will face less of, but if a new surprise
arises (e.g., capturing engine trajectories is broken at large depth),
log to BACKLOG with `since: vol-29` rather than reshaping T1.

## Vol-close protocol

Standard:
1. Update T1 status in BACKLOG.
2. Amend [[../concepts/learned-value-order]] with vol-29 measurement.
3. Write `sessions/vol-29.md`.
4. If gate PASS: draft VOL-30.md for LearnedOnTies hybrid + multi-seed.
5. If gate FAIL: update [[../concepts/learned-value-order]] status to
   `refuted` (currently `built`) for the canonical-transfer claim,
   keep `built` for the 6×6 gate result. Close the direction.

## Linked concepts

- [[../concepts/learned-value-order]] — full vol-26/27/28 history.
- [[../concepts/edge-bp-marginals]] — historical "learned-from-data
  value-order" comparison.

## Linked sessions

- [[../sessions/vol-28]] — direct predecessor (cross-domain refuted).
- [[../sessions/vol-27]] — bridge + 6×6 gate PASS.
- [[../sessions/vol-26]] — original 6×6 gate.
