# Δ-Regularized Search (vol-72 spec)

**Status**: `design` — vol-72 (2026-05-15).
**Inventor**: this autonomous run.

## Motivation

Vol-72 found:
- McGavin-469 has Δ=1 (lowest among our records)
- All canonical 480-boards have Δ=0 (necessary condition)
- Our records at 458-459 have Δ=2-4
- **Δ correlates negatively with score**: lower Δ → higher score

A search algorithm that **minimizes Δ in addition to maximizing
score** might bias toward high-score basins.

## The mechanism

Standard ALNS: maximize `f(B) = score(B)`.

Δ-regularized ALNS:
`f_reg(B) = score(B) - λ × Δ(B)`

Where λ > 0 penalizes border-interior interface mismatches.

For λ small: same as standard ALNS.
For λ large: search prioritizes low-Δ at the cost of edge-matches.
Tuning λ: small enough to not crash score, large enough to bias
toward low-Δ regions.

## Δ as a fast, sound, score-correlated proxy

Δ is cheap to compute: O(56) — just counts edge-piece inward
colors. Computable at every ALNS iteration in microseconds.

It's SOUND: Δ ≥ |true-mismatch-count-at-border-interior|. A
necessary (not sufficient) condition for score ≥ X.

It's SCORE-CORRELATED: empirically, lower Δ ⇒ higher score in
our 6-board sample.

## Where this might break

- Some basins may have low Δ AND low score (border-interior matches
  but interior-interior mismatches). Δ doesn't see interior-interior.
- McGavin-469 has Δ=1, but other 469s might have Δ=0 or Δ=2.
- The 470+ basins may have Δ=0 OR Δ=1 (we don't know).

## Build plan

### Day 1
- Modify alns_only or write Python wrapper:
  - Add Δ computation per board (cached via incremental update)
  - Augment SA acceptance: f_reg = score - λ × Δ
- Sweep over λ ∈ {0.5, 1, 2, 5}
- Compare final scores vs standard ALNS

### Day 2
- Test from multiple starting basins (47 component reps).
- Does Δ-regularization help reach 469+ from non-McGavin basins?
- If yes — useful!

## Linked

- [[basin-permutation-group]]
- vault/concepts/oracle-attracted-alns.md (related: regularization toward target)
- memory: project_e2_ns1_deficit_invariant
