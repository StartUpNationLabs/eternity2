# Session — vol-18

**Theme**: Trajectory families. R5f cooperativity. OracleCycleSwap + hot-PT → **457/480 cold-start record**.
**Raw**: [[archive/raw/RESEARCH_NOTES_18|RESEARCH_NOTES_18.md]]

## What was attempted

- R3 iterative Hungarian/OT repair.
- R5 mismatch homology (β_1 measurement).
- R5c "leaking pieces" hypothesis.
- R5d direct-snap from 447 to 456.
- R5e permutation-cycle decomposition of 447 → 456.
- R5f cooperativity barrier measurement (1024 cycle-subsets).
- [[oracle-cycle-swap]] + hot-PT at T_max=30.

## What was measured / kept

- **[[r5f-cooperativity]] — KEY PHYSICS**: 447→456 transition is a single 76-cell first-order barrier. ALL 1024 cycle-subsets have Δ < 0; only the full 10-cycle has Δ > 0. Standard MCMC at T=1: p ≈ 10⁻¹⁵.
- **COLD-START RECORD**: **457/480** (hot-PT, T_max=30, 4 chains, seed=1, from OracleCycleSwap'd 456). See [[basin-457-pt]].
- **[[trajectory-families]] — KEY INSIGHT**: score-distance ≠ configuration-distance. 454 and 456 boards from different CP partials share only 12% piece-position / 43% region. Cross-family σ-cycles are 88-218 cells with Δ up to -171.
- **456 unreplicable on chunk_0019**: 3 seeds → 449-454. The 456 board came from a DIFFERENT (pre-overnight) CP partial.
- **Mismatch homology β_1 = 0**: mismatch edges form a forest. Rules out CycleDestroy operator.

## What was refuted

- **R3 OT/Hungarian standalone**: strict valley-finder, stuck at 453/447 fixed points across 5 seeds (1000× faster than ALNS, useless without barrier-crossing). Later subsumed in [[basin-escape-recipe]] (vol-22) as middle step.
- **R5 cycle-destroy**: β_1 = 0 = no topological cycles to destroy.
- **Puzzle reduction (forced piece pairs)**: ZERO on canonical E2. Selby-Riordan generator intentionally avoids forced moves; minimum (color, side) supply = 24.

## Concepts touched

- [[r5f-cooperativity]] (KEY PHYSICS finding)
- [[trajectory-families]] (KEY INSIGHT)
- [[oracle-cycle-swap]] (introduced)
- [[parallel-tempering]] (hot-PT T_max=30 variant)
- [[mismatch-homology]] (introduced, small signal)
- [[basin-457-pt]] (NEW BASIN — current cold record)

## Implication

K ≤ 5 operators are insufficient at the 447→456 step (need K = 76). Sets up vol-20 [[operator-lock]] measurement.

## Linked memory

- `project_e2_vol18_457_record`
- `project_e2_vol18_r5f_cooperativity`
- `project_e2_vol18_trajectory_families`
- `project_e2_vol18_456_unreplicable`
- `project_e2_vol18_r3_ot_null`
- `project_e2_vol18_r5_homology`
- `project_e2_vol18_puzzle_reduction_null`
