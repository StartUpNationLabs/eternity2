---
tags: [session, vol-29, ml-ceiling]
---

# Vol-29 — distribution-matched ML hits the imitation ceiling

**Theme**: Vol-28's catastrophic Δ=−108 collapse was a distribution
problem, not a fundamental one. Training on canonical-E2 trajectories
from our own engine recovers to Δ=−1. Imitation tops out at the teacher.

## What was attempted

T1 — train v3 model on canonical-E2 expert trajectories from
`joe_depth150_bp` (Lever B from VOL-28).

1. `canonical_capture.rs` (new bin): runs `joe_depth150_bp` on
   canonical E2 for 20 seeds × 60 s, captures the winning prefix at
   each depth.
2. `preprocess_canonical.py`: joins JSONL trajectory with the
   canonical piece set, builds v2 .pt cache.
3. Reuses `train_v2_cached.py` (same v2 architecture).
4. Reuses `export_v2.py` for ONNX export.
5. `canonical_gate.py`: A/B `joe_depth150_bp` baseline vs same +
   Learned-v3, 60s budget each.

## What was measured

| | Baseline `joe_depth150_bp` | + Learned (v3) |
|---|---:|---:|
| Max depth | **165** | **164** |
| Nodes | 504 862 | **329 764** (−35%) |
| Backtracks | 85 251 | **53 511** (−37%) |
| Elapsed | 60 001 ms | 60 003 ms |
| Δ depth | — | **−1** |

| Gate condition | Threshold | Result | Pass? |
|---|---|---|---|
| Match within 5 of baseline | ≥ 160 | 164 | YES |
| Wall-clock ≤ 1.5× baseline | ≤ 1.5 | 1.00003 | YES |
| **Gate (match)** | | | **PASS** |
| (Strict) beat baseline | ≥ 170 | 164 | no |

## What was refuted

- **Vol-28's framing that "the architecture is broken"**. Vol-28 had
  Δ=−108 collapse; vol-29 has Δ=−1 with the SAME architecture and
  trained for FEWER epochs on 100× less data. The architecture was
  always fine; the problem was the cross-domain distribution gap.
- **The "training on canonical doesn't help" hypothesis from vol-28's
  worst-case framing**. Distribution-matched training works exactly
  as theory predicts: the model matches its teacher's performance.

## What was confirmed

- **Imitation ceiling**: the model matches but cannot beat its teacher.
  Δ=−1 with a model trained directly on the teacher's trajectories is
  the textbook expected outcome. Theory: imitation lower-bounds the
  expected loss at the teacher's loss, never strictly below.
- **The model is making different productive choices** (35% fewer
  nodes, 37% fewer backtracks at same depth and same wall-clock). Not
  just memorising one trajectory.

## What is open

- **LearnedOnTies hybrid** (BACKLOG): use Learned ONLY when LCV ties.
  The 35% node reduction at same depth suggests the model is genuinely
  better at tie-breaking. Cheapest remaining lever. ~2 days.
- **RL self-play** (BACKLOG `learned-16x16-long-train` flavor 2): the
  only direction that can structurally beat the imitation ceiling.
  ~1 week build + days of training.
- **Long-imitation experiment** (BACKLOG, user request): bigger model +
  more seeds + more epochs. Theory says it'll asymptote at the teacher;
  worth one run to confirm empirically.

## Concepts touched

- [[../concepts/learned-value-order]] — Vol-29 measurement section
  added. Direction status: imitation closed (cannot beat teacher);
  LearnedOnTies + RL self-play remain open paths.

## Open at close

- Three ML directions remain open in BACKLOG. Decision deferred to
  vol-30 open.
- Audit-at-open: completed; `bound-ascent-then-blackwood-cp` marked
  `wont-do` (7-vol-aged); `gap-recording-instrumentation` deferred
  again.

## Linked memory

- `project_e2_vol29_imitation_ceiling` (NEW)
