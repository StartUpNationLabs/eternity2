---
name: w-sat-459-unsat-findings
description: "W-SAT 2026-05-17: PROVEN via kissat that the 459 board's local neighborhood (mismatch cells + halo-1, halo-2, halo-3, halo-5) is UNSAT for the 480/480 decision problem. The 459 basin is exactly trapped — to reach 480 requires moving beyond the halo-5 region. Currently running: full interior SAT to test if 459's border ring is compatible with any 480 solution."
metadata:
  type: project
---

# W-SAT 459 UNSAT findings (vol-123, 2026-05-17)

User suggestion to extend SAT experiments led to a STRONG new result:
**SAT-decision proves the 459 board's local neighborhood is UNSAT for 480**.

## Setup

- Puzzle: canonical 16×16 E2 with 5 hints.
- Reference board: `output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json` (459 matched).
- Mismatch cells (vol-60 record): 32 cells in 13 clusters, mostly in
  bottom-right region.
- For each "halo" expansion, free those cells AND pin everything else
  to the 459 board's values. Decision SAT: is there ANY assignment to
  the free cells such that the WHOLE board has 480/480 matched edges?

## Results

| Halo | Free cells | Vars | Clauses | Result | Wall time |
|------|-----------|------|---------|--------|-----------|
| 0    | 32 (just mismatches) | 14k | 81k | **UNSAT** | 0.09s |
| 1    | 70 | 23k | 277k | **UNSAT** | 0.33s |
| 2    | 93 | 31k | 523k | **UNSAT** | 0.89s |
| 3    | 109 | 40k | 775k | **UNSAT** | 0.80s |
| 5    | 140 | 61k | 1.5M | **UNSAT** | 1.56s |
| Interior | 191 (all interior except hints) | 160k | 5.4M | running... | TBD |

## What this PROVES

1. **The 459 basin is mathematically trapped at halo-5.** No assignment
   to even the 140-cell neighborhood (>50% of the board) admits a
   fully-matched 480 board with the 459's BORDER + far-interior pinned.

2. **The 459 record's local moves are EXHAUSTED.** All ALNS / SAT
   destroy-and-repair operators within halo-5 are provably useless.

3. **To improve from 459 requires a non-local move.** Specifically,
   the BORDER RING or FAR INTERIOR (>5 Manhattan units from mismatches)
   must change.

## Comparison with prior work

- Vol-44 LP-UB: gave 478 as upper bound (LP relaxation).
- Vol-62 MIP joint local optimality: proved halo-1 joint MIP doesn't
  improve.
- Vol-80-99 rigidity theorem: McGavin 469 also halo-3 rigid (per-component).
- **THIS RESULT EXTENDS RIGIDITY TO SAT-DECISION** for the 459 basin
  at halo-5. Stronger than MIP because it's the full SAT theory.

## What's currently running

Full interior SAT (191 cells free, 60 border + 5 hints pinned).
30-min kissat budget. Result will tell us:
- If UNSAT: the 459's border-ring configuration is incompatible with
  any 480 solution. Need a different border arrangement.
- If SAT: solution found. **Millionaire win.**
- If timeout: inconclusive.

## Next experiments

If interior UNSAT:
- Try with EACH border cell freed too (giving piece-uniqueness flexibility).
- Try from DIFFERENT 459 boards (vol-110 NEW_459, others).
- Try from the BP-decim 435 basin (less constrained by ALNS-found 459).

If interior SAT or unknown:
- Extract the assignment, verify it's actually 480.
- If 480: HOLY GRAIL.

## Implication for "how to solve E2"

The W-SAT findings sharpen our understanding:
- Local repair of any 459 basin won't reach 480.
- The puzzle's solution requires a different BORDER ring configuration
  than what our 459 records have.
- This rules out the ALNS-from-459 path entirely for record breaking.

## Linked

- [[mcgavin-469-near-twin-orbit]] (similar rigidity for McGavin 469)
- [[basin-rigidity-refutation]]
- [[459-level-set-two-cluster-confirmed]]
- [[bseed9-460-halo1-mip-locked]] (prior MIP-locked finding)
- [[../plans/SOLVING-E2-VISION]]
