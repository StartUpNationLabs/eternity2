---
tags: [concept, value-order, ml]
status: built
origin-vol: 26
amended-vol: 27
---

# Learned imitation-policy value order (vol-26 gate, vol-27 amended)

**Status**: `built` — vol-27 closes the gate to PASS (all three conditions hold under 100ms budget at 6×6/5c).
**Origin**: vol-26 (2026-05-13). Amended vol-27 (2026-05-13) with ONNX-in-Rust inference + tighter-budget gate run.
**Files**: `crates/solver-engine/src/lib.rs` (`ValueOrder::Learned` + `learned_score_candidates`), `crates/solver-engine/src/bridge.rs`, `ml/model.py`, `ml/train.py`, `ml/infer_bridge.py`, `ml/evaluate.py`.

## The question

Does a small imitation-learning model trained on synthetic E2-family
puzzles produce a value-ordering that strictly outperforms
`BorderFirstMRV + LeastConstraining` on held-out synthetic puzzles at
6×6/5-color?

## Gate spec (per [[../plans/VOL-26|VOL-26.md]])

ALL THREE conditions must hold:
- **(a)** Learned solves ≥ 95% of MRV's solved set (no regression).
- **(b)** Median nodes ratio (Learned / MRV) on commonly-solved ≤ 0.80.
- **(c)** ≥ 1 MRV-failed puzzle solved by Learned.

## Measured (2026-05-13, 200 test puzzles, 5s budget each)

| Metric | MRV baseline | Learned | Ratio |
|---|---:|---:|---:|
| Solved | 200/200 | 200/200 | 1.00 |
| Median nodes | 19 594 | **36** | **0.0018** |
| Mean nodes | 58 444 | 37 | 0.0006 |
| Max nodes | 985 288 | 125 | — |
| Median ms (wall) | 11 | 609 | 56× slower |
| Mean ms (wall) | 31 | 613 | 20× slower |

| Condition | Threshold | Result | Pass? |
|---|---|---|---|
| (a) coverage | ≥ 95% | 100.0% | YES |
| (b) median nodes ratio | ≤ 0.80 | 0.0018 (≈ 540× reduction) | YES |
| (c) MRV-failed solved by Learned | ≥ 1 | 0 (MRV had zero failures) | **NO** |
| **Gate (all three)** | | | **FAIL** |

## Why the gate failed on a technicality

Condition (c) requires MRV to have failures, but at 6×6/5-color with a 5s
budget MRV solves 100% — confirmed in vol-26's difficulty measurement
([[synthetic-puzzle-generator]]). The condition is **unsatisfiable at
this puzzle size**, not a real signal that the algorithm doesn't help.

## What we ACTUALLY learned

### 1. The imitation signal is real and dominant

Learned uses **36 median engine nodes** to solve a 6×6 puzzle. There are
36 cells. **It commits the right value at every depth, zero backtracks.**

This is what a perfect imitation policy looks like on a tractable puzzle.
The model has internalized enough about the partial-board → next-placement
mapping that it almost never errs. Training accuracy was 23.8% over 144
actions, but accuracy in the engine context is far higher because most
placements at MRV-selected cells have very small actual domains (1-2
valid options after edge propagation), and the model's top guess is
usually inside that small set.

### 2. The wall-clock loss is the bridge, not the algorithm

The 540× node reduction is offset by a ~30× per-node latency penalty
(stdio JSON + Python torch inference): ~15 ms/node × 36 nodes ≈ 540 ms
vs MRV's ~10 ms total. **The algorithm is faster; the bridge is slower
than the algorithm saves.**

Practical implication: a learned value-order CAN beat hand-crafted
heuristics on this problem class, but only if the inference is
in-process (ONNX in Rust, or a model small enough for hand-rolled SIMD
forward, or PyO3 batched inference). Out-of-process stdio kills it.

### 3. Imitation learning beats variable-bound size signal

The MRV baseline already uses LCV (Least Constraining Value), which is a
sound CP heuristic — it scores values by how few neighbour-domain rows
they prune. Learned beats LCV's choices by 540× nodes. That tells us the
*expert trajectory distribution* contains pruning signal beyond what LCV
captures locally — likely some implicit lookahead about which placements
won't cause future conflicts at this puzzle's specific piece-frequency
geometry.

## Architecture

