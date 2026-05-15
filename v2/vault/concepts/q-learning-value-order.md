# Q-learning for E2 value-ordering

**Status**: `unbuilt` — vol-50 binding item (2026-05-15).
**Origin**: vol-50, as response to vol-48/49 ES-collapse diagnosis.

## Definition

Instead of training a policy network whose argmax is used as the
engine's `ValueOrder::Learned` choice (vol-26..vol-29 imitation) and
trying to update the policy parameters via ES (vol-48..vol-49,
refuted), train a Q-network that **estimates the value of each
(state, candidate) pair** and let the engine continue to argmax over
the network's outputs.

The crucial difference: the gradient target during training is the
**Q-value**, not the argmax. Q-values move continuously with parameter
updates even when the argmax is structurally invariant. This sidesteps
the vol-48/49 collapse mode (in which most ES perturbations produced
identical engine trajectories because the argmax of the perturbed
network coincided with the unperturbed one).

## Why this isn't the same as vol-29 imitation

Vol-29 trained on **(state, expert_action)** with cross-entropy loss.
The model imitates the engine — ceiling = engine's own behaviour.
This is what produced the Δ=−1 ceiling result.

Q-learning trains on **(state, action, reward, next_state)** using TD
target. The supervised signal is observed reward (engine's actual
solve quality), not expert action. The model can in principle
identify candidates that produce higher rewards than the expert's
own choices — which is the bare-minimum requirement to beat the
imitation ceiling.

## What this isn't

- **Not vol-48 ES**: gradient is on Q-values via standard backprop, not
  Gaussian noise + reward-weighted average.
- **Not Direct REINFORCE / PPO**: no log-probability plumbing through
  the engine. Engine still does argmax; only the scorer is learned.
- **Not Imitation**: training signal is reward, not expert action.

## TD-target formulation (concrete)

For trajectory `(s_1, a_1, r_1), …, (s_T, a_T, r_T)`:

```
Q_target(s_t, a_t) = r_t + γ · max_{a' ∈ cand(s_{t+1})} Q(s_{t+1}, a')
```

with `r_T` = matched-edge count at episode close (terminal reward) and
intermediate `r_t` = 0 (option: shaping reward = `pieces_placed_at_t -
pieces_placed_at_{t-1}` to densify, but adds bias).

Loss = `MSE(Q(s_t, a_t), Q_target(s_t, a_t))` over all `t` in a batch
of trajectories. Standard DQN-style replay buffer.

## Engine integration

`ValueOrder::Learned` already calls a scorer that returns a vector
of scores per candidate. The engine argmaxes. No engine change needed
for inference. The Q-net's output IS this score vector, interpreted
as Q(state, candidate) per candidate.

For training data collection, the engine needs to log:
- `state` representation at each placement step
- `cand(s_t)` (candidate set considered at that step)
- `a_t` (chosen candidate)
- `pieces_placed_after_step` (for shaping option)
- `matched_at_close` (terminal reward)

The vol-48 `crates/rl-search` infrastructure already collects
`EpisodeStep` records — needs an extension to log full candidate
sets (currently logs only the chosen action).

## Open questions before build

1. **State representation**: vol-29 v3 uses position-relative GNN
   features built from the board's filled cells. Q-net can reuse
   this exactly — only the head changes (scalar Q instead of
   classification logit).
2. **Discount γ**: Sparse-reward problems often use γ ≈ 0.99 to
   propagate terminal reward back. Choose γ ∈ {0.9, 0.99, 1.0}.
3. **Replay buffer size**: vol-29 had ~3300 samples from 20 episodes
   × 60s. Q-learning typically needs more. Plan 5000-10000
   transitions.
4. **Exploration policy** during training: ε-greedy on top of argmax(Q)
   is standard. Schedule ε from 0.5 → 0.05 over training.

## Linked concepts

- [[learned-value-order]] — imitation predecessor
- [[rl-es-pipeline]] — ES variant (refuted vols 48-49)
- [[rl-self-play-value-order]] — original RL design

## Linked sessions

- [[../sessions/vol-48]] — ES vanilla
- [[../sessions/vol-49]] — ES adaptive
- [[../sessions/vol-29]] — imitation baseline (Δ=−1)
