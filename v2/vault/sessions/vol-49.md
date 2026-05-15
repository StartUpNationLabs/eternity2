# Vol-49 — Adaptive-sigma ES (second ES negative result)

**Theme**: Vol-48's vanilla ES collapsed to std=0 by R3 with sigma=0.2.
Hypothesis: adaptive sigma that bumps when std drops below threshold
could rescue ES.

**Status**: closed. Adaptive ES is **better than vanilla but still fails
to beat the imitation baseline**. Documented negative result.

## What was built

- `ml/es_train_adaptive.sh` — multi-round driver with adaptive sigma:
  if std < MIN_STD (default 0.5), multiply sigma by SIGMA_BUMP_FACTOR
  (default 2.0), capped at SIGMA_MAX (default 1.0). Detects collapse
  and increases perturbation magnitude.

## Training trajectory (6 rounds, N=8 per round, 60s episodes)

| Round | Sigma | Mean | Std | Max | Note |
|---|---:|---:|---:|---:|---|
| R1 | 0.2 | 278.88 | 1.55 | 280 | |
| R2 | 0.2 | 279.62 | 1.06 | 280 | slight gain |
| **R3** | 0.2 | **280.00** | **0.00** | 280 | peak, then collapsed |
| R4 | 0.4 | 280.00 | 0.00 | 280 | bump doesn't break plateau |
| R5 | 0.8 | 278.12 | 1.55 | 280 | bigger sigma destabilizes |
| R6 | 0.8 | 278.88 | 1.45 | 280 | partial recovery |

## Findings

### F1. Adaptive ES improves over vanilla ES

Vol-48 vanilla ES collapsed at 277. Vol-49 adaptive ES reached 280.
**+3 over vanilla**, real but small.

### F2. The 280 ceiling is reached but not exceeded

R3 hit 280 mean. Subsequent rounds with bigger sigma (0.4, 0.8) did
NOT find new directions above 280 — they just made the variance bigger
while sometimes lowering the mean.

### F3. Sigma bumping has a fundamental trade-off

- Small sigma: low variance, fast convergence, easy collapse.
- Large sigma: variance recovers but pure noise dominates the
  update direction.

There's no sigma that simultaneously (a) maintains signal AND
(b) avoids collapse over many rounds.

### F4. Both ES variants end BELOW imitation baseline

vol-29 imitation baseline on the same engine setup: 282.
Vanilla ES (vol-48): 277.
Adaptive ES (vol-49): 280 peak, 278.9 final.

**The ES updates DEGRADE the model relative to its imitation starting
point.** Both ES variants are net-negative training, not net-positive.

### F5. The argmax-discreteness obstruction is FUNDAMENTAL on E2

Even with adaptive sigma, the engine's discrete action choice
(argmax over candidate scores) means most parameter perturbations
produce identical episodes. The std=0.00 rounds at sigma=0.2 (R3)
AND sigma=0.4 (R4) prove this isn't a calibration issue —
it's a structural property.

The only way to get fine-grained gradient signal would be a
**stochastic policy** (softmax with temperature). Engine doesn't
expose this.

## Verdict for ES on E2 value-ordering

**ES is not the right algorithm.** Both vanilla and adaptive variants
fail in the same fundamental way: the action space is discrete, the
search behavior is highly invariant to small parameter perturbations,
and large perturbations destroy the policy quality.

## Alternatives for next session (vol-50)

1. **Q-learning** (still recommended from vol-48 close). Train
   Q-values directly on observed reward. Argmax invariance doesn't
   break gradient estimation because gradient is on Q-values.

2. **Modify engine to expose stochastic policy hook**: add
   `ValueOrder::LearnedStochastic` that uses softmax-temperature
   sampling instead of argmax. Enables proper REINFORCE/PPO with
   gradient signal.

3. **Different teacher for imitation**: vol-29 imitated the engine
   itself (ceiling=engine). Imitate stronger trajectories from
   community 469 boards or multi-hour MIP runs. Could exceed engine
   performance via imitation alone.

## Linked

- [[vol-48]] — vanilla ES negative result (predecessor)
- [[learned-value-order]] — vol-26..vol-32 imitation context
- [[rl-es-pipeline]] — original ES design
