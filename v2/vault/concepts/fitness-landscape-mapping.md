---
tags: [concept, exploration, scaling, energy-landscape]
status: unbuilt
origin-vol: 34 (proposed)
---

# Fitness / energy landscape mapping on small E2 puzzles

**Status**: `unbuilt` (proposed at vol-34 mid-volume by user).
**Origin**: User question (2026-05-14): "in ML, we have gradient descent
in spaces and there is this notion of valley/cliffs etc.. and local
minimas which makes me think about our 'basins'. Could we on smaller
puzzles try to map the world of minimas/maximas etc., and from that,
first see if it makes sense on smaller puzzles, and then if we could
understand potential elements from that to scale to bigger and bigger
puzzles?"

## Premise

We already implicitly know that the E2 score landscape has:

- **Multiple disjoint basin families** ([[trajectory-families]] — vol-18)
- **First-order barriers** between basins (76-cell barrier for
  447→456, [[r5f-cooperativity]] — vol-18)
- **Bound ceilings** per basin family that operator-locks can't break
  ([[relaxed-bound]] — vol-21, vol-22)
- **Saddle-point regions** where bound-ascent can navigate to high-bound
  configs but ALNS cannot recover a high SCORE from there
  ([[basin-escape-recipe]] — vol-22)

The user's hypothesis: if we systematically map this landscape on
small puzzles (where the local-optima set is tractable), we may find
structural invariants that scale to canonical 16×16.

## Why small puzzles work for this

For canonical 16×16/22c, the raw configuration space is ~10⁴⁶⁵.
For 4×4/4c (existing testbed), it's ~10²⁴. For 6×6/5c, ~10⁵⁸.

But the LOCAL-OPTIMA set is much smaller:
- Number of LOs scales roughly as 2^(barrier-count), not as total
  configurations.
- Empirically on 6×6/5c with ALNS-from-random: probably hundreds of
  distinct LOs, not millions.

5000 ALNS-restart runs at 6×6/5c = ~30 min compute. Tractable.
Enough density to estimate basin size, adjacency, barriers.

## Proposed experiment

### Phase 1 — enumerate local optima at 6×6/5c

For 5000 independent random initial boards:
- Run ALNS (winning5 ops, SA-repair) until convergence (~30s each, but
  6×6 is much smaller so probably <5s).
- Save final board.

Cluster the 5000 final boards by edit-distance (or Hamming on
piece-position pairs). Each cluster = one local-optimum attractor.

### Phase 2 — basin properties

For each cluster {LO_i}:
- **Score**: matched-edge count of LO_i (deterministic per LO).
- **Basin size**: count of random starts that converged to this LO.
- **Basin radius**: max Hamming from LO_i to any board in its basin.
- **Adjacency**: for each pair (LO_i, LO_j), find min-Hamming bridge
  configuration accepted by ALNS from both sides.
- **Saddle-point height**: max-Δ along a bridge path between adjacent
  LOs (computes the "barrier").

### Phase 3 — fitness-distance correlation

Plot (Hamming-distance-to-best-LO, score) for all LOs. If FDC is
positive (close to best ⇒ high score), the landscape is "easy" — a
"big-valley" structure. If FDC ~ 0, the landscape is "rugged" —
distinct basins with no global structure.

For canonical-class problems (TSP, QAP, etc.) the FDC is typically
positive and the operator-design literature exploits this. If E2 has
positive FDC at 6×6 but negative at 16×16, that's a critical scale
transition.

### Phase 4 — test transferability

Repeat phases 1-3 at 4×4/4c, 6×6/5c, 8×8/5c. Look for invariants:
- Does "best basin is always reachable via ≤3 inter-basin moves" hold
  across scales?
- Does the basin-size-vs-score distribution have a consistent shape?
- Are saddle-point heights ∝ N (linear in cell count)?

### Phase 5 — predict + exploit at 16×16

If invariants hold at 4-6-8, predict 16×16 properties:
- If basins are connected in low Hamming, design "bridge operator"
  that traverses 3-basin paths efficiently.
- If saddle-heights scale linearly, predict the 16×16 barrier and
  design an SA schedule with matching temperature.

## What this volume would NOT do

- ❌ Try to break 458 directly (that's record-chase territory).
- ❌ Build new operators yet — only map and characterize.
- ❌ Apply to canonical 16×16 in phase 1 — too expensive there.

## Cost estimate

- Phase 1 (6×6 enumeration): 2 hrs compute + 1 hr build.
- Phase 2 (basin properties): 1 day analysis + visualization.
- Phase 3 (FDC): existing scripts apply.
- Phase 4 (transferability): repeat phases 1-3 at 4×4, 8×8.
- Phase 5 (prediction): depends on what we find.

**Total**: 2-3 day volume.

## Linked concepts

- [[trajectory-families]] — already-measured disjoint basin families.
- [[r5f-cooperativity]] — measured 76-cell barrier (vol-18).
- [[relaxed-bound]] — basin-local ceilings (vol-21).
- [[basin-escape-recipe]] — vol-22's high-K traversal.
- [[mismatch-geometry]] — where errors live within basins.

## Linked memory

- (to write at vol-35 close, if picked)
