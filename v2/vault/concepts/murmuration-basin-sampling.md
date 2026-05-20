# Murmuration — Basin Sampling at Scale (V171)

Status: `partial` (V155 stochastic-beam built 2026-05-20; sweep pending V169 finish)
Origin: vol-171 (this volume), motivated by user observation 2026-05-20: "there can be 1000s of 460 if we look deep enough, being stuck on one is not really good news".
Files: `crates/bench-audit/src/bin/v155_weaving_prior.rs` (`--stochastic-temperature`), `scripts/v171_murmuration/run.sh`.

## Premise

The E2 score landscape has a **460-tier basin family**. Volumes 122 and 129 found 18 distinct corner-perms with boards score ≥ 458. Counting board orbits up to σ-equivalence, the 460-class is likely several orders of magnitude larger.

Standard ALNS attacks ONE basin at a time. Even when it works, it converges to a 460 (or 461 with luck). Vol-156 to vol-163 made this explicit: 16 seeds → 16 identical boards. We have ONE 460 sample, not 1000s.

V171 changes the question from "lift this 460" to "sample 460-basin geography and find the rare basin that breaks 460".

## The stochastic-beam math

V155 picks the top-K children at each depth. With deterministic tie-break, the entire trajectory is fixed by the prior and scan order. Adding seed-tiebreak is null because there are essentially no exact-score ties at K ≥ 256 (vols 162-163 confirmed empirically).

**Stochastic beam (Gumbel-top-K).** At each depth, instead of sorting children by combined score $u(c) = \text{score}(c) + \alpha \cdot \text{prior}(c)$, sample K-without-replacement from $\mathrm{softmax}(u / T)$. The standard trick: add iid Gumbel(0,1) noise to each $u(c) / T$ and take top-K under the perturbed key.

**Why Gumbel-top-K**:
- Equivalent to sampling K elements without replacement proportional to $\exp(u/T)$ — see Vieira (2014), Kool et al. ICML 2019.
- $T = 0$ recovers deterministic top-K.
- $T \to \infty$ recovers uniform sampling K from all children.
- Per-child cost is one tanh, well under 1% of beam-step.
- Reproducible: seed → Gumbel via $g_c = -\log(-\log(U_c))$ where $U_c$ is a hash-derived uniform.

### Score-drop scaling

At each depth, the deterministic algorithm picks the top-K by $u$. The stochastic version picks K samples; some are not in the deterministic top-K. The expected $u$-drop per depth $\Delta u(T)$ is:

$$
\Delta u(T) = \mathbb{E}[u_{\text{det top}} - u_{\text{stoch sample}}].
$$

For a child distribution with spread $\sigma$ in $u$, the stochastic-top-K samples roughly the top region within $\sigma + T$ in $u$-space. So $\Delta u(T) \approx O(T)$ per depth.

Across $N = 256$ depths, total drop $\approx 256 \cdot O(T)$. But the score is the sum of edge-matches, not $u$ — and many depths don't contribute matches (e.g., corners). So the realized score drop is bounded by the number of *match-contributing* depths ≈ 240, times the per-depth $u$-drop divided by the per-match $u$-increment (which is 1).

Empirical calibration (one-shot smoke test on K=256 + high459 prior, scan=row):

| T | deterministic seeds (1,7,42) → score |
|---|---|
| 0 (det.) | 460, 460, 460 (V162 result) |
| 0.1 | 446, 453, 453 |
| 0.3 | 450, 448, 450 |
| 0.5 | 441, 439, 438 |
| 2.0 | 251, 252, 241 |

So $\Delta \text{score}(T = 0.1) \approx 10$, $\Delta \text{score}(T = 0.5) \approx 21$, $\Delta \text{score}(T = 2.0) \approx 210$. Non-linear in T because higher T allows compounding bad picks (a misplacement at depth 50 can prevent good placements at depth 100, even if depth 100's stochasticity is small).

### Why "low T is enough" might miss diversity

At T = 0.1, the build scores are 446-453, but the boards differ in corner_perm (the smoke test showed 3 distinct CP's across seeds 1, 7, 42). So even mild stochasticity scrambles the basin.

But the basins SAMPLED at low T may be biased toward "near the deterministic basin". To get truly DIVERSE 460-candidates, we may need T = 0.5-1.0 paired with a longer ALNS lift (which trades build cost for lift cost).

### Sweep parameterization

$$
\text{builds} = |\mathrm{priors}| \times |\mathrm{scans}| \times |\mathrm{seeds}| = 3 \times 2 \times 8 = 48.
$$

Per build: V155 K=256 at T=0.1 (~12s without congestion) + ALNS 5 min lift. Total wallclock 48 × 5 min / 8 cores = 30 min.

## What we expect to find

H1: 48 distinct basins lifted to 440-460 range.
H2: at least 2-3 distinct 460+ basins (i.e., 460 plateaus on DIFFERENT corner_perms than the seed1/seed13 V156 pair).
H3: maybe 1 basin at 461+, born from stochastic divergence into a corpus-rare-but-globally-viable region.

The valuable output is the basin atlas (corner_perm → lifted score), not the single best score. If H2 is confirmed, we have a basin-distance metric and can do **basin-similarity-to-known-462+** ranking.

## Linked

- [[../sessions/vol-171]]
- [[prior-data-augmented-beam]] (V155 base)
- [[prior-guided-alns]] (V169, complementary on the lift side)
- [[../plans/IDEAS_BACKLOG_2026-05-19]] (V165 STOCHASTIC BEAM was the seed idea)
