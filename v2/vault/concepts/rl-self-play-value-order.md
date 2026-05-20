---
name: rl-self-play-value-order
description: vol-30 T2 confirmed +9 depth lift invariant across 3 model variants;
status: unbuilt
metadata:
  type: concept
---
# RL self-play for E2 value-order (vol-48 design)

**Status**: design phase.
**Origin**: vol-29 imitation hit teacher ceiling (Δ=-1 vs baseline);
vol-30 T2 confirmed +9 depth lift invariant across 3 model variants;
vol-32 LOT bug refutation shows imitation alone cannot beat baseline.
RL self-play is the only structural path past the imitation ceiling.

Authorized by user (2026-05-15): multi-day research direction
after vol-47 lifted-LP path produced documented negative results.

## Why RL, not more imitation

Vol-26..vol-31 explored imitation learning extensively:
- Vol-27: ONNX in-process inference, 6×6/5c gate PASS.
- Vol-28: cross-domain transfer REFUTED (6→16 doesn't work).
- Vol-29: distribution-matched training, Δ=-1 (within teacher's noise).
- Vol-30 T2: 3 model variants, all hit depth 174 invariant.
- Vol-32: discovered LOT bug, real lift only +0 depth.

**Imitation ceiling**: training on engine traces caps performance at
"what the engine already does" (vol-29 result). To exceed the
engine, the agent must EXPLORE actions outside the engine's
trajectory and DISCOVER better moves via reward signal.

RL self-play does exactly this. The agent plays, receives reward
(depth reached, edges matched, basin escape), and learns from its
OWN trajectories — including the SUCCESSFUL deviations from the
engine's default policy.

## Problem formulation

### State

A partial E2 board: (puzzle, hints, partial placement). Specifically:
- Cells placed so far: 0 ≤ k ≤ 256.
- Pieces remaining: 256 - k.
- Per-cell candidate domains: which (piece, rotation) are still
  feasible given placed neighbors.

### Action

At each step, the agent picks ONE (cell, piece, rotation) to place
next from the candidate pool. The cell is chosen by a fixed
variable-ordering (e.g., MRV) OR is also a policy decision.

For first cut: **fix variable-ordering to MRV/AC3** (the engine's
default) and let the agent choose only the VALUE (piece, rotation).
This matches vol-26..vol-32's setup (value-order policy).

### Transition

Place the chosen (piece, rotation) at the chosen cell. Propagate AC-3
constraint propagation through neighbors. If propagation succeeds,
move to next cell. If it fails (any cell has 0 candidates),
backtrack: revert and the agent must pick differently.

### Reward

Two reward variants:

**R1 — depth-based**: at episode end (either solved or backtracked
to root), reward = max depth reached during the episode.
**R2 — score-based**: at every leaf reached, reward = matched edges
on the (partial) board, scaled so leaves at depth 256 with score
458+ are highly preferred.

R1 is simpler, R2 is what we ultimately want (record-breaking
needs score, not depth).

### Episode end

- Solved (depth 256, all matched): reward = 480 (or normalized).
- Timeout (e.g., 60s or 100k nodes): reward = best depth reached.
- Exhausted (backtracked to root with no improvement): reward = -1
  (or fixed penalty).

## Architecture

### Policy network

Input: state encoding. Options:
- **Grid encoding**: 16×16 grid with per-cell features (piece-id
  one-hot or learned embedding, rotation, placed/unplaced flag).
  ~16 × 16 × 256 + bookkeeping. Vol-29's GNN style.
- **Candidate-list encoding**: for the current decision cell, the
  list of candidates (piece, rotation) with their score features
  (neighbor color match counts, edge BP marginals, etc.).
- **Hybrid**: grid context + candidate features. Best of both.

For first cut: **hybrid encoding**. Reuse vol-29's GNN architecture
but add a decision-head over candidates.

### Output

Policy: softmax over candidates at current cell. Sample action.

### Training

PPO (Proximal Policy Optimization) — standard for episodic RL with
discrete actions. Or REINFORCE for simplicity.

For first cut: **REINFORCE with baseline** (the engine's depth as
baseline). Simpler than PPO.

### Compute budget

Per episode: 1-10 sec (one CP solve attempt with the learned
value-order).
Per training round: 100-1000 episodes = ~few hours.
Total: 100k+ episodes over days.

## Implementation plan

### Phase A: scaffolding (days 1-2)

- New crate: `crates/rl-search` (or extend `learned-value-order`
  module from vol-27+).
- Episode runner: invoke `EngineSolver` with `ValueOrder::Custom`
  driven by a policy callback. Capture trajectory.
- Reward computation: from final outcome + intermediate scores.
- Trajectory replay buffer (collected episodes).

### Phase B: policy network (days 3-4)

- Reuse vol-29 GNN architecture as policy backbone.
- Add decision-head: scores candidates at current decision point.
- Use ONNX export for inference inside engine (like vol-27).
- Loss: REINFORCE log-prob × (reward - baseline).

### Phase C: training loop (days 5-7)

- Initialize from vol-29's imitation-trained model (warm start).
- Iterate: collect episodes → compute returns → policy update.
- Eval every N rounds on canonical 16×16/22c with engine.
- Save checkpoints.

### Phase D: production run (days 7+)

- Train for days against canonical-E2.
- Eval periodically.
- Goal: depth > teacher (165) AND score > 458 in CP completion.

## Open questions

- **Where to run training compute**? 8-core Mac will be slow.
  Cloud GPU? Or accept slow training.
- **How to bridge to engine's CP value-order?** Engine already
  supports `ValueOrder::Learned` (vol-27 ONNX bridge); reuse it.
- **What's the right reward shaping?** Score-based may have sparse
  reward (most episodes are far from 458). Depth-based has denser
  signal but doesn't directly maximize the target.
- **Should we explore the variable-order axis too?** Current vol-29
  fixed MRV; RL could choose variable too. More expressive but
  bigger action space.

## Risk / outcome assessment

**Best case**: RL escapes imitation ceiling, reaches depth 200+
or score 462+ at CP completion. Real record break candidate.

**Likely case**: incremental lift over imitation (e.g., depth 170
from 165). Useful but not record-breaking.

**Worst case**: RL doesn't converge or shows no improvement over
imitation in available compute. Negative result, similar to vol-47.

## Linked

- [[learned-value-order]] — vol-26..vol-32 imitation work
- [[lp-ub-478-basins]] — basin landscape this RL would navigate
- [[vol-29]] — imitation ceiling reached
- [[vol-30]] T2 — long-imitation hits +9 invariant
- [[vol-32-bug-discovery]] — LOT bug refutation
