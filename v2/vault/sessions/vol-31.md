---
tags: [session, vol-31, ml-score-lift]
---

# Vol-31 — depth lift propagates to score at both weak and strong pipelines

**Theme**: Vol-30's +9 depth lift from LearnedOnTies turns into a +10
score lift at weak recovery (alns_only 5min) and +8 score lift at
strong recovery (pt_e2 15min with Houdayer + kicks). First ML-driven
score lift on canonical 5-clue 16×16 Eternity II — survives the
stronger pipeline.

## What was attempted

T1 — score-axis A/B at iso-budget across two recovery layers.

1. `crates/ml-export/canonical-eval`: added `--dump-partial PATH` to
   serialize the engine's `best_partial` board (works on `TimedOut`,
   `Cancelled`, `Solved` outcomes).
2. Generated two partials at the same 60s `joe_depth150_bp` budget:
   - baseline (default = EdgeBpMarginals) → depth-165 partial (170
     placed cells incl. 5 hints).
   - LearnedOnTies (E2_LEARNED_MODEL=ml/runs/v3/model.onnx) → depth-174
     partial (179 placed cells).
3. Ran A/B at two pipeline strengths:
   - **Weak**: `alns_only --ops winning5 --repair-kind sa` at 5 min.
   - **Strong**: `pt_e2 --start-from <partial> --pin-hints
     --houdayer-every 10 --kick-every 20` at 15 min, 8 replicas.
   - Conversion partial → pt_e2 placement format (length-256 with nulls)
     done in Python (~5 LOC).

## What was measured

**Weak pipeline (alns_only 5 min, seed=1, winning5 ops, SA):**

| starting partial | final matched | Δ |
|---|---:|---:|
| baseline-165 | 426/480 | — |
| **LearnedOnTies-174** | **436/480** | **+10** |

Reproducibility check at seed=2 on baseline-165: matched=425 (within
1 of seed=1's 426). Stable enough.

**Strong pipeline (pt_e2 15 min, 8 replicas + Houdayer + kicks):**

| starting partial | initial edges | PT-15min best | Δ |
|---|---:|---:|---:|
| baseline-165 | 280/480 | 437/480 | — |
| **LearnedOnTies-174** | 303/480 | **445/480** | **+8** |

PT-174 hit 443 at round 5 (~0.2s), 445 by round 25 (~1s), then
plateaued — the LearnedOnTies partial is a *better starting basin*
that the strong pipeline preserves but doesn't amplify.

## What was refuted

- **The "depth lift might not translate to score" risk** (vol-23/24
  cautioned that CP-deep partials don't always post-ALNS better).
  At iso-budget A/B, LearnedOnTies's +9 depth lift gives **+10 at
  weak / +8 at strong** score. Translation works.

## What was confirmed

- **The +9/+10/+8 is genuine ML signal**, not artifact of the recovery
  layer. Two different recovery pipelines both prefer the
  LearnedOnTies partial over the baseline partial at iso-budget.
- **The strong pipeline doesn't amplify the ML signal, it preserves
  it**: PT-174 reached the lift in 1 second, then ran the remaining
  899 seconds at the +8 plateau. The lift comes from the partial's
  *initial advantage*, not from PT discovering new moves on top of it.

## What is open

- **Score record**: 445 ≠ 457. Vol-22's record came from finding a
  specific lucky basin (vol-18 hot-PT, all 11 saved 457 boards
  byte-identical). Vol-31 doesn't break 457; vol-32+ might if we
  combine LearnedOnTies-174 with vol-22's basin-escape recipe (longer
  PT + bound-ascent + Hungarian).
- **Hyperparameter sweep** (BACKLOG: `learned-on-ties-hyperparam-sweep`):
  EPS × MAX_K grid. The +9 depth lift is invariant across models;
  it might or might not be invariant across EPS / MAX_K.
- **RL self-play** (BACKLOG: `learned-16x16-long-train` flavor 2): the
  only path to break the imitation ceiling for full-Learned mode.
  Not on critical path now that LearnedOnTies works.

## Concepts touched

- [[learned-value-order]] — Vol-31 measurement section
  added (both pipelines, full table). First ML-driven score lift on
  canonical 5-clue 16×16 E2.

## Open at close

- vol-32 candidate directions in BACKLOG:
  1. LearnedOnTies-174 + vol-22 basin-escape recipe → does the
     LearnedOnTies starting basin enable basin-escape to a >457 basin?
  2. Hyperparam sweep (cheap, 5 min compute).
  3. Long-horizon PT (1-2 hr) from LearnedOnTies-174 — does the
     plateau open up with more time?

## Linked memory

- `project_e2_vol31_ml_score_lift` (NEW)
