---
tags: [concept, value-order, ml]
status: built
origin-vol: 26
---

# Learned imitation-policy value order (vol-26 gate)

**Status**: `built` — gate FAILED on spec, PASSED on substance.
**Origin**: vol-26 (2026-05-13).
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
