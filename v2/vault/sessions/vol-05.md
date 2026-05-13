# Session — vol-05

**Theme**: GA crossover (450 → 453); rare-color 100% invariant; 30-mismatch budget.
**Raw**: [[../sessions/archive/raw/RESEARCH_NOTES_5|RESEARCH_NOTES_5.md]]

## What was attempted

- New crate `crates/ga/`: 4×4 region crossover ("[[genetic-algorithm|GA-light]]") + 6×6 ("GA-LARGE").
- 3-hour GA-LARGE cascade with PT mutation between generations.
- NE1/NE2 soft penalty operators (no-go penalty + iterative deepening).
- ALNS destroy-repair at 4×4, 5×5 scales.

## What was measured / kept

- **GA-LARGE reaches 453/480** in 3-hour cascade. 10 published distinct boards on 2-3 basin families.
- **3 of 8 replicas momentarily reach 454** but fall back — 454 is achievable but unstable from these basins.
- **[[rare-color-rule|Rare-color 100%-matched invariant]] discovered**: in every plateau board (≥440), all 24×5 = 120 rare-color edges are matched. ALL mismatches are abundant-color-only.
- **30-mismatch structural budget**: total mismatch count stays approximately conserved across NE1/NE2 moves.
- EvalMaxSAT confirms center-k optimal for k ≤ 5 (extends in vol-6 to 45-cell zone; see [[inner-k-optimality]]).

## What was refuted

- **Soft-penalty (NE1/NE2)**: conserves budget, redistributes mismatches without reducing total. No score lift.
- **ALNS at 4×4/5×5 scale**: hits [[r5f-cooperativity|Hamming moat depth ≥ 5]]. ~6.6M trials of 2-4-piece moves: zero improvers.
- **TA polishing on PT-converged boards** (Wauters 2012 style): basins already exhausted, zero improvement.
- **Consensus-seeding within family**: 452-basin trap.
- **Anti-consensus exploration**: wrong target; corner-hint edges dominate.

## Concepts touched

- [[genetic-algorithm]] (introduced)
- [[rare-color-rule]] (100% matched invariant established)
- [[mismatch-geometry]] (30-mismatch budget refinement)
- [[r5f-cooperativity]] (the moat-depth empirical floor)

## Implication

Within-family crossover saturates at 453. Vol-6 must look at **between-family** diversity (different borders).

## Linked memory

- `project_e2_state` (vol-5 row)
