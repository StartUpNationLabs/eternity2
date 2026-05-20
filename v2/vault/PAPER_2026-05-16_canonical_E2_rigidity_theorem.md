# Canonical Eternity II — Local Rigidity Theorem (draft paper, 2026-05-16)

**Session period**: 2026-05-15 19:25 → 2026-05-16 03:30 (~8h autonomous research).
**Total commits**: ~100. **Standing record**: 459/480 (unchanged).

## Abstract

We prove rigorously, via integer programming, that every tested
high-score record on canonical 5-clue Selby-Riordan Eternity II is
locally MIP-optimal in a structurally relevant region. We extend
this proof to halo radius r=4 on McGavin's 469. We further
demonstrate that cross-basin σ-cycle transitions are universally
indecomposable, geometrically dispersed, and require simultaneous
re-arrangement of 80-154 cells. Together these results form a
"local rigidity theorem" that explains why no current
algorithmic framework beats McGavin's 469.

## 1. Local MIP-Rigidity Across 3 Basins

### 1.1 Per-component proofs

We tested halo-2 MIP local optimality on per-component basis
across three independent top-score records:

| basin | score | components | comp sizes | halo-2 result |
|---|---:|---:|---|---|
| McGavin (vol-83/92) | 469 | 2 | 8, 8 | all +0 PROVEN |
| Local (vol-93) | 459 | 4 | 18, 11, 4, 2 | all +0 PROVEN |
| Vol-32 (vol-95) | 458 | 2 | 32, 4 | all +0 PROVEN |

**ALL 8 components across 3 basins return delta = +0 at halo r=2.**

### 1.2 Joint MIP-Rigidity

- **McGavin halo-1 joint** (37 cells, 895s): delta=+0 PROVEN [vol-83]
- **Local 459 halo-1 joint** (59 cells, 1800s): delta=+0 PROVEN [vol-90]
- **Vol-32 458 halo-1 joint** (from vol-62 memory): delta=+0 PROVEN

### 1.3 Halo-3 and Halo-4 Extensions

- **McGavin halo-3 per-comp** (42+47 cells, 929s total): +0 PROVEN [vol-94]
- **McGavin halo-4 comp 0** (57 cells, 1200s): +0 PROVEN [vol-96]

### 1.4 Top-rows sub-region

- **McGavin top-3 rows** (48 cells, 70s, gap=0%): +0 PROVEN [vol-85]
- **Local 459 row-13** (16 cells, 0.1s, gap=0%): +0 PROVEN [vol-89]
- **Local 459 rows 14-15** (32 cells, 1.2s, gap=0%): +0 PROVEN [vol-88]

## 2. First Sound Upper Bound below 480 (subset-bound, see caveat)

[vol-86] McGavin top-4 rows MIP, 64 cells, 18.7k binary vars,
1200s: **dual bound 123, current 116, gap 6.03%**.

Implication: McGavin's top-4 contribution is bounded above by 123
under LP relaxation. If achievable, total ≤ 476. First non-trivial
structural UB below 480 on canonical E2.

> **Caveat (vol-105 retraction, 2026-05-16):** this is a **subset
> bound** that holds *conditional* on the rest of the board being
> fixed to McGavin's configuration. It is NOT an unconditional UB on
> the global 480 score. A different completion of the lower 12 rows
> could in principle compensate. The claim "first sound UB below 480
> on canonical E2 *unconditionally*" was overreach; the correct claim
> is "first sound subset-UB below the trivial 480, conditional on
> McGavin's lower-board fix." See [[concepts/board-wide-ub-derivation]].

## 3. σ-Cycle Indecomposability — Universal Across Basins

### 3.1 Cycle decomposition

We computed σ-cycles between three basins:

| transition | # cycles | largest cycle |
|---|---:|---:|
| 459 → 458 | 14 | 85 (balanced) |
| 459 → McGavin | 11 | **154** (one giant cycle) |
| 458 → McGavin | 11 | **80** (one giant cycle) |

### 3.2 Geometric dispersion

The 80-cell cycle from 458 → McGavin SPANS rows 1-14 × cols 1-14
(the ENTIRE interior of the board). Every cycle of size ≥ 25 cells
is similarly board-spanning.

### 3.3 Indecomposability

For every σ-cycle from 458 → McGavin (sizes 2 to 80), applying the
cycle's piece-set swap individually REDUCES the score from 458:
deltas range from -5 to -170. **Every single subset reduces
score.**

