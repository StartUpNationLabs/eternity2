---
name: high-t-mcmc-refuted
description: "Vol-114 T1 — IDEAS_FROM_BLANK Idea H REFUTED both forms. Single-piece-swap MCMC at T ∈ {2, 5, 10, 15, 25, 50}: chain randomizes (score crashes from 459 to 20-25), never returns to high-score. σ-cycle MCMC with corpus of 4 459 basins: chain hovers around 459 (max ever observed = 459, never 460+). The 459 ceiling holds across the entire 'random + Metropolis' algorithmic family."
metadata:
  type: project
---

# High-T MCMC on the 459 level set (vol-114 T1 — REFUTED)

**Status**: `refuted` 2026-05-16 ~15:35.
**Origin**: IDEAS_FROM_BLANK Idea H — "Energy-based MCMC at high T".
**Hypothesis**: standard MCMC at T=1 has acceptance ~0 for the
σ-cycle moves needed to cross 459 barriers. At T=50-100, these
moves should accept. Maybe MCMC can mix where ALNS can't.

## Test 1 — single piece-swap Metropolis

`scripts/vol114_high_t_mcmc.py` — for each iteration, pick two
random non-hint cells, swap their pieces (or pieces+rotations),
Metropolis acceptance. 100K iterations across T ∈ {2, 5, 10, 15,
25, 50}.

| T   | best | acceptance | high-score (≥450) visits |
|----:|-----:|-----------:|-------------------------:|
|   2 |  459 |       0.85 |                      1   |
|   5 |  459 |       0.94 |                      1   |
|  10 |  459 |       0.97 |                      1   |
|  15 |  459 |       0.98 |                      1   |
|  25 |  459 |       0.99 |                      1   |
|  50 |  459 |       0.99 |                      1   |

**The "1 visit" is the starting state itself.** Chain immediately
diverges from 459 (score plunges to 20-25 within thousands of
iterations) and **never returns** in 100K steps.

Even at low T (=2), acceptance rate is high (85%) because the
typical Δ is small (range -5 to +5 per swap, T=2 gives p ≈
0.6-0.9 for negative deltas), so the chain doesn't stay near 459.
The 459-level set is essentially a measure-zero subset of valid
placements; random walking can't find it.

## Test 2 — σ-cycle Metropolis with basin corpus

`scripts/vol114_sigma_mcmc.py` — at each iteration, pick a random
target basin from the corpus, compute σ-cycles current→target,
pick a random cycle (up to size K), apply it as a multi-cell
swap, Metropolis acceptance.

| max-cyc-size | T | iters | best | high-score visits           |
|-------------:|--:|------:|-----:|-----------------------------|
|           20 | 2 |   500 |  459 | 459:13, 455:5, 454:3, others |
|           50 | 5 |   500 |  459 | 459:12, 455:9                |

**The chain hovers around 459 but never exceeds 459.** This is the
σ-cycle indecomposability finding (vol-99 + vol-110/111) in action:
the only moves that preserve 459 are FULL σ-cycle applications;
subsets lose edges; the chain never CONSTRUCTS a 460+ move.

## Why H is refuted

Both forms tested:
- **Random local moves at high T**: chain randomizes faster than
  it can find another high-score basin. The 459-level set's
  measure-zero structure dooms random walkers.
- **σ-cycle moves at moderate T**: chain navigates within the
  459-level set (visiting multiple basins) but never EXCEEDS it,
  because σ-cycles between 459-basins are score-preserving
  (Δ=0 for full) or score-decreasing (Δ<0 for subsets).

The 459 ceiling is robust against the MCMC family.

## Implication for the directive

IDEAS_FROM_BLANK Idea H (Energy-based MCMC at high T) is closed as
refuted. Confirms (yet again) that to exceed 459 requires either:
- A genuinely new move structure (not random + Metropolis).
- A different objective function that admits sub-459 stepping stones.

Multi-week ML / RL self-play (Idea C) remains the only theoretical
handhold not yet refuted at this scale.

## Linked

- [[multiple-459-basins-rigid]] — basin corpus used.
- [[basin-mix-mip-refuted]] — vol-112 T1, parallel MIP refutation.
- [[../MATH_NOTES_2026-05-16_459_LEVEL_SET]] — theoretical framing.
- [[../sessions/vol-114]].
