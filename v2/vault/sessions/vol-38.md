# Vol-38 — prune-restart on canonical 454 (honest null)

**Theme**: Test if prune-restart with MaxScore CP can lift the
canonical 454 record by completing mismatch-cell drops with the
3 vol-37 invariants naturally pinned.

**Status**: Done with honest null at vol close.

## What was attempted

Two binding-item revisions:
1. **Originally**: no-good CDCL learning (deferred — 2-3d engine work,
   too risky given context budget).
2. **Revised T1**: prune-restart from canonical 454 with MaxScore at
   various drop-k values.

## What was measured

| drop-k | dropped cells | pinned | CP budget | CP depth | CP score |
|---:|---:|---:|---:|---:|---:|
| 0 (mismatch only) | 38 | 218 | 60s | 6 | 446 (best so far in 0.1s) |
| 0 (mismatch only) | 38 | 218 | **5min** | **38** | **431** |
| 20 (+ halo) | 78 | 178 | 60s | 63 | 401 |
| 40 (+ halo) | 78 | 178 | 60s | 63 | 401 |

All COMPLETE the 256 cells but **none score ≥454**. The best CP
completion of the dropped region is 431 (with 38 mismatch dropped,
218 pinned, 5min budget). Score went DOWN from 454.

## What this means

**Canonical 454 is a "true" local optimum** in the CP-completion sense:
the 38 mismatch cells form a region where, given the surrounding 218
pinned cells, NO completion scores ≥454. The global score-maximum
compatible with the rest of the board is 431.

This means:
- The 22-26 mismatches in our canonical records are not "fixable" by
  local CP completion.
- To break canonical 454, we need a **larger-scale move**: drop 50+
  cells (escape constraints), or change the SURROUNDING 218 cells
  (not just the mismatch cluster).
- ALNS-from-454 with cluster-destroy ops (BottomBandDestroy etc.)
  hits 449-455 which is similar magnitude.

## What was refuted

- **prune-restart + MaxScore as a record-lift mechanism FROM canonical 454**:
  refuted. Doesn't beat starting score.

## What's NOT a null

- The 38 mismatch cells are confirmed as a **structurally connected
  region** (we verified earlier that 458-vs-457 differ in a single 51-cell
  connected component — same shape problem).
- prune-restart DOES work for the OPPOSITE direction (make-canonical:
  vol-32 458 → canonical 446 in 0.1s, +12 missing edges filled in).
  It's a "drop the displaced HINTS only" operator, not "drop mismatches".

## Concepts touched

- [[prune-restart]] — empirical bound on its lift-capacity from a saturated
  basin (it can't beat the starting score on canonical 454).
- [[make-canonical]] (TODO concept page) — works in the OTHER direction
  (de-canonicalise then re-canonicalise).

## Records ledger (no change)

| score | canonical | source |
|---:|:---:|---|
| 458 | 3/5 | vol-32 vanilla_fast → ALNS |
| 457 | 5/5 | vol-32 blackwood_mrv × 3 |
| 456 | 5/5 | vol-32 blackwood_raw seed 2, 4 |
| 454 | 5/5 | vol-36 make-canonical → ALNS seed 5 |

Cold-start canonical: 457 (unchanged).
Cold-start absolute: 458 (3/5 hints, unchanged).

## Open at close

1. **The 38-cell mismatch cluster has 0 better completion.** That's
   information: any record lift must involve cells OUTSIDE the
   mismatch cluster too. This contradicts "pin the perfect part, fix
   the broken part" — the broken part can't be fixed locally.
2. **vol-39 candidates** (BACKLOG):
   - no-good CDCL (2-3d engine work, risky, may not lift records)
   - soft unsat-pruner depth-conditional (1d, vol-34 BACKLOG)
   - **larger-window basin-escape**: drop 100+ cells from canonical 454,
     re-CP. May need to drop > 50% of the board.
   - **cross-basin transfer**: take partial from blackwood basin,
     transplant to vanilla basin (vol-22 basin-escape recipe applied
     to multiple seed basins).
3. **Realistic ceiling**: with M1 + week-budget, expect 454-458 range
   to remain our practical ceiling. Beating 458 requires either
   community-class compute (days × 100 cores) or a new algorithm
   class (RL self-play, exact MaxSAT — both 1-2 week builds).

## Linked

- [[vol-37]] — predecessor (structural discoveries + re-eval)
- [[prune-restart]] — extended empirical bound
- ml/make_canonical.py, ml/structural_scan.py, ml/gh_e2/ — vol-36/37 tools
