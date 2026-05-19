# Current Volume — Vol-155

**Theme**: PRIOR — empirical-frequency informed beam value ordering.
Augments V151 beam search with a (piece, position) prior extracted
from the 1278 high-score DB boards.

V152-V154 explored coupling-aware inventions:
- V152 HARMONICS refuted (matching cannot decouple from layout).
- V153 BRAID wont-do (warp-weft reduces to row-major-beam).
- V154 DLX-XCC bug-fix attempt: partial (3x3 works, 4x4 still fails);
  pivoted to xcover library validation (8x8/c4 in 0.04s; 12x12/c12
  scaling test running).

PRIOR is the **first data-augmented constructive builder**. Pure
from-scratch but informed by the corpus distribution.

## Binding items (3 max)

1. **Build prior matrix** from `database-400-480/`. 256×256 piece-cell
   frequency table. Save as JSON for Rust binary consumption.
2. **Modify v151_weaving_beam** to optionally accept a prior file and
   use it as tiebreak in candidate sorting.
3. **Measure**: K=1024 PRIOR vs K=1024 plain. Same wallclock.

## Kill-criteria

- Build at K=1024 PRIOR scores ≤ 455 (no lift) → refute as
  "corpus statistics don't transfer".
- Build at K=1024 PRIOR matches a specific basin too closely (= identical
  to one of the 18 basin families) → not really from-scratch; refute.

## Days budget

1 day. Prior is a small Python script; Rust modification is 50 lines.

## Linked

- [[../sessions/vol-155]] (to create)
- [[../concepts/prior-data-augmented-beam]] (created)
- [[../sessions/vol-151]] (V151 baseline 455)
- [[INVENTION_NAMES_2026-05-19]]
