---
tags: [concept, metaheuristic]
status: built-light
origin-vol: 5
---

# Genetic algorithm (4×4 / 6×6 region crossover)

**Status**: `built` (vol-5); not extended past vol-5
**Origin**: vol-5
**Files**: `crates/ga/`

## Definition

- **Population**: ~50 plateau boards (score ≥ 440).
- **Crossover**: pick a K×K region. Replace child's region with parent 2's same region; reconcile piece duplications by random reassignment.
- **Mutation**: PT polish on the offspring (small SA budget).
- **Selection**: tournament on score.

## Variants

- **GA-light**: 4×4 region crossover, ~10-iter cascades. Reaches 452/480 within a basin family.
- **GA-LARGE**: 6×6 region crossover, 3-hour cascade with PT mutation. Vol-5 best: **453/480** (10 published distinct boards on 2-3 basin families).

## What got measured

- **Within-family** (similar borders): reaches 452-453. Some replicas momentarily touch 454, fall back.
- **Between-family** (different borders): noise. Crossover fails because piece-reconciliation destroys structure.

## Why it stalled at 453

Vol-5 + vol-6 finding: the "30-mismatch budget" stays approximately conserved across local moves (NE1/NE2 soft penalties redistribute but don't reduce). GA crossover at 4×4-6×6 size hits the same Hamming-moat depth ≥ 5 that defeats ALNS at that K.

Larger crossover (8×8+) would be needed to traverse the moat, but cost-per-iteration explodes. Not explored.

## Status post-vol-6

Superseded by vol-6's `pt_e2 --pin-perimeter` which reached **454/480** with a different mechanism (border-diversity sampling + PT).

Could still be useful for **inter-family** transfer if combined with `--start-from` warm starts from each family. Unbuilt.

## Vol-25 literature review (added 2026-05-13)

Conducted a careful read of the academic literature on GA for canonical 16×16 Eternity II. The published evidence is unambiguous: **no pure GA has ever broken 400 on canonical 5-clue E2**. The often-cited "458/480" result was Schaus 2008's CP+VLNS hybrid, NOT a GA. We had been miscrediting the literature.

### Reproducible canonical 16×16 GA scores from the literature

| Source | Method | Best score | Notes |
|---|---|---|---|
| Munoz, Gutierrez, Sanchis (2009 IEEE CEC) | MOEA + initialisation-with-knowledge | **396/480** (mean 387.6, std 2.94) | Reproducible. The honest pure-GA SOTA on canonical 5-clue. Random init: 365 max. Random search baseline: 48 max. Exhaustive backtrack: 371 max. |
| Munoz et al. (2009) | GA + initialisation-with-knowledge | 394 max | Mean 385.9. Slightly worse than MOEA. |
| Munoz et al. (2009) | Artificial Immune EA + IWK | 385 max | Mean 379.8. |
| Niang (Concordia MASc 2010) | Genetic algorithm, region exchange crossover | **NOT TESTED ON 16×16.** | Worked on 4×4 (27s avg), 5×5 (30s avg), 6×6 (195s avg). **Failed on 7×7.** Explicit conclusion in thesis: "*we were not able to obtain a solution on a 7x7. Apparently, our solution did not scale well.*" |
| nathan-pichon (GitHub 2017) | Island GA with 3 crossovers × 3 mutations | "467 claimed" — **not achieved** | Single commit, broken score function (double-counts internal edges), README disclaims success. |
| **us, vol-5 (2024)** | GA-LARGE 6×6 crossover, warm-start from 440-class basins | **453/480** | Within-family only; between-family was noise. **Best recorded GA-style result on canonical 16×16 E2 anywhere.** |

### What the literature actually proves (3 independent findings)

1. **Pure GA caps at ~396 cold-start on canonical 16×16 E2.** Three independent attempts (Munoz 2009, Niang 2010, nathan-pichon 2017) confirm. The Sholomon 2013 jigsaw work (96-98% accuracy on 30k-piece puzzles) does NOT transfer because image jigsaw has pixel-gradient signals that E2 lacks.

2. **Initialization-with-knowledge contributes more than the GA itself.** Munoz et al. measure +29 score points from IWK alone (random init 365 → IWK init 394 for the same MOEA). The crossover/mutation cycle contributes much less than the warm-start.

3. **All published >400 results on canonical 5-clue E2 are HYBRIDS that use a non-GA method as the heavy lifter.** Schaus 2008 (458): CP + VLNS. Vancroonenburg 2010 (459): hyper-heuristic with DFS + lower-level heuristics. McGavin 2020 (469): scheduled-relaxation backtracker (no GA). The GA framing is decorative.

### Why pure GA hits this wall

The first-principles reason (confirmed by ALL published experiments): GA depends on small perturbations producing small fitness changes. E2's score is **discrete and rugged** — moving one piece changes the score by ±4 with cascading invalidations. Region-exchange crossover that swaps a "good region" only retains its score if the region's boundary happens to align with matching colors on the other parent; otherwise the swap loses all internal matches and gains nothing. Best-buddy heuristics (Sholomon) don't transfer because edge-color matching is many-to-many, not unique.

### Operator zoo from the literature

For reference if we ever build a GA variant ourselves. Operators tested in published work:

**Crossover**:
- **Region exchange** (Munoz, Niang, nathan-pichon): clone parents, swap two random sub-rectangles, fill conflicts randomly. **Most tested. Most popular. Caps at ~396.**
- **Uniform crossover** (Munoz, Niang): per-cell pick from parent A or parent B via random template. Slower, marginally worse than region exchange.
- **Kernel-growing crossover** (Sholomon 2013): start with one piece, grow outward, use consensus → best-buddy → greedy at each boundary. SOTA on image jigsaw. **Doesn't transfer to edge-matching** because best-buddy requires unique pixel-gradient matches.

**Mutation**:
- Rotate / swap / swap+rotate single tile — too small, no impact.
- Rotate region / swap region / region inversion — Munoz finds region rotation best.
- Row/column inversion — Niang finds these effective.
- Scramble (keep one corner, randomize rest) — emergency-only.

**Selection**: tournament (most papers). Linear ranking (Niang). Roulette (refuted by Niang: "poor results").

### Vol-25 outlook

A parallel agent is currently implementing population GA with sub-region crossover. Based on the literature evidence, honest expectations:
- **Without domain-informed initialization**: cap at ~365 (Munoz random-init baseline).
- **With domain-informed initialization**: cap at ~394 (Munoz IWK baseline).
- **With warm-start from our basin pool (vol-22 451-class basins)**: cap at ~453 (our own vol-5 result).
- **If the GA targets cross-basin recombination (sub-region swap *between* basin-escape outputs)**: unclear, but this is the *only* framing not yet tested empirically in any published work. Could yield novel basins; probably not a record-breaker.

### Honest framing

GA is NOT a path to 469+ on canonical 5-clue E2. The literature evidence is overwhelming after 16 years and 6 independent attempts. Any GA work we do should be framed as:
- a **cross-basin recombination operator** inside [[basin-escape-recipe]] (genuinely untested),
- a **diversification layer** over PT chains (sub-region crossover between chain states),
- **NOT** as a standalone record-attempt method.

## Linked papers

- Munoz, Gutierrez, Sanchis. *Evolutionary techniques in a constraint satisfaction problem: Puzzle Eternity II*. IEEE CEC 2009.
- Niang. *Solving the Eternity II Puzzle using Evolutionary Computing Techniques*. Concordia MASc thesis 2010.
- Schaus, Deville. *Hybridization of CP and VLNS for Eternity II*. JFPC 2008 (the 458 record, NOT GA).
- Vancroonenburg, Wauters, Vanden Berghe. *A two phase hyper-heuristic approach for solving the Eternity II puzzle*. META 2010 (459).
- Sholomon, David, Netanyahu. *A genetic algorithm-based solver for very large jigsaw puzzles*. CVPR 2013 (image jigsaw, NOT edge-matching).
- Kovalsky, Glasner, Basri. *A global approach for solving edge-matching puzzles*. SIAM J. Imaging Sci. 2015 (SDP relaxation, NOT GA, but interesting alternative).

## Linked concepts

- [[parallel-tempering]] — the post-vol-6 successor
- [[basin-454-vol6]] — the basin GA stalled just below
- [[alns]] — the K-bound moat

## Linked memory

- `project_e2_state` (vol-5 row, vol-6 row)
