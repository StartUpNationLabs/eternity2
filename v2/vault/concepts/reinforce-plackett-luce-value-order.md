# REINFORCE via Plackett-Luce on engine value-order

**Status**: `partial` — math drafted, infrastructure probe revealed
the cheap "no engine change" path is dead (vol-50, 2026-05-15).
Engine-side `LearnedStochastic` build is the correct path but not
shipped.

## Vol-50 quick probe — Gumbel-via-ONNX-noise dead end

Hypothesis: wrap the Learned ONNX model with `z + T*Gumbel` noise
INSIDE the model (using ONNX `RandomUniformLike`), to get a stochastic
policy without modifying the engine.

Measurement (2026-05-15):
- Built `gumbel_perturb.py` wrapping `PositionRelativeModel`.
- Re-exported with `torch.rand_like` + Gumbel transform.
- Confirmed: `RandomUniformLike` exports without a seed attribute.
- Ran 5× `run_learned` on canonical-E2 at 8s budget, identical engine
  seed: ALL 5 RUNS GAVE IDENTICAL `matched=275 placed=167`.
- ORT's RandomUniformLike with no seed produces deterministic output
  across calls within a single session. Engine-side gets the same
  noise every step.

The "no engine change" path is dead. Engine-side `LearnedStochastic`
build is the only correct path forward.

## Origin
Vol-50 (2026-05-15), as alternative to vol-48/49 ES.

## The setting

At each placement step `t`, the engine considers `K_t` candidate
rotations for the current cell. The Learned scorer outputs scalar
scores `z_t = (z_{t,1}, …, z_{t,K_t})` and the engine sorts them
descending; the engine tries candidates in this order during DFS.

Vol-48/49 attempted to learn `z` via ES on the model parameters. The
failure mode: small perturbations to `z` rarely flip the argmax, so
most ES samples produce identical engine trajectories.

## Stochastic relaxation via Gumbel-noise

If we sample `g_{t,i} ~ Gumbel(0, 1)` iid and feed `s_{t,i} = z_{t,i} + T·g_{t,i}`
to the engine, then `argmax_i s_{t,i}` is a sample from the categorical
distribution `softmax(z_t / T)`. (Gumbel-Max trick.)

Extending: sorting `s_t` descending samples from the **Plackett-Luce**
distribution over permutations of `{1, …, K_t}` parametrized by
`softmax(z_t / T)`.

This is the key insight: **without changing the engine, we can convert
the deterministic argmax-sort policy into a stochastic Plackett-Luce
policy** simply by adding Gumbel noise to the model's outputs at
inference time.

## Log-probability of an observed trajectory

Let the engine's chosen permutation at step `t` be `π_t = (π_{t,1}, …, π_{t,K_t})`
(so `π_{t,1}` is the rotation tried first, etc.).

The Plackett-Luce log-prob is:

```
log P(π_t | z_t) = Σ_{k=1..K_t-1} [ z_{t,π_{t,k}} / T  −  logsumexp_{j ∈ {π_{t,k}, …, π_{t,K_t}}}(z_{t,j} / T) ]
```

This is fully differentiable in `z_t` (and hence in the model's
parameters via backprop). Crucially, it does NOT depend on the engine —
the engine is just the sampler.

## REINFORCE step

For an episode with steps `1, …, T_ep` and terminal reward `R` (e.g.
matched-edge count at episode close):

```
loss = − Σ_{t=1..T_ep} log P(π_t | z_t) · (R − b)
```

where `b` is a baseline (mean R across the current batch of episodes).

Gradient step:

```
θ ← θ − η · ∂loss/∂θ
```

## Why this avoids the ES collapse mode

ES gradient: `∇θ ≈ Σ_i (R_i − R̄) · ε_i / σ²`, where `ε_i` is the
parameter perturbation. The gradient vanishes when `R_i = R̄` for all
i, which happens when most perturbations produce identical episodes
(vol-48/49 collapse).

REINFORCE gradient: `∇θ = (R − b) · ∇θ log P(π | z(θ))`. The
`∇θ log P` term comes from backprop through the score network and is
**non-zero by construction** whenever the policy is non-deterministic
(T > 0). It does not require multiple parameter perturbations.

## What we need to build

1. **Per-step trajectory logging**: extend `crates/rl-search/run_learned`
   to dump JSONL of `(cell, candidates_in_input_order, chosen_permutation_indices)`
   per step. Roughly 50 lines of Rust.
2. **Score-snapshot**: also dump the model's raw scores `z_t` at each
   step. Either by hooking into the ONNX inference path inside the
   engine, OR by recomputing them in Python from the trajectory states.
   The latter is cleaner but requires a state→features helper in
   Python.
3. **PL log-prob computation** in PyTorch (5 lines).
4. **REINFORCE training loop** (~30 lines).

## Risks

1. **High-variance gradient.** REINFORCE is famously high-variance
   for long episodes; canonical-E2 episodes have ~250 steps. Variance
   reduction (baseline subtraction, possibly value-baseline / A2C
   later) is mandatory.

2. **Reward sparsity.** Reward is only at episode close. The
   credit-assignment problem is hard. Mitigation: per-step shaping
   `r_t = pieces_placed_at_t − pieces_placed_at_{t−1}` (cheap; biases
   the gradient but provides density).

3. **6×6 gate may not measure anything useful.** vol-26 showed
   imitation already gives 540× node reduction at 6×6; little
   headroom for REINFORCE. The gate that actually matters is
   canonical 16×16/22c.

## Linked

- [[learned-value-order]]
- [[rl-es-pipeline]] — refuted predecessor (vol-48/49)
- [[../sessions/vol-50]] — vol-50 session

## Open questions before building

- Is the Plackett-Luce log-prob NUMERICALLY STABLE at large `K_t`
  (canonical 16×16 has up to ~764 rotations at top of search)?
  Naive logsumexp over 764 terms should be fine in float32.
- Is `T` (temperature) trainable? Start with `T=1.0` constant.
- Can we use multiple actions per step (action = top-N rotations)
  to get richer log-probs? Probably yes; defer until vanilla REINFORCE
  fails.
