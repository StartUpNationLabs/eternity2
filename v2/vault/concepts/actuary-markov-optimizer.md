---
name: actuary-markov-optimizer
description: "ACTUARY (vol-216 invention): Verhaard-class markov schedule optimizer. (depth, spent)-conditional fit statistics (fitstats2) -> branching-process DP over states (d, s) -> offline anneal over gate schedules -> race the computed schedule. Key math: depth-marginal rates TELESCOPE into an identity (no schedule signal; naive DP overestimated arrivals 2.3e5x) — the (d,s) split is the transferable content. Measured gate multiplier b1 ~ 20 children/open arrival vs b0 ~ 1."
status: partial
metadata:
  type: concept
---

# ACTUARY — markov schedule optimizer

**Origin**: vol-216 binding 1 = BACKLOG `verhaard-markov-schedule-
optimizer` (the most-credentialed unbought multiplier: Verhaard's
records used per-depth fit statistics + a Markov model over
(depth, slips) + offline schedule search, "thousands of combinations
per minute"). Absorbs `verhaard-order-optimization` (the DP evaluates
order × gates jointly once per-scan calibrations exist).

**Files**: `crates/cloister/src/dfs.rs` (`fit_y0/fit_y1/fit_starts/
fit_starts_open` + `fit2` (d,s)-block, `FIT2_S`), cloister2
`fitstats_*.tsv` (new columns) + `fitstats2_*.tsv` (state-conditional),
`scripts/v216_actuary/actuary.py` (fit / eval / optimize).

## Model

Break-DFS as a branching process over states $(d, s)$ = (scan depth,
breaks spent). From calibration counts:

$$b_0(d,s) = \frac{y_0(d,s)}{\text{starts}(d,s)},\qquad
  b_1(d,s) = \frac{y_1(d,s)}{\text{starts\_open}(d,s)}$$

DP for a candidate schedule $G$ ($G[s]$ = min depth for break $s{+}1$):

$$V(d{+}1, s) \mathrel{+}= V(d,s)\,b_0(d,s), \qquad
  V(d{+}1, s{+}1) \mathrel{+}= V(d,s)\,b_1(d,s)\,[d \ge G[s]]$$

$V(d_{\max}, \cdot)$ = expected exact-tail arrivals per epoch root by
spent; nodes $\approx \sum V$; objective = $\gamma^s$-weighted
arrivals per node.

## ★ The telescoping lemma (why depth-only fails)

With starts$(d{+}1) = y(d)$ (every arrival is its parent's placement —
verified EXACTLY in calibration: starts(145) = y0(144)+y1(144) =
147,473), the depth-marginal branching product telescopes:

$$\prod_{d=k_0}^{D-1} \frac{y(d)}{\text{starts}(d)}
  = \frac{y(D{-}1)}{\text{starts}(k_0)}$$

i.e. depth-marginal rates reproduce the calibration run's own
arrivals-per-root identically and carry **zero schedule-transferable
information**. Measured consequence: the depth-only DP predicted
2.0e6 arrivals/epoch where 8.86 were measured (×2.3e5) — the error is
the s-dependence of subtree productivity, compounded over 51 depths
(≈ +16%/depth). Conditioning on spent breaks the telescope; the
$(d,s)$ table IS the signal. (Verhaard's state space was also
(depth, slips) — convergent evidence.)

## Measured so far (config A: d146-seed63 pin, hand gates 133-182, et14, 120 s × 8)

- **Gate multiplier**: $b_1 \approx 20{-}22$ children per gate-open
  arrival vs $b_0 \approx 1$ — each gate is a ×20 tree multiplier;
  schedules trade survival (gates rescue walks at walls) against
  explosion (×20 mass each, paid in nodes).
- Measured throughput: 8.86 arrivals/epoch, 9.1e7 nodes/epoch,
  arrivals/node ≈ 9.7e-8.
- Config A reproduces the d146 basin (451 × 4/8 at 120 s — calibration
  doubles as another incumbent reproduction).

## Method discipline

- Coverage-aware DP: V-mass through unmeasured (d,s) cells is
  reported; candidate schedules trusted only at coverage ≥ 0.8
  (trust region). Iterative loop: race chosen schedule → pool its
  fitstats2 → refit → re-optimize.
- Instance starts (arrivals) are counted at instance START;
  `fit_visits` counts ENDS and is survivorship-biased at break depths
  (long-lived instances under-represented) — wrong denominator for
  branching rates.

## ★ Self-consistency achieved (vol-216, same day)

DP-predicted vs measured (config A, hand schedule): **8.99 vs 8.55
arrivals/epoch (5% error)**, nodes/epoch within 1.9× (different node
definitions), coverage 0.99999. The error ladder, each step a real
modeling lesson:

| model | predicted arrivals/epoch | error |
|---|---|---|
| depth-marginal rates | 2.0e6 | ×2.3e5 (telescoping lemma) |
| (d,s) + depth-marginal fallback | 4.1e5 | ×4.8e4 (cross-lane mixing) |
| (d,s) + lane-coherent fallback | 4.4e3 | ×520 (hint cells got free-cell b1≈20) |
| + forced-break lanes + y2 | **8.99** | **×1.05** |

Mechanisms found on the way (each verified by flow audits):
1. starts(d+1,s) = y0(d,s) + y1(d,s−1) + y2(d,s−2) holds EXACTLY in
   the corrected instrumentation (only the et-frontier row differs,
   by design).
2. Hint (forced) cells can pay cost 2 (both constraints wrong) — the
   y2 lane; and their break placements are per-arrival, not
   per-open-enumeration (b1_forced = y1/starts).
3. Fallback for unvisited (d,s) cells must stay IN-LANE (nearest d,
   same s; then more-spent same-d): depth-marginals hand healthy
   branching to lanes whose true dynamic is death at the wall.

## Open
- Optimize + race vs hand gates on d146 finish config (≥8 seeds,
  300 s, min/med/max) and on from-scratch hinted.
- Pool calibrations across schedules (A + C + jittered) for coverage.
- Scan-order axis: per-scan fitstats2 → joint (order, gates) search.

## Linked

[[ladder-prefix-racing]], [[reference-verhaard]],
[[assignment-lp-prefix-scoring]], session [[vol-216]]
