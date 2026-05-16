---
name: corpus-restricted-region-mip-locked
description: "Vol-119 T5 — INVENTION: corpus-restricted region MIP. Instead of vol-44's full-piece MIP (4 pieces × 196 rotations per cell), restrict free-region cell choices to a corpus of observed basin placements (mean 5 options/cell). MUCH FASTER (0.04s vs 1h) and proves same kind of local optimality. Vol-60 459 at halo-2 PROVEN OPTIMAL; vol-60 459 at halo-8 (191 of 256 cells free) PROVEN OPTIMAL. bseed9 460 (1-clue variant) at halo-2 PROVEN OPTIMAL."
metadata:
  type: project
---

# Corpus-restricted region MIP (vol-119 T5)

## Method

For a target board `B0` and a corpus `{B1, ..., Bk}`:
1. Identify mismatch cells in `B0`.
2. Expand to halo-K: `free = mismatch ∪ {neighbors_K}`.
3. Pin all cells outside `free` to `B0`'s (piece, rot).
4. For cells in `free`, allow choosing from the **union of corpus
   options** at that cell (typically 4-7 (piece, rot) pairs).
5. MIP: max matched edges, subject to piece-uniqueness across `free`
   (pieces already pinned cannot be chosen).

Implementation: `scripts/vol119_region_basin_mix_mip.py` using PuLP +
CBC.

## Why faster than vol-44's full-piece MIP

Vol-44's `cluster_repair_458` formulation uses ALL 196 interior pieces
× 4 rotations as cell choices, so each free cell has ~784 options. The
196-cell whole-interior MIP took 1h and didn't prove optimality. The
28-cell halo-1 took 1.74s.

Corpus-restricted MIP at the same free regions has mean 5.2 options/cell.
The x-var count drops ~150×, and the y-var (edge match indicator) count
drops similarly. CBC handles even halo-8 (191 free cells) in ~30s.

## Result on canonical 459 record

10-board corpus: 5×459 (4 cluster-A + 1 cluster-B = vol-60 RECORD) +
3×457 (vol-32 RECORD_TIE) + 1×458 (vol-32 RECORD_BREAK) + 1×460 (bseed9).

| Target            | Halo | Free cells | Result      | Wall |
|-------------------|-----:|-----------:|------------:|-----:|
| vol-60 459        |    2 |         77 | Δ=0 (459)   | 0.04s |
| vol-60 459        |    4 |        127 | Δ=0 (459)   | <1s |
| vol-60 459        |    8 |        191 | Δ=0 (459)   | ~30s |
| bseed9 460 (1cl)  |    2 |         85 | Δ=0 (460)   | 0.96s |

**Even with 75% of the board "free" to choose from any of 10 basins'
observed options, the MIP optimum stays at the base board's score.**

## Significance

Strengthens vol-44/95/100 local-optimality findings:
- vol-44/95/100: MIP-locked under ALL piece-rot rearrangements (full
  search space), but only on small regions (≤ 56 cells).
- This: MIP-locked under CORPUS-RESTRICTED rearrangements, but on
  MUCH larger regions (191 cells). Different optimality flavor.

The two complement: full-piece MIP shows local rigidity is REAL
(no piece-permutation breaks it). Corpus-restricted MIP shows it
also holds when restricted to observed basin variations across
DIFFERENT basins from DIFFERENT pipelines.

Together: 459 is **multi-basin observable-variation locally optimal**
on the 16×16 grid at all tested halo radii.

## What this does NOT prove

- 459 may still be beatable by piece-rot combinations not present in
  any of the 10 corpus boards. New algorithm runs could discover
  them.
- The MIP doesn't certify global optimality — just local optimality
  in the corpus-restricted neighborhood.

## Pending

- T1 sweep enlarges corpus to ~20-30 basins. Re-run halo-8 region MIP
  on enlarged corpus. If still 459, lock is even more robust.
- Test on bseed9 with halo-4 / halo-8.
- Apply to 457 records (test if 457 lifts to 458 via corpus-MIP).

## Linked

- [[basin-mix-mip-refuted]] (vol-112 base case)
- [[sigma-subset-bound-empirically-tight]] (companion T3 finding)
- [[../sessions/vol-119]]
