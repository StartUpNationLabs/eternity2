# Vol-48 — RL self-play via Evolutionary Strategies (negative result)

**Theme**: Pivot from vol-47's lifted-LP path (also negative) to RL.
Use evolutionary strategies (ES) to bypass the engine's lack of
per-step trajectory hooks. Build infrastructure, run training, see
if it can beat the vol-29 imitation ceiling.

**Status**: closed with **documented negative result**. Infrastructure
shipped, training failed cleanly. ES is not the right algorithm for
E2 value-ordering.

## What was shipped

### Infrastructure (working)

- **`crates/rl-search`** — new crate. `Episode`, `EpisodeStep`,
  `EpisodeOutcome` types. `ValueOrderPolicy` trait. `RandomPolicy`
  baseline. Tests pass.
- **`crates/rl-search/src/bin/run_learned`** — Rust bin that drives the
  engine with `ValueOrder::Learned` via `E2_LEARNED_MODEL` env var.
  Outputs one-line JSON with outcome.
- **`ml/es_perturb.py`** — load .pt model, add Gaussian noise, save
  perturbed ONNX. Verified round-trip with engine.
- **`ml/es_round.py`** — one ES round: N perturbations, parallel
  episode runs, reward collection, parameter update.
- **`ml/es_train_loop.sh`** — multi-round driver.

### Training run

4 rounds × 8 perturbations × 60s budget × 4 parallel.
Sigma=0.2, lr=0.05, reward=matched.

| Round | Mean | Std | Max | Notes |
|---|---:|---:|---:|---|
| R1 | 277.38 | 0.99 | 280 | weak signal (1/8 above mean) |
| R2 | 278.12 | 1.45 | 280 | slight gain |
| R3 | 277.00 | **0.00** | 277 | collapsed |
| R4 | 277.00 | **0.00** | 277 | frozen |

**Net effect**: trained model is WORSE than vol-29 base (277 vs 282 / 480).

## Why ES failed

### 1. Discrete argmax action selection

The engine's `ValueOrder::Learned` ranks candidates by the model's
output and picks the **argmax**. Small perturbations to the model's
scores rarely shift the argmax unless they're near a rank boundary.

**Consequence**: most perturbations produce identical engine
behavior → identical episode trajectories → identical rewards →
zero gradient signal.

The empirical evidence: R3/R4 had std=0.00 across 8 perturbations.
That's not noise; that's structural invariance.

### 2. Sigma calibration is brittle

- σ=0.05: no perturbation effect (all 8 episodes identical).
- σ=0.5: perturbations too large, becomes random search noise.
- σ=0.2: worked for R1-R2, then collapsed in R3.

The sigma value at which perturbations produce useful signal **moves
during training** — the policy concentrates probability mass on
specific actions, so a perturbation that was "in the productive
range" at start becomes "below the rank-flip threshold" later.

### 3. Sparse discrete reward

Reward = matched edge count, an integer in [0, 480]. Variance
across 8 perturbations at the same training point is typically
0-3 edges. The gradient estimate from this is dominated by
discretization, not policy change.

## Alternative paths considered

### Direct REINFORCE / PPO

Requires per-step log-probability exposure. Engine doesn't natively
provide this — `LearnedScorer::score()` returns score vectors, engine
picks argmax with no log-prob plumbing. **Modifying engine internals
to expose this is multi-day work** and risks breaking the existing
ValueOrder::Learned path.

### Q-learning / value-function approach

Learn Q(state, action) → choose action by argmax Q. Gradient-based
update on Q values from observed rewards. Need state representation
that the engine can score against; already have one (ONNX bridge).
**Not broken by argmax discreteness** because the gradient is on
Q-values, and argmax is just inference.

### Population-based training (PBT)

Run K policies in parallel, periodically copy parameters from
best-performing to worst-performing + small noise. Doesn't depend on
fine-grained reward signal. Might work better than ES.

### Imitation from BETTER teacher

Vol-29's imitation hit the teacher ceiling. If the teacher is
the engine itself, we hit engine performance. To beat engine, we'd
need to imitate **stronger search trajectories** — e.g., longer
MIP runs or community 469 board reconstructions. The trajectories
are sparse but each is highly informative.

## Files

- `crates/rl-search/` — RL infrastructure (shipped).
- `ml/es_perturb.py`, `ml/es_round.py`, `ml/es_train_loop.sh` — ES scripts.
- `ml/runs/es_run_001/` — failed training run (R1..R4).
- `output/vol-48_es/run_001.log` — full training log.

## Verdict

Vol-48 produced **two outputs**:

1. **Working ES infrastructure** that can drive the engine from
   Python with any ONNX model. Reusable for future RL experiments.
2. **A documented negative result**: ES does not converge on E2
   value-ordering due to the discrete action structure.

For future work the natural next experiment is **Q-learning** with
gradient-based Q-value updates from observed episode rewards. The
Q-network would be the candidate-ranking network; training directly
on observed reward signal avoids the ES collapse mode.

## Linked

- [[learned-value-order]] — vol-26..vol-32 imitation context
- [[rl-self-play-value-order]] — original RL design (PPO path)
- [[rl-es-pipeline]] — ES design (this session's path)
- [[vol-47]] — predecessor (lifted-LP, also negative)
- [[parallel-night-session-findings]] — parallel agent's work
