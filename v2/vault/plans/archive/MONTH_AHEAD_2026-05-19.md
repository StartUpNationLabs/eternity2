# Month-Ahead Plan (2026-05-19, user away ~30 days)

User feedback: "Great pivot here. Continue. Even with new pivots."
Mandate: keep working, pivot when stuck, no McGavin obsession, no
single-track basin attacks.

## Principles for this month

1. **Build reusable tools, not one-shot scripts**. Anything I write
   should be measurable and re-runnable for future operator
   comparisons.
2. **Pivot honestly when something doesn't work**. Don't burn weeks
   on a doomed approach. Refutation is data.
3. **Cross-domain framings encouraged**. Per user-archived
   brainstorm reservoir: PRISM, GRAIN, TUNNEL, MURMUR, INTAGLIO,
   PROVENANCE, THAW.
4. **Variance reporting**: every quant result needs ≥ 3 seeds with
   min/median/max.
5. **Vol discipline**: one invention per vol, vault session + concept
   pages, commit early/often.

## Vol-132 candidate: CONSTRAINT-DENSITY CHARACTERIZATION

The scaling curve revealed canonical 16×16/22 is LESS dense than
mid-size generated puzzles. That's measurable.

**Plan**:
- Define constraint density: per piece-side, what fraction of colors
  has ≥ 1 occurrence in the piece set? (Equiv: out-degree in the
  color-pairing bipartite graph.)
- Measure on canonical, on generated suite, on community boards.
- Predict solver wall: where does ALNS basic fall below threshold?
- If hypothesis holds (lower density ⇒ higher reachable %), generate
  a HIGHER-DENSITY 14×14 testbed that should be HARDER than canonical.

## Vol-133 candidate: FILAMENT vs SA HEAD-TO-HEAD on scaling suite

We have the suite + FILAMENT. Run alns_e2 with `--repair-kind sa` vs
`--repair-kind filament` on the same 18 puzzles. First proper
controlled comparison.

## Vol-134 candidate: GRAIN polycrystalline

Multi-seed crystal growth on E2. Distinct from CONCORD's projection
math and PALIMPSEST's data-mining. Requires:
- Seed placement on board
- Greedy/WFC attachment from each seed under shared piece inventory
- Grain-boundary score as objective
- Recrystallisation destroy operator

## Vol-135 candidate: bf_bw vs ALNS scaling

We have bf_bw_canonical_partial as a DFS seeder. Run it on the suite
to see how DFS scales vs ALNS. May reveal that some sizes are
DFS-trivial.

## Vol-136 candidate: INTAGLIO forbidden-pattern mining

For each k-cell subgrid configuration (k ≤ 5), determine if it can
appear in ANY solution. Forbidden subgrids prune the search space.

## Vol-137 candidate: PROVENANCE generator-fingerprinting

E2 was built by Selby+Riordan with a specific algorithm. Can we
extract statistical fingerprints from the piece set that constrain
the original solution? Risky but novel.

## Hard rules

- NO McGavin-anchored or basin-anchored work this month.
- NO single-invention multi-vol expansion. Each vol gets ONE name + 1
  binding item set.
- Cap at 3 vols per real-time day to avoid shallow output.
- If a vol takes > 8 hours wall-clock with no progress, refute and
  pivot.

## Honest current state at session start (2026-05-19 ~12:50)

- Records: matched-edges 469 (McGavin), strict-canonical 459. NEW
  matched-edges 463 from V129-T12 in (2,3,0,1) McGavin-adjacent basin.
- Refuted this session: FPL (cross-basin), CONCRETION, ATLAS,
  PALIMPSEST hard-pinning, FILAMENT vs SA.
- Built: PALIMPSEST data-analysis tooling, FILAMENT operator,
  scaling-curve infrastructure.

## Next action: pick highest-EV vol-132

Of the 6 candidates, **vol-132 = constraint-density characterization**
is highest EV because:
- Concrete measurement, not search
- Builds on vol-131's curve finding
- Outputs a constraint-density predictor
- Could explain why E2 specifically is hard