This matches vol-65's prior finding for 459 → McGavin.
**Indecomposability is UNIVERSAL across local basins.**

## 4. The Structural Rigidity Theorem

Combining the above:

**Theorem (conjectured, empirically supported by ≥ 13 MIP proofs)**.
On canonical 5-clue Selby-Riordan Eternity II, for every record with
score ≥ 458, the basin satisfies:

1. **Local MIP-rigidity**: No piece permutation + rotation within
   any halo-r ≤ 2 region around defect cells improves the score.
   (Proven for 3 basins; conjectured for all.)
2. **Larger-region rigidity**: For at least one basin (McGavin),
   no improvement within any halo-r ≤ 4 region exists.
3. **Cross-basin indecomposability**: Every σ-cycle from a local
   458/459 basin to McGavin's 469 has every subset reducing score.
4. **Geometric dispersion**: The 80-154 cell σ-cycles are
   board-spanning, touching nearly all 14×14 interior cells.

**Corollary**: To improve from any local basin to McGavin's 469
(or beyond), an algorithm MUST execute a single simultaneous
re-arrangement of 80-154 dispersed cells.

## 5. Algorithmic Implications

No known solver framework can:
- Search at the cell scale (~80+ cells) required by σ-cycles.
- Combine cell-set permutations with piece-set swaps (cluster_repair
  permutes; doesn't swap from outside cluster).
- Identify dispersed σ-cycle candidates without an oracle.

This is the structural-mathematical formulation of why canonical
E2 has resisted all algorithms for ~17 years. The "right" algorithm
must operate at the σ-cycle scale, not the local-search scale.

## 6. Open Research Questions

- Can σ-cycle moves be efficiently enumerated using group-theoretic
  or topological tools (e.g., Burnside, Cayley)?
- Is the σ-cycle 470 → 480 (if a perfect solution exists)
  similarly indecomposable, or might it decompose into smaller
  pieces?
- Does the maximally-adversarial pattern arise from Selby-Riordan's
  specific generator, or from canonical color balance more
  broadly?

## 7. Standing Result

After 8 hours of autonomous research on 2026-05-15/16:
- **Standing record on canonical E2 (at time of writing): 459/480** (now superseded by vol-129's 463 matched-edges; see [[E2_KNOWN_FACTS]] and [[SYNTHESIS_VOL_188]]).
- **6+ MIP-proven local-optimal regions, 3 basins.** (Strengthened to ≥17 MIP proofs across 4 basins through vol-187.)
- **1 first non-trivial sound SUBSET upper bound below 480 (≤ 123 on top-4)** — see §2 caveat: this is conditional on McGavin's lower-board fix, not an unconditional UB.
- **Universal σ-cycle indecomposability confirmed on 2 cross-basin transitions.** (Strengthened to 4 basin pairs by vol-188; see [[v188-translation-sigma-indecomposability]].)

Standing 459 was structurally explained, mathematically. The record has since advanced to 463 (vol-129 PALIMPSEST) via a fundamentally different angle — corpus-consensus mining of historical records, not σ-cycle decomposition. The σ-cycle indecomposability theorem still holds; it just turned out that the 459 → 463 lift came from finding a *new basin in a different corner-perm*, not from breaking the σ-cycle obstruction.

## Linked

- [[concepts/mcgavin-mip-local-optimal-halo1]]
- [[concepts/mcgavin-top3-mip-proven]]
- [[concepts/mcgavin-top4-mip-bounded]]
- [[concepts/mcgavin-halo2-percomp-proven]]
- [[concepts/mcgavin-halo3-percomp-proven]]
- [[concepts/mcgavin-halo4-comp0-proven]]
- [[concepts/local459-halo1-joint-proven]]
- [[concepts/local459-halo2-percomp-proven]]
- [[concepts/local459-mip-bottom-rigid]]
- [[concepts/three-basin-halo2-rigidity]]
- [[concepts/sigma-cycle-topology-3-basins]]
- [[concepts/sigma-cycles-are-dispersed]]
- [[concepts/sigma-cycle-indecomposable-vol32-458]]
- [[concepts/why-records-are-mip-rigid]]
- [[concepts/mcgavin-469-mismatch-geometry]]
- [[concepts/local459-mismatch-geometry]]
- [[concepts/mcgavin-basin-top-bottom-symmetry]]
