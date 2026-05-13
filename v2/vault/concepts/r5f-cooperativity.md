---
tags: [concept, structural-physics, barrier]
status: measured-key-finding
origin-vol: 18
---

# R5f cooperativity (the 447→456 first-order barrier)

**Status**: KEY PHYSICS finding (vol-18)
**Origin**: vol-18 (R5f reframing)
**Files**: vol-18 measurement scripts

## Statement

The 447 → 456 transition is a **single 76-cell first-order barrier**. ALL 1024 cycle-subsets within the cycle structure decomposing 447→456 have Δ < 0; only the FULL 10-cycle has Δ > 0.

→ Every single step (any K < 76) is downhill. Standard MCMC at T=1 has acceptance `p ≈ exp(-21) ≈ 1×10⁻¹⁵`.

## Implication: hot-PT temperature

To traverse Δ=-21 with reasonable probability, need T ≈ 30-50:
- `p(Δ=-21 at T=30) ≈ exp(-21/30) ≈ 0.50`.
- `p(Δ=-21 at T=50) ≈ exp(-21/50) ≈ 0.66`.

→ Vol-18 [[parallel-tempering]] with T_max=30 made the 447→456 transition occur; this is how the 457 cold-start record was reached.

## Implication: ALNS temperature irrelevance

The 100% Metropolis acceptance on iso-score plateaus (vol-17 H9) and the impossibility of traversing Δ=-21 by single moves are **the same observation**. The lever is not T; the levers are:
- Larger destroy (K ≥ 76 to span the cycle).
- Oracle guidance to choose the right 76-cell cycle.
- A different operator altogether (Blackwood, prune-restart).

## Why K ≤ 5 operator-lock at 457

The next 456→457 step is presumably another cooperative barrier of similar shape (not yet measured directly). With K ≤ 5 testing (vol-20: 28M 5-cycles), zero improvers. K=8-11 perms (vol-21): zero improvers. Inferred cooperative size at 457: K ≥ 12, plausibly much larger. See [[operator-lock]].

## Linked concepts

- [[parallel-tempering]] — why T=30 was needed
- [[operator-lock]] — the K-bound on local moves
- [[alns]] — why temperature isn't the lever
- [[basin-457-pt]] — the basin discovered by crossing this barrier

## Linked memory

- `project_e2_vol18_r5f_cooperativity`
- `project_e2_vol18_trajectory_families`
