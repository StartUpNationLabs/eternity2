---
name: 459-basin-halo-10-rigidity
description: "Vol-124 2026-05-18: extended the vol-123 halo-N rigidity proofs. Confirmed via kissat that the 459 basin (RECORD_TIE_459_p06) is UNSAT for 480 even at halo-10 — 218 free cells, only 38 cells pinned (essentially the TOP 2 rows of the 459 record). The 480 (if it exists) must differ from this 459 in at least one of those 38 cells."
metadata:
  type: project
---

# 459 basin — halo-10 rigidity (vol-124 extension)

## Background

Vol-123 W-SAT proved via kissat that the 459 basin
(RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json) is UNSAT for any 480
solution at halo-0 through halo-5. That is: even when freeing the 35
mismatch cells + Manhattan-distance-5 neighbors, no valid 480 assignment
extends the pinned remainder.

This volume extends the rigidity result.

## Method

For halo N: starting from the 35 mismatch cells of the 459 record,
free all cells within Manhattan-N. Pin all remaining cells to the 459
record's piece-rotation values. Encode as SAT (with 5 canonical hints
forced) and run kissat.

```bash
python3 scripts/w_sat/sat_unsat_border.py \
    ../data/puzzles/size_16_official_eternity.csv \
    output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json \
    --free-cells halo-N --timeout 600
```

## Results

| Halo | Free cells | Pinned cells | Result | kissat time |
|---|---|---|---|---|
| 0–5 | varied | varied | UNSAT | <2s (per vol-123) |
| 7   | 173 | 83 | **UNSAT** | 0.17s |
| 10  | 218 | 38 | **UNSAT** | 0.31s |
| 15  | 252 | 4  | TIMEOUT | 10min |

## What the halo-10 backbone is

When halo=10 frees 218 cells, the 38 cells that remain pinned are:

- **Hints**: positions 135, 210, 221 (3 of the 5 canonical hints; the
  other 2 hints (34, 45) are inside the halo-10 neighborhood and freed).
- **Top region**: row 0 (16 cells), most of row 1 (15 cells), and 6
  cells from row 2 (positions 32, 34, 39, 41, 45, 47).

Geographically, **the entire top 2 rows of the 459 record are
provably incompatible with any 480 solution**. Any 480 must
substitute different (piece, rotation) values in at least one of
these 38 cells.

## Implications

1. **The 459 basin is rigid up to halo-10.** Any escape attempt that
   only modifies cells within halo-10 of the mismatches CANNOT reach 480.
2. **The 459 basin's TOP region carries the rigidity.** The
   3 canonical hints OUTSIDE the halo are insufficient; the rigidity
   comes from the top 2 rows (38 cells) of the 459 record itself.
3. The community 469 records have their mismatches in different geographic
   regions (per vol-14 "scan-order-determined" geometry). The 459 basin's
   incompatibility may be specifically about *this top region*.

## What this DOESN'T prove

- Whether canonical E2 has a 480 solution at all (halo-15 timed out;
  the full SAT is still undecided).
- Whether all 459 boards have this same top-region rigidity, or just
  this specific RECORD_TIE_459_p06.

## Next steps

- Halo-15 with a much longer kissat budget (multi-hour) to determine
  whether full-board freedom is SAT or UNSAT.
- Test the same halo-10 rigidity on OTHER 459 boards from our corpus
  (vol-110 NEW_459_from_off100_pipeline boards).
- If different 459 boards have DIFFERENT halo-10 backbones, **the
  intersection** is the smallest provably-rigid region — and any 480
  must lie outside that intersection.

## Linked

- [[w-sat-459-unsat-findings]] (the vol-123 base)
- [[w11-sat-correctness-validated]] (kissat encoder validated)
- [[../sessions/vol-124-portfolio-results]] (vol-124 broader attack)
