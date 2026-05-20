# Session — vol-20

**Theme**: Exhaustive local-move null on 457. K ≤ 5 operator-lock proof. Backbone scan-order correction.
**Raw**: [[archive/raw/RESEARCH_NOTES_20|RESEARCH_NOTES_20.md]]

## What was attempted

- N3a pair-rotation sweep, N3b exact rotation via LP/junction tree (queued).
- N4 2-cell transposition landscape (20k+ pairs).
- N4b 3-cycle/4-cycle/5-cycle scan (32k+ + 982k+).
- N4c cooperative 3-cycle composition.
- N5 patch branch-and-bound on 38-cell mismatch region (60s, ~456k nodes).
- N5b halo radius-r BB.
- N5c boundary perturbation via rotation.
- N6 cross-board backbone consensus (with dedupe bias correction).
- N6c cross-scan-order backbone TD vs BU.
- `basin_hop` (perturb + ALNS recovery, Δ = -2 to -16 all reabsorbed).

## What was measured / kept

- **[[operator-lock]] (K ≤ 5)**: 457 is **strictly locked** under all moves of cardinality ≤ 5. Zero improvers in:
  - 1024 single rotations
  - 6720 adjacent-pair rotations
  - 20240 non-adjacent transpositions
  - 32796 3-cycles, 982200 4-cycles, 28480440 5-cycles
  - 38-cell patch BB (~456k nodes / 60s) and 82-cell halo-1 BB (~122k / 90s).
- **All 11 saved PT-457 boards are byte-identical** (one basin found 11 times).
- **[[mismatch-geometry|Backtrack distribution]]**: 95% interior, 5% border, 0% corner. Layer-3 shoulder is peak (124 bt/cell, 12× perimeter).
- **The 764-plateau**: ~175 interior cells all have domain 764 after hints+AC3. **The plateau IS the search problem.**
- **Backbone correction**: cross-scan-order TD vs BU portfolio shows the vol-17 "17/18-cell backbone" is **mostly scan-order artefact**. Only **5 canonical hints** have true structural cross-source agreement.
- **basin_hop**: 457 attractor radius Δ = -16; ALNS reabsorbs all perturbations.

## What was refuted

- **All single-rotation, pair-rotation, K=3-5 cycle operators on 457**: zero improvers.
- **38-cell patch BB at permutation optimum**: no improvement; boundary-limited not piece-limited.
- **Vol-17 backbone hypothesis**: 12 of 18 cells are basin-specific scan-order artefact, not puzzle-structural.

## Concepts touched

- [[operator-lock]] (introduced + measured rigorously)
- [[mismatch-geometry]] (scan-order correction + backtrack distribution + 764-plateau)
- [[basin-457-pt]] (operator-lock now proven property)

## Implication

To escape 457, need K ≥ 12 (cooperativity bound from vol-18) AND cross-basin operator. Vol-21 introduces relaxed-bound as a strictly-stronger dead-end test.

## Linked memory

- `project_e2_vol20_operator_lock`
- `project_e2_vol20_backbone_correction`