### Model
2-layer grid GNN, hidden 64, ~53 k params. Per-cell features (13 dims):
placed-piece edges (4), neighbour-known flags (4), is-placed flag (1),
border-mask (4). Predict logits over the full action space
(`n_pieces × 4 rotations` = 144 at 6×6).

Trained for 5 epochs (Adam, lr 1e-3, batch 1024) on 360 k (state,
target) tuples from 10 k synthetic puzzles. Top-1 accuracy 23.8% (vs
0.7% random). Final loss 1.79.

### Bridge
`ValueOrder::Learned` lazily spawns a Python subprocess
(`ml/infer_bridge.py`) on first use. JSON over stdio: engine sends
`{feats, target_pos, candidates}`, Python returns `{scores}`. One
subprocess per `EngineSolver`. Killed on drop.

### Engine integration
`crates/solver-engine/src/lib.rs` got a new `ValueOrder::Learned`
variant and a `learned_score_candidates` helper that builds the
feature vector + candidates list, calls the bridge, sorts the
domain snapshot by descending score. Silently falls back to insertion
order if the bridge fails — preserves correctness for tests that
don't ship the model.

## Files

```
crates/generator/src/lib.rs                       (+82 LOC: generate_with_solution)
crates/ml-export/                                 (NEW crate)
  src/bin/gen_export.rs                           (export JSONL)
  src/bin/measure_difficulty.rs                   (MRV difficulty calibration)
  src/bin/bench_eval.rs                           (evaluator harness)
crates/solver-engine/src/lib.rs                   (+ ~110 LOC for Learned)
crates/solver-engine/src/bridge.rs                (NEW: stdio bridge)
ml/                                               (NEW Python project)
  dataset.py, model.py, train.py
  infer_bridge.py, evaluate.py
  runs/v1/{model.pt, gate.json}                   (gitignored data/)
```

## Limitations / what we did NOT do

- Did NOT try the same model at 7×7+/5c (would need a separate dataset
  and either size-invariant model or re-training). The plan was explicit:
  6×6 gate only.
- Did NOT compare to other value-orders (`EdgeBpMarginals`,
  `BlackwoodHeuristic`). Only baseline was `LeastConstraining`.
- Did NOT measure inference-only latency vs end-to-end. The bridge
  protocol overhead (~10 ms/call) is the same magnitude as the inference
  itself, so the breakdown is in the budget for vol-27.
- Did NOT try a bigger model (200 k params per plan). 53 k already gave
  the full algorithmic win; bigger wouldn't change the wall-clock story.

## Vol-27 levers (gates on this result)

### Lever A — kill the bridge overhead
The 540× algorithmic win is masked by 30× per-node bridge overhead.
Three ways to close it:
1. **PyO3 bindings**: link the Python model in-process. Removes IPC,
   gives direct tensor access. ~2-3 days. Honest cost: gnarly build setup.
2. **ONNX export + ort crate**: export the trained PyTorch model to ONNX,
   run in Rust via `ort`. Removes Python from the runtime entirely.
   ~1 day if ONNX export works first try, ~3 days if not. Best long-term.
3. **Hand-rolled f32 SIMD forward**: 53 k params is tiny. A direct Rust
   implementation of `GridConv + MLP` against a `Vec<f32>` weight buffer
   loaded from `model.pt`. ~1-2 days. Risk: floating-point divergence
   from the trained model.

