---
name: keyring-patch-prior
description: Three corpus-derived signals each carry partial information about \"what
status: built
metadata:
  type: concept
---
# KEYRING — Patch + Pheromone + Position Prior (V181)

Status: `built` — produced 460 in new basin cp=(0,3,1,2) + 459 in distinct basin same run.
Origin: vol-181.
Files: `crates/bench-audit/src/bin/v181_keyring.rs`, `scripts/v181_keyring/run_combined.sh`, `output/vol-181/patch_prior.json`.

## Motivation

Three corpus-derived signals each carry partial information about "what
high-score boards look like":

- **Position prior** (V155): $P(\text{piece} = p \mid \text{position} = c)$.
- **Pheromone** (V178): $\tau(p_1, p_2, d)$ for adjacency frequency.
- **Patch prior** (V181): score-conditional frequency of each 2×2 patch.

A keyring carries all three keys together: the beam ranker sums their
contributions.

## Math

Let a beam state be a partial placement $b$. Define three additive sums:

$$
S_\text{pos}(b) = \sum_{c \in \text{placed}(b)} \log P(b[c] \mid c)
$$

$$
S_\text{pher}(b) = \sum_{(c_1, c_2)\,\text{adj}} \tau(b[c_1], b[c_2], d(c_1, c_2))
$$

$$
S_\text{patch}(b) = \sum_{2\!\times\!2\ \text{patches in } b} \log \rho(\text{patch})
$$

where $\rho \in \{\text{high-only}, \text{neutral}, \text{low-only}\}$ encoded as
$\{+1, 0, -1\}$ after categorical lookup.

Beam ranking score:

$$
R(b) = \text{matched}(b) + \alpha \cdot S_\text{pos}(b) + \lambda \cdot S_\text{pher}(b) + \mu \cdot S_\text{patch}(b)
$$

Calibrated weights (after grid sweep at depth 200):

| Weight | Value |
|---|---|
| $\alpha$ (position) | 1.0 (V155 default) |
| $\lambda$ (pheromone) | $10^{-7}$ |
| $\mu$ (patch) | 0.1 |

Stochastic-temperature $T = 0.05$ gives mild diversity without quality
collapse.

## Patch prior structure

Patch prior file `output/vol-181/patch_prior.json` (5.6MB):

- Enumerate every 2×2 patch (4 piece-id × 4 rotation slots) from all boards ≥440 in DB.
- Categorize by score tier:
  - **high-only**: patches appearing only in boards ≥459. 2087 unique.
  - **neutral**: appearing in both tiers. 853.
  - **low-only**: only in <459. 122 132.

Encoded as `HashMap<u64, f32>` where the u64 key packs (piece1, rot1, ..., piece4, rot4) into 10 bits × 4 cells, low bits at piece1.

## Empirical performance

- 36 builds (9 scans × 4 seeds) → top 8 to 30min ALNS.
- **5/8 V181 lifts reached ≥458** (V175-LONG-LIFT: 1/8).
- Average build score: +3 over V175.
- **New basin 460** in cp=(0,3,1,2) — see [[basin-460-cp0312-v181]].
- **Distinct 459** in same run.

## Why KEYRING works better than V175 alone

- Position prior alone (V155) deterministic; converges on identical seed boards.
- Pheromone alone (V178) too weak.
- Patch prior alone (V181 ablation, not run) likely too noisy due to low-only count dominating.
- Combined: position anchors macro-placement, pheromone refines adjacency, patch
  prior penalises tier-distinctive bad configurations.

## What was kept

- `v181_keyring` Rust binary (committed).
- Patch prior file.
- Calibrated weights.

## What's still open

- KEYRING + 1h ALNS budget instead of 30min — not run.
- Score-gradient patch prior (penalise low-only patches proportional to their score-tier separation).
- Adaptive $\lambda$, $\mu$ that anneal during beam.

## Linked concepts

### Builder components
- [[prior-data-augmented-beam]] (V155, position component)
- [[stigma-pheromone-adjacency]] (V178, pheromone component)
- [[intaglio-forbidden-patterns]] (V180, patch theory)

### Related builders
- [[murmuration-basin-sampling]] (V171 Gumbel-beam parent)
- [[spectral-border-signature]] (V178 sibling)
- [[neuronic-ranker]] (V177 sibling, exploratory)

### Findings produced
- [[basin-460-cp0312-v181]] (the 460 in new cp)
- [[three-basin-iso-plateau]] (post-build ALNS lift is bounded)
- [[v186-pool-biased-top-down]] (vol-186 attempt to extend KEYRING)

### Path forward
- [[plans/CURRENT-VOL]] — vol-189 CORTEZ extends KEYRING with corner-pinning

## Linked memory

- `project_e2_v181_460_new_basin_2026_05_20`
