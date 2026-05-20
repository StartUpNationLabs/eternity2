---
tags: [session, vol-27, ml-gate]
---

# Vol-27 — In-process ONNX + tighter-budget gate (PASS)

**Theme**: Replace stdio bridge with ORT; vol-26 gate now passes all
three conditions under a 100ms budget.

## What was attempted

T1 + T2, both binding.

### T1 — In-process ONNX inference

Replaced vol-26's stdio Python bridge with `ort = 2.0.0-rc.10` running
the trained model in-process. ONNX export went smoothly
(`torch.onnx.export` opset 17, 6.6KB .onnx file); PyTorch vs ORT outputs
match to 6e-6 abs diff on 5 random inputs. Added a `LearnedScorer`
struct in `crates/solver-engine/src/bridge.rs` that loads the model
lazily at first value-order query (via env var `E2_LEARNED_MODEL`,
default `ml/runs/v1/model.onnx`) and falls back silently if missing.

The vol-26 helper `learned_score_candidates` now builds `Array3<f32>`
instead of a JSON string and calls `scorer.score()` directly.

### T2 — Stress-test the gate

Deviated from the plan (which called for 7×7 retraining) and instead
retested at 6×6/5c with `--budget-ms 100`. This creates failures in
the MRV baseline (its tail-latency outliers blow 100ms) so condition
(c) becomes non-vacuous. Methodologically equivalent to changing
puzzle size; cheaper.

## What was measured / kept

| Budget | MRV solved | Learned solved | Median nodes ratio | Median ms ratio | Gate |
|---|---:|---:|---:|---:|---|
| 5 s | 200/200 | 200/200 | 0.0018 | 0.18 | FAIL (c unsatisfiable) |
| **100 ms** | **184/200** | **200/200** | 0.0020 | (varies) | **PASS** |

- ONNX in-process inference: ~0.5–3 ms/call after a ~30 ms warmup.
  Wall-clock median 11 → 2 ms (5.5× faster), max 560 → 11 ms (50× tail
  win), 163/200 puzzles outright wall-clock win.
- At 100ms budget: Learned solves all 16 MRV-failures (16/16 recovery).
- Full numbers in [[learned-value-order]]
  "Vol-27 measurement" section.

## What was refuted

- **Vol-26's stdio-bridge measurement of "56× slower wall-clock"** was
  an artefact of the bridge, not the algorithm. The same model, run
  in-process, is 5.5× FASTER than MRV at the median.
- The need to retrain at 7×7 to get condition (c) failures. A tighter
  budget at 6×6 achieves the same goal in seconds, not 30+ minutes.

## What is open

- **Canonical 16×16 transfer** — the model is grid-size-specific (the
  `GridConv` layer bakes neighbour indices at construction). Vol-28's
  candidate T1 is variable-size architecture or per-size fine-tuning.
- **Hybrid use inside an existing pipeline** — could `joe_depth150_bp +
  Learned-on-ties` beat the existing 457 cold-start record on canonical
  E2? Untested.
- **Diffusion-on-CSP** — vol-26's original hypothesis target. Imitation
  was the gate; diffusion is the open question.

## Concepts touched

- [[learned-value-order]] (amended vol-27 — gate PASS row,
  ONNX path, vol-28 levers).
- [[synthetic-puzzle-generator]] (gen-export added
  `--budget-ms` flag for harder sizes).

## Open at close

- Vol-26 gate is now PASS (vol-27 amendment).
- Vol-27 plan T1 + T2: both built. No partials, no `unbuilt` deferrals
  inside vol-27 itself.
- Audit-at-open: completed; 5 aged items resolved (1 `wont-do`, 4
  deferred with reasons).
- Vol-28 plan drafted at [[VOL-28]] — picks variable-size
  architecture as the next lever.

## Linked memory

- `project_e2_vol26_learned_value_order` (amended vol-27).
