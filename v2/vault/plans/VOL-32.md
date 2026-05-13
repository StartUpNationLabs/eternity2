# VOL-32 — overnight ML engineering: sweeps, sizes, learning rates

**Opened**: 2026-05-13 (vol-31 close + community research night).
**Status**: drafted; ready to launch as overnight work.
**Theme**: machine-learning *engineering*. The 4-volume ML arc (vol-26..31)
proved the algorithm — the LearnedOnTies hybrid produces +9 cold-start
depth and +8/+10 score lift at canonical 16×16. We have **not** done
the engineering work that follows a proof-of-concept: hyperparameter
sweeps, model-size scaling, learning-rate schedules, candidate-count
ablations. Tonight is that work.

## Why this volume exists

Three concrete observations:

1. **The +9 depth lift is invariant across v3 / v3b / v4** (vol-30 T2).
   Train data size and model width were both varied; result didn't
   move. That's evidence the bottleneck is the hybrid *policy*
   (EPS=0.05, MAX_K=8) not the model. **EPS / MAX_K have never been
   swept.**
2. **The community-research detour** (vol-32 open) surfaced concrete
   high-value engineering items (vanilla fast backtracker;
   capiman/e2 70M unsat-clause database; Joe's iteration-budgeted
   pruning). These are NOT ML, but tonight we'll be running long ML
   experiments and the spare CPU cycles can also drive ALNS post-fill
   batches.
3. **User directive (2026-05-13)**: "I want the night spent on ML
   optimization, models, hyperparameters, sizes, learning rates etc...
   like ML engineering. BUT only if that could bring potential value."
   The +9/+10 result IS the prima facie value. We sweep.

## Audit-at-open

Items aged ≥ 3 vols (vol-32 open, items ≤ vol-29 = old).
Vol-31 deferred ALNS-axis items; carrying that.

- `multi-cell-bound-ascent` (10 vols, ALNS): defer; tonight is ML.
- `bound-floor-alns-with-per-step-check` (10 vols, ALNS): defer.
- `diverse-457-search` (11 vols): defer.
- `learned-on-ties-hyperparam-sweep` (1 vol since vol-30): **PICKED, becomes T1**.
- `learned-on-ties-long-pt` (1 vol since vol-31): **PICKED, becomes T2's recovery layer**.

## Binding items

**Three tracks, runnable in parallel (CPU contention is the budget gate, not human time).**

### T1 — LearnedOnTies hyperparameter sweep (ML)

Sweep over the two tunables exposed in `crates/solver-engine/src/lib.rs`
via env vars `E2_LOT_EPS` and `E2_LOT_MAX_K`:

| EPS | MAX_K |
|---|---|
| 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.40 | 2, 4, 8, 12, 16, 24, 32 |

7 × 7 = 49 configs. Each at 60s budget (the headline measurement) =
49 minutes sequential, ~15 minutes 4-way parallel. **Output**: depth +
node-count + backtracks per config. Heatmap shows whether +9 is the
real ceiling or the default config is sub-optimal.

**Gate**: at least one config reaches depth ≥ 175 (one beyond
current +9). If yes, headline lifts. If no, the +9 plateau is the
genuine canonical-E2 ceiling under the current model.

Cost: ~15 min wall-clock parallel. Driver: `ml/sweep_lot.sh`.

### T2 — Model-size / training-data / learning-rate sweep (ML)

Train multiple models varying:

- **hidden_dim**: 32, 64, 128, 256
- **color_emb**: 8, 16, 24, 32
- **lr**: 1e-4, 5e-4, 1e-3, 3e-3
- **epochs**: 30, 60, 120
- **data scale**: 20 traj, 100 traj, **300 traj** (NEW capture
  required for 300)
- **candidate count C**: 8, 12, 24

We don't run the full Cartesian — that's 4×4×4×3×3×3 = 1728 configs.
Instead do an **ablation pattern**:

1. **Baseline** (v3 = hidden 64, emb 16, lr 1e-3, 30 ep, 20 traj, C 12) — already done.
2. **Size sweep** (hold all else): hidden ∈ {32, 64, 128, 256}, fixed
   emb=16, lr=1e-3, 30 ep, 100 traj. 4 models.