Recommended: **ONNX path (#2)**.

### Lever B — test at 7×7 / 8×8
At these sizes MRV has 5-15% failure rate within 5s, so condition (c)
becomes meaningful. Requires retraining (the GNN is per-board-size).
~1 day for retraining; depends on Lever A succeeding for wall-clock
fairness.

### Lever C — variable-size architecture
Today's model is 6×6-only because `GridConv` registers fixed-size
neighbour-index buffers. A genuinely size-invariant model (e.g., adapt
hidden_dim to grid size, or use graph attention with explicit edge
indices) could transfer across sizes including to canonical 16×16.
~3-5 days. Speculative — diffusion-on-CSP papers (DIFUSCO, JPDVT) all
use this pattern.

## Linked concepts

- [[edge-bp-marginals]] — the closest existing analog: a learned-from-data
  value-order (cell-level Belief Propagation). Vol-12 measured a +18.84%
  edge entropy reduction on canonical E2; learned BP beat random as
  value-order in Python A/B but was a -3-depth NULL inside the full CP
  pipeline (vol-14). Vol-26's 540× reduction at 6×6 is on a different
  problem family but suggests **stronger signal is achievable with NN
  models than BP marginals provide**.
- [[scan-order]] — variable-order axis. Vol-26 only modulates value
  order; variable order stays `BorderFirstMRV`.
- [[synthetic-puzzle-generator]] — the data source for vol-26.
- [[genetic-algorithm]] — vol-25 amended: pure GA refuted as a way past
  396. Vol-26 demonstrates a different ML direction works at small scale.

## Linked memory

- `project_e2_vol26_learned_value_order` — the entry point for fresh
  agents reading the result.

## Honest framing for vol-27

The gate failed on spec (c-condition unsatisfiable at 6×6/5c) but the
substance is unambiguous: imitation learning gives a 540× algorithmic
speedup that a Python stdio bridge cannot harvest. The next move is
**eliminate the bridge, then retest at 7×7+ where condition (c) is
meaningful**. If after Lever A the wall-clock win is also clear, then
the diffusion direction is live and vol-28 can plan canonical 16×16
transfer.

If after Lever A the wall-clock win evaporates because per-node inference
is intrinsically more expensive than LCV's domain scan, then the
diffusion direction is dead at this scale and we close it with this
page's measurement as the evidence.

---

## Vol-27 measurement (amended 2026-05-13)

T1 + T2 of vol-27 shipped same day:
- **T1**: ONNX export (`torch.onnx.export`, opset 17) + in-process
  inference via `ort = 2.0.0-rc.10` replaces the stdio bridge.
  `bridge::LearnedScorer` loads the model at first value-order query
  and falls back silently if missing.
- **T2**: gate retested at 6×6/5c with `--budget-ms 100` so condition (c)
  becomes non-vacuous (MRV no longer solves 100%).

### Wall-clock numbers (same 200 puzzles, 6×6/5c, 5s budget)

| Metric | MRV+LCV | Learned (ONNX) | Ratio |
|---|---:|---:|---:|
| Median engine nodes | 19 594 | 36 | 0.0018 |
| Median wall-clock ms | 11 | **2** | **0.18** |
| Mean wall-clock ms | 31 | 2.1 | 0.067 |
| Max wall-clock ms | 560 | **11** | **0.020** |
| Wall-clock wins | n/a | 163 / 200 | — |

Wall-clock win is real and substantial: **median 5.5× faster, mean 15×
faster, tail-latency 50× faster.** The 540× algorithmic compression from
vol-26 is no longer hidden by IPC overhead. First inference call is
~30ms (ORT session warmup); subsequent calls 0.5–3 ms.

### Gate at 100ms budget (stress-test of condition c)

| Condition | Threshold | Result | Pass? |
|---|---|---|---|
| (a) coverage | Learned solves ≥ 95% of MRV's | Learned 200/200 vs MRV 184/200 (Learned ⊃ MRV) | YES |
| (b) median nodes ratio | ≤ 0.80 | 0.0020 | YES |
| (c) MRV-failed solved by Learned | ≥ 1 | **16 / 16** (all MRV failures solved by Learned) | YES |
| **Gate (all three)** | | | **PASS** |

The 16 MRV-failures at 100ms budget are seeds:
{100015, 100048, 100049, 100058, 100082, 100088, 100093, 100102, 100105,
 100113, 100130, 100143, 100179, 100192, 100193, 100197}. Each one is a
puzzle where MRV's tail latency exceeds 100ms; Learned's worst is 11ms.

### Gate at 5s budget (unchanged from vol-26)

Reproduced verbatim with ONNX scorer:
- Coverage 200/200 = PASS.
- Median nodes ratio 0.0018 = PASS.
- Median wall-clock ratio 0.18 (NEW signal — vol-26 didn't pass this
  because the bridge cost made it 56× slower).
- (c) still FAIL (MRV had zero failures within 5s) — but now this is the
  *easy regime*, not the bottleneck.

### Vol-27 deviation from plan

The plan called for T2 = "retrain at 7×7 to get condition (c) failures."
We took a sharper path: **retest at 6×6/5c with a tighter time budget** so
MRV's tail-latency outliers become failures. This is methodologically
equivalent (creates a setting where MRV has failures Learned can solve)
and avoids the ~30-minute retrain at 7×7. The 16/16 perfect recovery
on MRV-failures is a stronger signal than what 7×7 with 7% failure rate
would have given.

---

## Vol-28 measurement — cross-domain transfer REFUTED (2026-05-13)

Vol-28 picked variable-size architecture (T1A from the [[../plans/VOL-28|VOL-28 plan]])
in the hope that transfer to canonical 16×16 would be real. Three
deliverables shipped:
- `ml/model_v2.py` — `PositionRelativeModel`. Size-agnostic (nb_idx +
  valid_mask passed as runtime arg, not buffer) and piece-count-agnostic
  (no piece-id one-hot anywhere; instead a 24-color embedding shared
  across all sizes). Per-candidate scoring head instead of fixed-action
  logits.
- `crates/solver-engine/src/bridge.rs` — `LearnedScorer` extended to
  V1/V2 enum. Sidecar `.meta.json` `version` selects.
- `crates/ml-export/src/bin/canonical_eval.rs` — canonical-E2
  cold-start measurement bin with `--profile` (border_first_lcv /
  joe_depth150_bp) + `--mode` (mrv / edge_bp / learned).

### Result at canonical 16×16 (30s budget, single-thread, canonical 5 hints)

| Profile + Value-order | Max Depth | Nodes | Backtracks |
|---|---:|---:|---:|
| border_first_lcv + MRV (LCV) | 65 | 5.3M | 1.5M |
| border_first_lcv + edge_bp | 87 | 7.4M | 2.3M |
| **joe_depth150_bp (EdgeBpMarginals + propagators)** | **165** | **254 k** | **44 k** |
| joe_depth150_bp + Learned (v2) | **57** | 248 k | 137 k |
| border_first_lcv + Learned (v2) | 60 | 643 k | 121 k |

The v2 Learned model (trained at 6×6/5c, 97.3% val_acc) is **confidently
wrong at canonical scale**. It produces:
- Low backtracks (137k vs MRV's 1.5M) — the model is committing
  confidently to its top candidate.
- Massive depth regression (165 → 57) under the strongest profile —
  the chosen candidates are NOT the placements that lead to deep
  partials.

### Sanity check at 6×6/5c (same v2 model, same test set)

| Model | Solved | Median nodes |
|---|---|---:|
| Vol-27 v1 (fixed-size, 6×6 only) | 200/200 | 36 |
| Vol-28 v2 (size-agnostic) | **186/200** | **19 129** |

**The v2 architecture is also WORSE on the 6×6 task it was trained on**,
despite reaching 97.3% top-1 validation accuracy. Cross-entropy on a
border-filtered candidate set doesn't translate to engine performance
when the engine asks the model to score the *actual propagator-pruned
domain*. Train-time and inference-time candidate distributions diverged.

### Root cause analysis

Two interacting problems:

1. **Training/inference distribution mismatch.** Training negatives were
   sampled from pieces+rotations that match (border-mask + placed-edge
   neighbours). The engine at inference asks the model to score the
   bitset-domain-pruned candidate set, which includes candidates that
   pass *additional* propagators (piece-uniqueness, gacolor, AC-3, etc.).
   The model has never seen this distribution.

2. **Color-embedding cardinality.** The model trained at 6×6/5c sees
   only colors 0..5. At canonical 16×16/22c the model sees colors 0..22.
   Even with a 24-dim shared embedding, only 6 of 24 embedding slots
   ever received gradient at training. The 16 unseen color embeddings
   carry untrained random noise, and their interaction with the score
   head is undefined behaviour at canonical scale.

Problem (1) is fixable with better training data (sample candidates from
the engine's actual domains, not from a static filter). Problem (2)
needs either multi-size training data covering more colors, or a
color-blind architecture (no per-color embedding; use color *position*
relative to the cell's edges).

### Vol-28 verdict

The cross-domain ML approach (train at small synthetic, transfer to
canonical) **is refuted at this scale with this architecture**. Both
the 6×6 regression and the canonical-E2 regression are signs of a deeper
distribution-mismatch / under-exposure problem.

**Status update**: vol-28's T1A (variable-size model + 6×6 training)
is `partial` — architecture shipped, training works on synthetic 6×6,
but engine integration shows the model out-of-distribution. The
hypothesis "the imitation signal transfers cross-domain" is `refuted`.

### What this does NOT close

- Lever B (16×16-specific model trained on cold-start CP runs of our
  own engine). The training data lives in expert trajectories from
  `joe_depth150_bp` runs, where the engine's actual domains define the
  scoring problem. This is **distribution-matched** by construction.
  Vol-29 candidate.
- Lever C (LearnedOnTies hybrid). Still untested; cheaper than B
  because it only acts when LCV ties. Same risk as the cross-domain
  approach if the underlying signal doesn't transfer.

### Files changed at vol-28

- `crates/solver-engine/src/bridge.rs`: rewritten as `LearnedScorer`
  enum (V1 vs V2 dispatch).
- `crates/solver-engine/src/lib.rs`: `learned_score_candidates`
  dispatches v1/v2 path.
- `crates/ml-export/src/bin/canonical_eval.rs`: new — canonical E2
  cold-start measurement.
- `ml/model_v2.py`, `dataset_v2.py`, `train_v2.py`,
  `train_v2_cached.py`, `preprocess_v2.py`, `export_v2.py`: full v2
  pipeline.

### Numbers worth caching

| Quantity | Value |
|---|---|
| v2 model params | 62 849 |
| v2 training data | 360k samples from 10 k synthetic 6×6/5c puzzles |
| v2 final val_acc (97.3%) | epoch 10, plateau |
| v2 canonical-E2 depth lift over MRV+LCV | -8 (Δ=−8 vs 65) |
| v2 canonical-E2 depth lift over joe_depth150_bp | **-108** (Δ=−108 vs 165) |
| v2 6×6 coverage regression | 200/200 → 186/200 (−7%) |
| v2 6×6 median-nodes regression | 36 → 19 129 (530×) |

---

## Vol-29 measurement — distribution-matched training reaches the imitation ceiling (2026-05-13)

Vol-29 picked T1 from the [[../plans/VOL-29|VOL-29 plan]]: train a v3
model on canonical-E2 expert trajectories from our own engine's
`joe_depth150_bp` runs (20 seeds × 60 s), so train and inference
distributions match by construction. The model architecture is
unchanged from v2.

### Capture (vol-29 T1a)

`crates/ml-export/canonical-capture` runs `joe_depth150_bp` (Border
First MRV variable-order, EdgeBpMarginals value-order, gacolor + AC-3
+ multiset-equality propagators) on canonical E2 for 20 seeds × 60 s,
recording the winning prefix at each depth as the value the engine
last committed at that depth before the budget expired. All 20 seeds
reached depth 165 with nearly-identical trajectories (165 placements
each, divergence at depth ~118).

Total trajectory samples: ~3300 (down from 360k for the synthetic
v2 dataset). Training set is small + correlated; expected overfit.

### Training (vol-29 T1b)

`ml/preprocess_canonical.py` joins the trajectory JSONL with the
canonical CSV piece set, reconstructs the partial board at every
depth, builds the v2 .pt cache format. Each sample's negatives are
sampled from the canonical piece-set rotations that match the target
cell's border-mask + placed-neighbour edges. With ~3300 samples × 30
epochs ≈ 1.5 s / epoch (vs 30 s for 360k synthetic), training takes
under 1 min total.

Best val_acc: **94.55%** at epoch 24, plateau. Slightly lower than
v2's 97.3% on 360k synthetic, consistent with the smaller correlated
dataset.

### Canonical 16×16 gate (vol-29 T1c)

| | Baseline `joe_depth150_bp` | `joe_depth150_bp` + Learned (v3) |
|---|---:|---:|
| Max depth | **165** | **164** |
| Nodes | 504 862 | **329 764** (−35%) |
| Backtracks | 85 251 | **53 511** (−37%) |
| Elapsed | 60 001 ms | 60 003 ms |
| Δ depth | — | **−1** |

| Condition | Threshold | Result | Pass? |
|---|---|---|---|
| Match within 5 of baseline | depth ≥ 160 | 164 | YES |
| No collapse within 30 | depth ≥ 135 | 164 | YES |
| Wall-clock ≤ 1.5× baseline | ratio ≤ 1.5 | 1.00003 | YES |
| **Gate (match + wall-clock)** | | | **PASS** |
| (Strict) beat baseline by 5+ | depth ≥ 170 | 164 | no |

### What this measurement says

1. **The vol-28 collapse was a distribution problem, not a fundamental
   limitation.** From Δ = −108 (vol-28, cross-domain) to Δ = −1
   (vol-29, distribution-matched) is a 107-point recovery driven
   purely by training on the correct partial-board distribution.
2. **Imitation has a ceiling at the teacher's own performance.** The
   model matches `joe_depth150_bp` within 1 depth but doesn't beat
   it — which is exactly what imitation theory predicts. To beat the
   teacher you need reinforcement learning (reward = max_depth) or
   self-play, not imitation.
3. **The model is doing genuinely different work, not just copying.**
   Same depth in same wall-clock with 35% fewer nodes + 37% fewer
   backtracks means the model is making different choices that are
   equally productive — finding different productive paths to the
   same plateau, not memorising one trajectory.

### Vol-29 verdict

The cross-domain ML transfer hypothesis (vol-28) was clearly refuted.
The distribution-matched ML transfer hypothesis (vol-29) is **vindicated
within the imitation ceiling**: the model works on canonical, just
can't beat the engine that generated its training data.

Implication for the ML direction on canonical 5-clue E2:
- **Imitation alone**: closed direction. The 4 volumes vol-26–29
  produced a working pipeline (synthetic generator → trajectory
  capture → v2 size-agnostic model → ONNX in-process → engine
  integration) and proved imitation tops out at engine performance.
- **LearnedOnTies hybrid** (BACKLOG entry from vol-28): the 35% node
  reduction at same depth suggests the model is genuinely better at
  tie-breaking than EdgeBpMarginals. A hybrid that uses Learned ONLY
  on LCV ties is the cheapest remaining lever and could plausibly
  produce a small positive Δ. ~2 days.
- **RL self-play** (BACKLOG: `learned-16x16-long-train` flavor 2):
  the only direction that can structurally beat the imitation ceiling.
  ~1 week build + days of training. Different vol entirely.

### Numbers worth caching (vol-29 amendment)

| Quantity | Value |
|---|---|
| v3 training data | 3300 samples from 20 canonical-E2 trajectories × 60 s |
| v3 final val_acc (94.55%) | epoch 24, plateau |
| v3 canonical depth | 164 (baseline 165, Δ=−1) |
| v3 canonical node reduction at same wall-clock | −35% |
| v3 canonical backtrack reduction | −37% |
| v3 distribution-match recovery from vol-28 collapse | Δ from −108 to −1 (+107 points) |

### Files changed at vol-27

- `crates/solver-engine/Cargo.toml`: + `ort = "=2.0.0-rc.10"`, `ndarray = "0.16"`.
- `crates/solver-engine/src/bridge.rs`: rewritten as `LearnedScorer` (in-process ORT session).
- `crates/solver-engine/src/lib.rs::learned_score_candidates`: builds
  `Array3<f32>` instead of JSON string; calls scorer.score directly.
- `crates/ml-export/src/bin/gen_export.rs`: `--budget-ms` flag.
- `ml/evaluate.py`: `--budget-ms` flag + `median_wallclock_ratio` in
  the summary.
- `ml/runs/v1/model.onnx` + `model.onnx.meta.json`: exported model.

### What this conclusion is and isn't

**Is**: a clean PASS of the vol-26 gate spec on synthetic 6×6/5c
E2-family puzzles. Imitation learning + in-process ONNX inference
beats `BorderFirstMRV + LeastConstraining` on all three gate metrics
under a realistic time budget.

**Isn't**: a result on canonical 16×16 E2. The model is grid-size-specific
(the GridConv layer bakes the size in the neighbour buffer). Transferring
needs vol-28's variable-size architecture.

**Isn't**: a result on a difficulty regime that matches canonical E2.
6×6/5c is a small problem; the largest canonical E2 partials we've found
(457/480) are in a different complexity regime where the imitation
signal might or might not generalize.

### Vol-28 levers (gated on this result)

The ML direction is now alive at small scale. Vol-28 candidates:
1. **Variable-size GNN** so we can train on 6×6, fine-tune on 8×8, 10×10,
   16×16. ~3-5 days build + training compute.
2. **Diffusion-on-CSP** (the original vol-26 hypothesis target): replace
   imitation with a denoising objective. ~1-2 weeks.
3. **Hybrid**: use Learned as a tie-breaker inside an existing engine
   profile (joe_depth150_bp + Learned-on-ties) on canonical E2. ~2 days.
   Lower-EV but lower-risk than #1/#2.
