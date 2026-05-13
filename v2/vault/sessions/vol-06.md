# Session — vol-06

**Theme**: Border monoculture diagnosis; Las Vegas border sampler; **454/480 historic warm record**.
**Raw**: [[../sessions/archive/raw/RESEARCH_NOTES_6|RESEARCH_NOTES_6.md]]

## What was attempted

- Hard-skeleton solver: keep rare-color cells fixed, search the 32-cell free zone (10²⁵ state space).
- Consensus-threshold sweep across corpus.
- EvalMaxSAT minimal encoder (15× WCNF reduction; see [[inner-k-optimality]]).
- Border-monoculture analysis on community corpus.
- Las Vegas border sampler + transfer-matrix count estimate.
- `pt_e2 --pin-perimeter` flag.

## What was measured / kept

- **Border-monoculture confirmed**: corpus has 3 unique borders dominating, 86% cell consensus. This is why local moves can't escape — everyone starts from the same border.
- **[[border-diversity|Las Vegas border sampler]]**: 100k diverse borders generated in 6s.
- **Corner-tightness surrogate**: weakly predictive of border quality (validated at low compute).
- **HISTORIC RECORD: 454/480** (pt_e2 --pin-perimeter from a 453 seed). Byte-identical across 4 seeds (seed 42, 9018, 18019, 27020) — **deterministic ceiling** for this basin. Saved as `output/HISTORIC_first_454_1778567792.json`.
- **[[inner-k-optimality]]**: EvalMaxSAT proves the 454 board's defect zone is optimal for k = 3, 4, 5.

## What was refuted

- **Hard-skeleton + free-zone solver**: over-rigid; reaches only 357/480.
- **Consensus-seeding**: polishes back to 452.
- **Frame-first border-search (non-corpus borders)**: caps at 449/450; never beats 449 outside the corpus borders.
- **EvalMaxSAT for k ≥ 6**: intractable in 60s.

## Concepts touched

- [[border-diversity]] (introduced)
- [[parallel-tempering]] (with --pin-perimeter, --pin-cells flags)
- [[inner-k-optimality]] (EvalMaxSAT-minimal encoder)
- [[basin-454-vol6]] (new basin page)

## Implication

454 is locally optimal under k ≤ 5 EvalMaxSAT and under standard PT in this basin. To go higher: bigger cooperative moves (see vol-18 [[r5f-cooperativity]]) or different basin entirely.

## Linked memory

- `project_e2_state` (vol-6 row)