3. **LR sweep**: hidden=128 (best from #2), lr ∈ {1e-4, 5e-4, 1e-3, 3e-3}, 30 ep. 4 models.
4. **Data scale**: capture 300 traj overnight (parallel=4 ≈ 75 min);
   train hidden=128 + best LR + 60 epochs. 1 model.
5. **Candidate count**: hidden=128, best LR, 30 ep, C ∈ {8, 12, 24}. 3 models.

Total: 4 + 4 + 1 + 3 = 12 trained models. Each is ~5 min training (we
measured this) — 60 min compute. Plus the 75-min data capture if
needed. Plus 12 × 60s gate measurement = 12 min.

**Each trained model evaluated on three modes**: `learned`,
`learned_on_ties` (default EPS/MAX_K), `learned_on_ties` (best from T1).

**Gate**: at least one (model, EPS, MAX_K) combo reaches depth ≥ 176.
If yes, headline lifts. If no, the +9 plateau is genuinely structural.

Cost: ~3-4 hr wall-clock parallel with T1 (they don't contend much —
T1 uses canonical-eval which is single-thread; T2 trains use 8 cores
sequentially).

### T3 — Multi-seed PT/ALNS lottery from LearnedOnTies-174 (score axis)

While T1 + T2 run, the remaining CPU bandwidth runs the **score-axis
lottery** from the user-suggested original VOL-32:

- Capture 30+ depth-174 partials by running `joe_depth150_bp +
  LearnedOnTies` with 30 different seeds × 60s each.
  - Note: engine value-order is deterministic given seed. Seeds come
    from varying `VariableOrder::BorderFirstMrv` tie-breaks (we
    already do this for canonical-capture).
- For each partial, run `pt_e2` at 30 min (strong config: 8 replicas,
  Houdayer, kicks).
- Histogram of final scores. The vol-31 result was 445 from one seed;
  the lottery hunts for a 450+ outlier.

Cost: 30 × 30 min × pt_e2 (which is 8-replica) but pt_e2 saturates 8
cores. So 30 sequential = 15 hours, OR 30 × pt_e2 with fewer replicas
(e.g., 4 replicas, 30 min) = ~7.5 hours sequential = ~2 hr 4-way.

**Gate**: at least one seed lands at score ≥ 450 (above vol-31's 445).
If yes: depth-174 starting basin admits exploration deeper than the
single-seed measurement suggested. If no: 445 is structural for
LearnedOnTies-174.

### T4 (light, non-blocking) — ML training-curve diagnostics

While the long runs are running, write small Python tooling to
*understand* what the models learned:

- Distribution of `LearnedOnTies` fire-rate per depth (how often does
  the tie-rerank actually trigger?). Already-existing engine has the
  data via instrumentation env var; needs a small bin.
- Per-cell error rate: what fraction of expert placements is the model
  top-1, top-3, top-12?
- Histogram of EdgeBpMarginals tie-cluster sizes at each canonical-E2
  depth. Tells us whether vol-30's +9 lift is coming from "many small
  ties broken better" or "a few critical ties at specific depths".

Cost: 1-2 hr Python work, no CPU contention.

## What this vol explicitly does NOT do

- ❌ Vanilla fast backtracker (BACKLOG `vanilla-fast-backtracker` — vol-33+).
- ❌ Unsat-clause propagator (BACKLOG `unsat-clause-propagator` — vol-33+).
- ❌ Joe's iteration-budgeted prune (BACKLOG — vol-33).
- ❌ RL self-play (vol-34+).
- ❌ The vol-32 T1 (basin-escape) that I drafted before today's
  research — replaced by T3 score-axis lottery which is the lighter
  version of that question.

The community-research items are *engineering* (Rust speed, propagator
plumbing, parameter policy) and don't belong in an *ML engineering*
night. They become vol-33 once we know whether ML hyperparam
optimization moves the +9 plateau.

## Vol-close protocol

At vol-32 close:

1. Update BACKLOG status of each tracked sweep + lottery.
2. Write `sessions/vol-32.md` with the heatmap + best config.
3. If new ML-driven canonical record (depth >174 OR score >445):
   amend `concepts/learned-value-order.md` and write memory entry.
4. Draft `plans/VOL-33.md` — likely **vanilla fast backtracker +
   unsat-clause propagator** depending on whether vol-32 lifted ML.
5. INDEX score-history row.

## Files / drivers needed

```
ml/sweep_lot.sh                NEW   T1 hyperparam sweep driver
ml/sweep_train.sh              NEW   T2 model-size/LR sweep driver
ml/eval_all_models.sh          NEW   T2 eval-12-models driver
ml/diagnose_model.py           NEW   T4 fire-rate / top-k analyser
crates/ml-export/canonical_capture: existing — re-use with --parallel 4
crates/ml-export/canonical_eval:    existing — already supports --dump-partial
crates/benchmark/pt_e2:              existing — score-axis A/B
```

Nothing new in Rust. All tonight's work is in `ml/` (Python / shell)
and in calling existing bins.

## Honest cost estimate

- T1: 30 min (build script + 15 min compute).
- T2: 3-4 hr (build + 300-traj capture + 12 trains + 12 evals).
- T3: 2-3 hr (depending on parallelism choices).
- T4: 1-2 hr (Python diagnostic + writeup).
- Vault close: 30 min.

**Total**: 7-10 hr of mixed wall-clock. Fits an overnight window
comfortably. The user-stated time-estimate rule applies (estimates are
typically 1.5-3× too large; actual will likely be 5-7 hr).

## Why this is the right shape for the night

- **It does what the user asked** (ML engineering on a promising
  signal).
- **It's parallelizable**: T1 + T2 + T3 don't fully contend, and T4 is
  human-time-only.
- **Each track has a clean gate**: PASS or FAIL is a single number.
- **Every output is informative**: even FAIL on all three teaches us
  the +9 plateau is structural and vol-33+ should pivot to the
  engineering items from community research.
- **Negative results count**: if no sweep produces a lift, that's a
  clean closure on the ML-imitation-only direction for canonical
  E2 — and the engineering items in BACKLOG (vanilla speed,
  unsat-propagator, Joe-prune) become THE high-EV path.

## Linked concepts

- [[../concepts/learned-value-order]] — Vol-26..31 history; tonight
  amends with Vol-32 measurement.
- [[../sessions/vol-31]] — direct predecessor.

## Linked sessions

- [[../sessions/vol-31]] — score lift result.
- [[../sessions/vol-30]] — +9 depth invariance across models.
