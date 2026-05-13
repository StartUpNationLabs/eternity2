# Session — NIGHT 5 (preprint abstract + falsification framework)

**Theme**: Formalising vol-5/6 findings as a peer-ready paper.
**Raw**: [[../sessions/archive/raw/NIGHT5_ABSTRACT|NIGHT5_ABSTRACT.md]], [[../sessions/archive/raw/NIGHT5_MORNING_BRIEF|NIGHT5_MORNING_BRIEF.md]], [[../sessions/archive/raw/NIGHT5_FINAL_SUMMARY|NIGHT5_FINAL_SUMMARY.md]], [[../sessions/archive/raw/NIGHT5_NEXT_DAY|NIGHT5_NEXT_DAY.md]], [[../sessions/archive/raw/NIGHT5_SYNTHESIS|NIGHT5_SYNTHESIS.md]]

## Output

**Working title**: *Structural sources of the 449/450 plateau in Eternity II local search.*

## Abstract content (preprint draft)

The 5-clue Eternity II puzzle has a published metaheuristic SOTA of 458/480 matched edges (Wauters 2012) that has not been improved in peer-reviewed work since 2019. Local-search algorithms commonly plateau at 449/480; we identify three coupled mechanisms that pin the plateau:

1. **Strain cascade**: asymmetric placement of the 5th hint at (7,8) + 180-symmetric corner hints warp the search backwards (vol-4 hotspot rows 10-13, cols 4-13).
2. **Rare/abundant color class split**: 100% rare-color edges matched in every plateau board; ALL mismatches abundant-color-only (vol-5).
3. **Hamming moat depth ≥ 5**: ~6.6M local-move trials (size 2-4) with zero improvers (vol-5/6).

## Falsification framework

Three falsifiable predictions, each with a designed experiment:

1. **Strain-cascade**: remove (7,8) hint, check if hotspot persists. Status: queued, never executed.
2. **Budget conservation (30-mismatch)**: NE2-iter 3+ rounds, check if total < 31 reachable. Status: queued.
3. **Rare-only invariant**: extreme-score boards (≤ 435 or ≥ 455) for robustness. Status: needs 455+ board (vol-17 calibrated_v17a 447, vol-18 hot-PT 457 satisfied this).
4. **Moat depth ≥ 5**: find any 6-piece simultaneous move improving a 450. Status: vol-18 [[r5f-cooperativity]] CONFIRMED at scale 76 (the 447→456 barrier).

## Concepts touched

- [[strain-cascade]] (formalized as preprint hypothesis)
- [[rare-color-rule]] (100% matched invariant)
- [[r5f-cooperativity]] (later confirmed the moat-depth claim)

## Status

Preprint never finalized; subsumed by ongoing research. The structural findings have aged well (vol-18 confirmed moat); the strain-cascade hypothesis is partly confounded with [[scan-order]] (vol-14 finding).
