# Vol-45 — Per-color LP diagnostic + structural refutations

**Theme**: Continue vol-44's structural analysis. Identify which
colors / edges / slots are the bottleneck for the 478 LP UB cap.
Pivot to next-frontier design doc when refinement-research saturates.

**Status**: clean session. Several refinements documented. No record.

## What was built (vol-45 deltas vs vol-44)

- Extended `border_ub.rs` with **per-color y-sum reporting** (the LP
  UB broken down by color k ∈ 1..22).
- Extended `mismatch_map` to **print B-I mismatched edges**.
- New `run_cp_seeded` — generic CP runner with --seed/--profile/--out.
- New `hall_condition` — single-slot supply-vs-demand bipartite check.

## Findings (vol-45)

### F1. Per-color LP UB structure on vol-32 458

| Subgroup | Contribution to interior LP UB |
|---|---:|
| Rare colours 1-5 | 0.000 (structural; rare on border pieces only) |
| Medium 6-10 | 19.0 to 22.84 |
| Common 11-22 | 19.0 to 23.64 |
| **Total** | **363.978** ≈ 364 |

The LP I-I UB is essentially tight (363.98 / 364). The 2-point gap
from 478 to combinatorial 480 is **entirely in B-I** (54.02 / 56),
not I-I.

### F2. 458's mismatch geometry is entirely in bottom band

All 22 mismatches (4 B-I + 18 I-I) are in rows 10-15:
- 4 B-I: between perim y=15 and interior y=14, at x ∈ {2, 3, 7, 14}.
- 18 I-I: rows 10-14, in 10 disjoint clusters of size 2-5.

### F3. Hall condition has NO violations

Per-(side, color) demand vs supply: every (side, color) has
supply ≥ demand. No single-slot infeasibility.

**Conclusion**: the 2-edge LP cap is from **piece-uniqueness
coupling** (one piece serving multiple demands), not single-slot
shortage.

### F4. Bottom-band + perimeter 84-cell MIP returns delta=0

30 min, 84 cells (4 perim + 18 interior + the rest of the bottom
5 rows), warmstart from 458. HiGHS B&B found **no improvement**.

Whether the LP's claimed 2 B-I lift is integer-feasible OR
intractable for HiGHS in 30 min remains open.

### F5. 5-min seeded CP runs do not generate basin diversity

8 CP runs with diverse (seed, profile) at 5min produced **identical**
179-cell partials (303 matched) across 6 of 8 runs. Profile-internal
determinism dominates seed variation. Need ≥ 30 min CP runs and
genuinely-different value-orders to sample new basins.

## Cumulative 458 basin-locking evidence

| Test | Result |
|---|---|
| ALNS-diverse 10min × 24 (vol-40) | 0/24 ≥ 458 |
| ALNS-mega_mix 60min × 8 (vol-44) | 8/8 = 458 |
| MIP cluster halo=0 (28 cells) | PROVEN optimal |
| MIP cluster halo=2 (~16 cells) | delta=0 (likely optimal) |
| MIP union of clusters (28 cells, 1.74s) | PROVEN optimal |
| MIP whole-interior 1h (196 cells) | delta=0 |
| MIP bottom-band+perim 30min (84 cells) | delta=0 |
| 13/13 random k≤3 border perturbations | all decrease LP UB |
| Hall condition | no single-slot violation |

The 458 basin is **firmly locked** at every operator scale tested.

## Pivot frontier

Refinement-grade experiments have saturated. To break 458 we must
pursue a multi-day track:

1. **CP search with LP UB objective** (vol-45 binding item, design
   started in [[cp-with-lp-ub-pruning]]). Multi-day Rust build.
2. **RL self-play for value-order** (vol-30 T2, deferred). 1-2 weeks.
3. **Multi-hour MIP with specialized warmstart** (e.g., warm from
   multiple basins' interiors). Hours of wait per attempt.
4. **Custom propagator that learns from failed branches** (no-good
   CDCL). Multi-day.

## Open questions for vol-46

- Does the CP+LP-UB-pruning approach generate borders with LP UB ≥ 479?
- If yes, can ALNS push them past 458?
- What's the actual LP-UB-maximum reachable border? (Search problem.)

## Linked

- [[vol-44]] — predecessor (extensive)
- [[per-color-lp-ub-458]] — F1
- [[458-class-A-mismatch-structure]]
- [[color-multiset-bound]]
- [[lp-ub-478-basins]]
