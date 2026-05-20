---
name: cp-with-lp-ub-pruning
description: sampled basins. Breaking 458 requires finding a basin with LP UB ≥ 479.
status: unbuilt
metadata:
  type: concept
---
# CP search with LP-UB pruning (design doc)

**Status**: unbuilt. Designed during vol-45 close.
**Origin**: vol-44/45 found that LP UB 478 is a robust ceiling on all
sampled basins. Breaking 458 requires finding a basin with LP UB ≥ 479.

## Motivation

The space of canonical-E2 5-clue partial-border placements is
combinatorially huge (4 corners × 56! edges). Most placements yield
LP UB ≤ 478. The few-to-zero placements with LP UB > 478 are needles
in a haystack.

**Hypothesis**: a CP-style backtracking border-placement search that
at each placed cell *evaluates a fast LP UB lower-bound* and prunes
branches whose UB drops below a threshold T (e.g., T = 479) might
efficiently isolate high-UB borders.

## Architecture

### Search tree

- Variable: position $p \in $ perimeter (60 cells).
- Domain: which (piece, rotation) goes at $p$.
- Order: corners first (fixes 4 cells), then edge ring cells in some
  canonical order (e.g., top row left-to-right, then right column,
  bottom row right-to-left, left column).

### Pruning condition

At each placement, compute a **fast lower-bound on LP UB** given the
partial border. If lower-bound < T, prune.

The "fast LP UB" need not be the full LP. Options ordered by cost:

1. **Combinatorial count** (vol-44 found = 480). Constant. Useless.
2. **Color-supply count** with current partial border colors fixed.
   Subtract colors locked-out by partial border. ~ms.
3. **Hall-condition** per (side, color). ~ms.
4. **Reduced LP** with only B-B + B-I edges + fixed pieces. Drop the
   I-I LP entirely. ~10-100 ms.
5. **Full LP**. ~150 s. Only at leaves.

### Phased approach

- PHASE 1 (depth ≤ 30): aggressive cheap pruning (options 1, 2, 3).
- PHASE 2 (30 < depth ≤ 55): reduced LP (option 4).
- PHASE 3 (depth = 60, full border): full LP (option 5).

At each leaf with LP UB ≥ T, save the border + record it for later
ALNS exploitation.

## Open mathematical questions

1. **What's the *partial* LP UB?** Given $k$ cells of the border
   placed, what's the LP relaxation of the *remaining* problem?
   Well-defined; handles empty border slots, pool remainders, partial
   B-I demands.

2. **Is the partial LP UB monotonic in placements?** Yes (proof sketch):
   each placement *adds* constraints (the placed piece's color forces
   specific B-I matches), and adding constraints to a max-LP can only
   decrease the optimum. So the partial UB at depth $k$ is an
   over-estimate of the final UB at depth 60. Pruning at depth $k$
   with threshold T is **safe**: any leaf surviving has UB ≥ pruning
   threshold or lower.

3. **What's the right threshold T?**
   - T = 478: no filter (every known basin passes).
   - T = 479: filter EVERY known basin (max observed 478). Aggressive.
   - T = 478.5: keep only borders with LP UB ≥ 478.5 — likely most
     filtered, leaves the few "almost 480" candidates.

4. **Branching factor estimation**: 4 corner pieces × 4 positions ÷
   global rotation 4 ≈ 4 corner arrangements after symmetry break.
   Then 56 edge pieces in 56 positions, but many color-compat
   constraints prune fast. Empirically: 1-shot edge placements
   typically have ≤ 5 valid rotations per (piece, position) combo.
   Effective branching factor ~10-30 per placement after pruning.

## Implementation skeleton (Rust)

```
// In a new crate: crates/cp-lp-search/src/lib.rs

pub struct CpLpSearchOpts {
    pub threshold_ub: f64,
    pub phase1_depth_max: u32,  // 30
    pub phase2_depth_max: u32,  // 55
    pub time_budget_secs: f64,
    pub threads: u32,
    pub save_dir: PathBuf,
}

pub struct CpLpResult {
    pub n_explored: u64,
    pub n_pruned_cheap: u64,
    pub n_pruned_lp: u64,
    pub n_solutions_found: u64,
    pub best_lp_ub_seen: f64,
}

pub fn run_cp_lp_search(puzzle: &Puzzle, hints: &Hints, opts: CpLpSearchOpts)
    -> Result<CpLpResult, String>;
```

## Cost estimate

- Skeleton + cheap pruning + symmetry break: 1-2 days.
- Reduced LP at depth 30-55: 1-2 days (incremental LP setup).
- Full LP at leaves: trivial (re-use existing `border_ub::lp_ub`).
- Tuning + benchmarking: 1 day.

**Total: 3-5 days of focused Rust dev.**

## Expected outcome

Either:
- (A) Search produces borders with LP UB > 478. Worth ALNS push.
- (B) Search exhausts and finds nothing > 478. **Then we have a
  near-proof that 478 is the LP-UB ceiling for canonical 5-clue.**

Both outcomes are valuable research.

## Linked

- [[lp-ub-478-basins]]
- [[border-enum-lp-ub]] — full LP math
- [[per-color-lp-ub-458]]
- [[vol-45]] — design originated here
