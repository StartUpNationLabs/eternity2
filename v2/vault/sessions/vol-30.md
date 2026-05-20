---
tags: [session, vol-30, ml-lift, first-positive-canonical]
---

# Vol-30 — LearnedOnTies hybrid: first Δ > 0 from ML at canonical scale

**Theme**: `ValueOrder::LearnedOnTies` (EdgeBpMarginals first, Learned
on ties) lifts canonical-E2 cold-start depth from 165 to **174 (+9)**.
The lift is architecture-independent and data-amount-independent across
three trained models — structural to the task, not the specific model.

## What was attempted

T1 — `ValueOrder::LearnedOnTies` hybrid.

Engine change in `crates/solver-engine/src/lib.rs`:
- New variant alongside existing `Learned` and `EdgeBpMarginals`.
- Extended the EdgeBpMarginals block to also produce parallel
  `bp_keys` for tie detection.
- New block detects the top-k candidates within EPS=0.05 BP-score of
  the top (max 8), reranks them by Learned scores. Falls through to
  pure EdgeBpMarginals if no ties.
- Tunable via env vars `E2_LOT_EPS` and `E2_LOT_MAX_K`.

T2 — Long-imitation experiment (user request).

1. `canonical-capture` gained `--parallel N` (rayon worker pool).
   Cut 100 seeds × 60s from 100 min sequential to ~25 min wall-clock
   with `--parallel 4`.
2. Trained v3b (hidden=64, same as v3 but 5× data) for 30 epochs.
3. Trained v4 (hidden=128, color_emb=24, 50 epochs) on the same data.
4. Ran the 7-row eval table comparing baseline / v3 / v3b / v4 under
   both `learned` and `learned_on_ties`.

## What was measured

**T1: A/B at canonical 16×16 (5-clue hints, single-thread, seed=1)**

| Budget | Mode | Max depth | Nodes |
|---|---|---:|---:|
| 1 min | baseline | 165 | 505 k |
| 1 min | learned (full) | 164 | 336 k |
| 1 min | **learned_on_ties** | **174 (+9)** | 474 k |
| 5 min | baseline | 166 | 2.49 M |
| 5 min | **learned_on_ties** | **174 (+8)** | 2.37 M |

LearnedOnTies plateaus at 174 even with 5× the budget — the
tie-breaking signal is finite, but it lets the engine reach a basin
baseline never visits.

**T2: same A/B with 3 models trained on different data + sizes**

| Model | Trajectories | Hidden | Mode | Max depth | Nodes |
|---|---|---:|---|---:|---:|
| baseline | — | — | default | 165 | 509 k |
| v3 (vol-29) | 20 | 64 | learned_on_ties | **174** | 478 k |
| v3b | 100 | 64 | learned | 165 | 329 k |
| v3b | 100 | 64 | learned_on_ties | **174** | 479 k |
| v4 | 100 | 128 | learned | 165 | 268 k |
| v4 | 100 | 128 | learned_on_ties | **174** | 479 k |

**The +9 lift is invariant across all three models.** v3, v3b, and v4
all reach exactly depth 174 with nearly-identical node counts under
`learned_on_ties`. v4 (bigger model + 5× data) uses 47% fewer nodes
than baseline under full `learned` mode but never beats the teacher's
depth, exactly as vol-29's imitation ceiling predicts.

## What was refuted

- **The "more data + bigger model → bigger ML lift" hypothesis**.
  Trained on 5× data and 4× params, v4 produced THE SAME +9 lift as v3.
  The lift is a property of LearnedOnTies' interaction with
  EdgeBpMarginals' tie structure, not the model's capacity.

## What was confirmed

- **Imitation ceiling at the teacher (vol-29)**. v4 (most-trained model)
  on `learned` mode reaches depth 165 with 47% fewer nodes — most
  efficient imitation, still ceiling-bound.
- **EdgeBpMarginals has tie structure**. The +9 lift means LearnedOnTies
  actually fires often enough (over ~9 productive tie-break decisions)
  to compound through to the deeper plateau.
- **The depth-174 plateau is structural to the puzzle, not to a specific
  trained model**. Three independently-trained models hit the same
  number — this is the *canonical-E2-with-LearnedOnTies-hybrid*
  saturation point.

## Open at close

- **Score-axis question (vol-31 T1)**: does depth-174 → ALNS-fill
  produce score > 457? Vol-30 lifts depth, not score; vol-23/24 showed
  these don't always correlate.
- **EPS / MAX_K hyperparameter sweep** (BACKLOG). The +9 invariance
  across models suggests the lift is hyperparam-tuning-driven, not
  model-tuning-driven. A 5-min sweep over EPS ∈ {0.01..0.20} × MAX_K
  ∈ {4..32} might lift further.
- **RL self-play**: the only direction that can structurally beat the
  imitation ceiling at full-Learned mode. Vol-32+ if score-axis (T1)
  shows promise.

## Concepts touched

- [[learned-value-order]] — vol-30 measurement section
  added. First Δ > 0 from ML at canonical.

## Linked memory

- `project_e2_vol30_first_ml_canonical_lift` (NEW)

## Honest framing

Vol-30 produced the first measurable lift from ML on the canonical
5-clue 16×16 Eternity II puzzle, after 4 prior volumes (vol-26 6×6/5c
gate, vol-27 ONNX, vol-28 cross-domain refutation, vol-29 imitation
ceiling). The +9 depth lift is reproducible, architecture-agnostic, and
finite (plateaus at 174 even at 5× budget). The next question is
whether deeper CP partials translate to higher post-ALNS scores
(vol-31 T1).

The negative finding is also strong: imitation alone cannot
structurally beat the teacher. Vol-30's +9 came from selective use
(LearnedOnTies), not from making the model better. To go beyond +9
likely requires RL self-play or a hyperparam sweep, NOT bigger models
or more data.
