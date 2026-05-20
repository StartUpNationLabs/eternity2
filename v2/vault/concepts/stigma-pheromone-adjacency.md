---
name: stigma-pheromone-adjacency
description: Naming: STIGMA — Latin \"mark, brand\"; in Ant Colony Optimization the stigmergic trace ants leave on a path. We trace ...
status: unbuilt
metadata:
  type: concept
---
# STIGMA — Pheromone Adjacency Learning Across Runs (V178)

Status: `unbuilt` (design 2026-05-20)
Origin: vol-178 (planned)
Naming: **STIGMA** — Latin "mark, brand"; in Ant Colony Optimization the *stigmergic* trace ants leave on a path. We trace which piece-piece adjacencies "work" across many runs.

## Idea

Standard V155 / V175 beam search uses a FROZEN corpus prior — same matrix for every run. ALNS uses adaptive operator weights but no cross-run memory.

STIGMA introduces a **pheromone matrix** $\tau \in \mathbb{R}^{N_{\text{piece}} \times N_{\text{piece}} \times N_{\text{dir}}}$ where $\tau[p_1, p_2, d]$ = accumulated reward for placing piece $p_1$ at position $\pi$ and piece $p_2$ at $\pi + d$ (d ∈ {N, E, S, W}).

After each ALNS run with final board $B$ and score $s(B)$, update:

$$
\tau[p_1, p_2, d] \mathrel{+}= \rho \cdot s(B)^\gamma \cdot \mathbb{1}[B[\pi]=p_1 \wedge B[\pi+d]=p_2]
$$

where $\rho$ is the evaporation rate (≈ 0.1) and $\gamma$ amplifies high-score boards (≈ 2-3).

Between runs:
- $\tau \mathrel{\*}= (1 - \rho_{\text{evap}})$ — global pheromone evaporation.

Beam search ranking incorporates pheromone:
- For child $c$ at position $\pi$ with piece $p$ and existing neighbor $p'$ at $\pi - d$, add bonus $\lambda \cdot \tau[p', p, d]$ to the combined score.

## Why genuinely new (vs corpus prior)

1. **Adjacency-level, not placement-level.** Corpus prior says "piece 42 at position 17 → support N". Pheromone says "piece 42 with piece 67 to its east → support N".

2. **Live updating, not frozen.** Corpus is built once from DB. Pheromone updates after every run.

3. **Out-of-distribution learning.** If a piece-pair appears in 0 corpus boards but in 5 of our run-best boards, pheromone learns it; corpus prior never does.

4. **Position-invariant.** A pair (p, q) east-adjacent at position 17 gets the same pheromone credit as the same pair at position 100. Generalizes better than position-anchored prior.

## Math — pheromone size

$N_{\text{piece}}^2 \cdot 4 = 256^2 \cdot 4 = 262144$ entries.
At f32 each, 1 MB matrix. Cheap.

Compute per beam-step: 4 neighbor lookups × f32 add = trivial.
Update per ALNS run: 480 edges × 1 add = trivial.
Evaporation: 262k mul = sub-ms.

## Algorithm sketch

```
INIT: τ = uniform_small
For batch in 0..N_BATCHES:
    For job in 0..N_PARALLEL:
        b = V175_GAUNTLET_with_pheromone(τ, seed=job)
        b' = ALNS_lift(b, budget=5min)
        record (b', s(b'))
    For each (b', s) in batch:
        update τ with (b', s)
    τ *= (1 - ρ_evap)
```

Convergence behavior:
- Early batches: pheromone ≈ 0, beam falls back to corpus prior + Gumbel-top-K.
- Mid batches: pheromone amplifies pairs that consistently appeared in 450+ outputs.
- Late batches: if a 461+ pair emerges, pheromone reinforces it across all subsequent runs.

## What's still open

- **Cold start**: bootstrap pheromone from the 1278-board corpus? Or zero-init and let it learn fresh?
- **Multi-objective**: separate pheromone for "high-score" vs "diverse-basin" boards?
- **Anti-pheromone**: subtract pheromone for low-score boards? Risk of unlearning useful signal.
- **Position-conditioned variant**: $\tau[p_1, p_2, d, \text{region}]$ where region ∈ {border, edge-adj, interior}.

## Why this beats just-using-corpus

Hypothesis: the 49-board high459 corpus is fundamentally CONCENTRATED in a few cp-families. Our 460-tier 23 boards in the database are clustered. The pheromone, fed by V175's diverse-cp builds (18 unique cps in 36 builds), can DISCOVER new pair-patterns characteristic of unexplored basins.

If V175 GAUNTLET builds across 9 scan orders explore 18+ unique corner-perm families, and STIGMA reinforces pair-patterns shared by HIGH-score runs (not all runs), then after a few iterations pheromone identifies the *family-invariant* good adjacencies — knowledge the corpus prior cannot capture because corpus is dominated by 1-2 families.

## Linked

- [[vol-178]] (planned)
- [[prior-data-augmented-beam]] (V155 — what STIGMA augments)
- [[murmuration-basin-sampling]] (V171 — diversity engine)
- [[IDEAS_BACKLOG_2026-05-19]] V158 PAIR-PRIOR built static; STIGMA is the live version.
