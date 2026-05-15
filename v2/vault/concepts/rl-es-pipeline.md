# RL via evolutionary strategies (ES) — pipeline design (vol-48)

**Status**: design, replacing the REINFORCE plan from
`rl-self-play-value-order.md` because the engine doesn't expose
per-step trajectory hooks.

**Why ES instead of PPO/REINFORCE**: gradient-based RL needs
per-step log-probabilities of the chosen action. Our engine calls
the policy as a black-box scorer (ONNX inference returns scores
per candidate; engine picks max — no log-prob exposure). To get
log-probs we'd need to modify engine internals (multi-day work
and risk).

**ES bypasses this**: optimize the policy parameters $\theta$
using only the FINAL reward (depth or score reached). No per-step
info needed. Compatible with any black-box policy.

## Algorithm (OpenAI-ES style)

```
Initialize θ_0 (warm-start from vol-29's imitation model)
for round = 1, 2, ...:
    sample N noise vectors ε_1, ..., ε_N from N(0, σI)
    for i = 1..N:
        θ_i = θ_0 + ε_i
        export θ_i to ONNX
        run engine with E2_LEARNED_MODEL=θ_i.onnx
        record R_i = depth or score reached
    compute centered rewards (R_i - mean(R)) / std(R)
    θ_0 = θ_0 + (lr / (N · σ)) · Σ_i (R_i - mean) · ε_i
    save checkpoint
    optionally eval on held-out canonical CP runs
```

Each round: N=20 episodes × 60s each = 20 min (parallelizable across
cores). Days of rounds → millions of parameter updates.

## Implementation plan

### Step 1: ONNX round-trip with vol-29's model

- Load vol-29 model in PyTorch.
- Export to ONNX with grid-size/piece-count parameters baked in.
- Verify engine accepts it (E2_LEARNED_MODEL env var).
- Verify engine runs end-to-end and reports depth/score.

### Step 2: parameter perturbation script

- Python script that:
  - Loads base θ from .pt or .onnx.
  - Adds Gaussian noise to selected layers.
  - Saves perturbed ONNX.
- Engine runs the perturbed model.

### Step 3: episode runner (Rust or Python)

- For a given ONNX model path, run engine for B ms budget, capture
  final outcome.
- Outputs: depth, matched, elapsed.
- Cron-friendly so we can run hundreds in parallel.

### Step 4: ES update

- After N episodes, compute the gradient estimate.
- Apply update with momentum / Adam-style.
- Save checkpoint.

### Step 5: training loop

- Round-trip through 1, 2, 3, 4 indefinitely.
- Eval every K rounds.

## Compute budget

- Per episode: 60s wall-clock.
- Per round: 20 episodes × 60s = 20 min (or 5 min if parallelized 4×).
- Per day: ~70 rounds = ~1400 parameter updates.
- 1 week: 10000 updates. Sufficient for ES on a few-million-param net.

## Risk

- ES is slow to converge (no gradient info). Expect to need days
  of training for any visible improvement.
- Warm-start from imitation model gives a head-start.
- The reward signal (final depth) is sparse: most episodes will
  have similar depth (engine's baseline 165). The variance comes
  from rare hits with better policies.

## Linked

- [[rl-self-play-value-order]] — original PPO/REINFORCE design
  (deferred due to engine-hook complexity)
- [[learned-value-order]] — vol-26..vol-32 imitation context
- [[vol-48]] — session
