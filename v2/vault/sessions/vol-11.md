# Session — vol-11

**Theme**: Survey Propagation + boundary-MPS tensor networks. Both refuted; NS-1 quantified.
**Raw**: [[archive/raw/RESEARCH_NOTES_11|RESEARCH_NOTES_11.md]]

## What was attempted

- Full Python BP/SP stack on E2 factor graph (cell × (piece × rotation) encoding).
- 1RSB cavity-method Parisi parameter sweep.
- SP-decimation as solver.
- BP marginals as backtracker value-order.
- NS-1 multiset-equality measurement on 82-board corpus.

## What was measured / kept

- **[[bp-marginals]] cell encoding: 8.4% interior entropy reduction** at convergence.
- **[[survey-propagation]] m-sweep**: lower m → flatter marginals, not sharper. REVERSED from random k-SAT. Confirms E2 is SAT-regime (~1 expected solution), not 1RSB-shattered.
- **SP-decimation best**: depth 125 / score 211 in 316s (m=0.30). Below baseline CP.
- **Backtracker A/B (90s)**: BP value-order loses to random (256 vs 297 max score). Deterministic value-orders correlate failure modes.
- **NS-1 deficit measurements** on 82-board corpus: all 4 known 480 boards satisfy A = B exactly (necessary condition). Plateau boards: Δ ∈ {0, 1, 2, 4}. See [[ns1-deficit]].
- **Hint reach**: each hint piece-id has marginal > 0.01 at only 2-9 cells beyond the hint cell. Information is highly local.

## What was refuted

- **[[survey-propagation]]** on E2: theoretical (cavity assumes locally-tree-like) + empirical (m-sweep wrong direction). Strong refutation.
- **BP marginals as value-order**: random beats them.
- **Local message-passing as sufficient**: foreshadows vol-13's 10¹⁰¹ overcounting finding.

## Concepts touched

- [[bp-marginals]] (cell encoding measured)
- [[survey-propagation]] (refuted)
- [[ns1-deficit]] (corpus measurement)
- [[dead-ends]] (vol-11 empirically confirmed the 2026-05-11 SP verdict)

## Implication

If revisiting BP, use **edge-color encoding** (vol-12 did, 2.24× stronger signal). Cell encoding is exhausted.

## Linked memory

- `reference_e2_bp_measurements`
- `project_e2_ns1_deficit_invariant`
- `project_e2_dead_ends`
