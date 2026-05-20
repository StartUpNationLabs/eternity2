# Session — vol-21

**Theme**: Relaxed bound + edge-gap. Dead-end detector strictly stronger than K ≤ 5.
**Raw**: [[archive/raw/RESEARCH_NOTES_21|RESEARCH_NOTES_21.md]], [[archive/raw/RESEARCH_NOTES_21_PLAN|RESEARCH_NOTES_21_PLAN.md]]

## What was attempted

- `edge_relax.rs` (relaxed piece-uniqueness iteration → basin-local bound).
- `edge_bound_ascent.rs` (optimize bound not score).
- `edge_gap_attack.rs` (destroy gap-region cells, repair).
- `edge_target_match.rs` (Hungarian to relaxed target).
- `edge_relax_hints.rs` (hint-only bound 448).
- `edge_tight_bound.rs` (per-edge loose bound 480, all edges independently matchable).
- `v21_gap_survey.py` (121 boards, map gap landscape).
- Edge-Kempe phase 1-3 probe.

## What was measured / kept

- **[[relaxed-bound]] introduced**: `relaxed_bound(B) − score(B) = gap(B)`. Strictly stronger than K=5 [[operator-lock]] test (gap = 0 implies operator-locked at any K).
- **Our 457 basin ceiling = 461** (gap +4, **HARD-LOCKED**: 4 dup + 4 missing pieces have ZERO shared rotation tuples; min hamming = 2; 40M perms K=8-11 give 0 improvers).
- **Other basins**: 456 winning5_sa +5, 450 ocs +15, 454 winning5_sa +6.
- **[[bound-ascent]] from our 457**: bound climbs 461 → 468 in 710 iters (greedy); score collapses 457 → 128.
- **Bound-ascent terminal**: 468-473 across seeds; score always collapses.
- **121-board gap survey**: gap distribution maps the basin atlas.

## What was refuted

- **R3 OT (vol-21 re-test)**: still valley-finder.
- **Edge-Kempe phase 1-3**: 0 improvers in mismatch-cell flips; 0 improvers in 2-cycles; 0 improvers in ≥0 3-cycles.
- **Houdayer oracle-swap on (457, 456_k)**: 456 basins configured worse than 457 (vol-22 will reconfirm).
- **`alternating bound-score`**: every step undone within 30s; lands on byte-identical 457.

## Concepts touched

- [[relaxed-bound]] (introduced)
- [[bound-ascent]] (introduced)
- [[edge-grid-dual]] (Kempe-chain probe, null)
- [[operator-lock]] (strictly weaker than gap test)

## Open at vol-close → vol-22

The bound-ascent on (440, ???) pairs could find basins with ceiling > 457. Vol-22 builds the recipe.

## Linked memory

- `project_e2_vol21_edge_relax_bound`
