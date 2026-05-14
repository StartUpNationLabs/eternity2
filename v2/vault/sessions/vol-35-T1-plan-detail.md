# Vol-35 T1 detailed plan — brute-force LO enumeration at 4×4/6×6

**Status**: drafted at vol-34 close based on vol-35-prep findings.

## Premise

Vol-34's landscape-pilot showed that ALNS-from-random produces
essentially uniformly-spread LOs at 6×6/5c — no clustering, no
big-valley FDC structure. This refutes naive "sample-and-cluster"
plans.

BUT: at 12×12/8c the FDC weakly emerges (r=-0.104). The canonical
16×16 probe (in flight at vol-34 close) will measure the canonical
FDC.

If the canonical FDC IS meaningful (r << 0), then the simple
"ALNS-from-random" approach fails at 6×6 because the puzzle is
too small for meaningful structure, but the same approach should
work at canonical. We can't validate that with brute-force LO
enumeration at 16×16 (computationally infeasible).

## The actually-tractable plan: small-puzzle brute force

At 4×4/4c there are 16 cells and 16 pieces. Total raw configurations:
16! × 4^16 ≈ 9×10²² configurations.

But the SEARCH TREE with edge-color forward-checking + piece-uniqueness
is MUCH smaller. vanilla_fast (or its 4×4 analog) would explore
maybe 10⁵ - 10⁷ search-tree leaves.

For each *complete* configuration the search visits, check:
- Score (matched edges, max=24).
- LO-ness: try all single-piece swaps with all rotation pairs (16
  choose 2 × 16 rotation combos = 1920 swaps per board). If any
  improves the score, this board is NOT a LO.

Algorithm:
1. Enumerate all complete configurations (i.e., let backtracker
   run to leaf, record, backtrack).
2. For each, score and store as (score, config).
3. Post-process: for each, check LO-ness; keep only LOs.
4. Cluster LOs by Hamming.

## What this gives us that ALNS-from-random doesn't

- **Complete** LO set (no sampling bias).
- **Exact** basin sizes (for each LO, count boards in basin via
  per-pair LO check).
- **Exact** saddle-point heights (for adjacent LOs, the barrier
  height = score-difference of the lowest-score config between them).

This data, combined with the same measurements at 6×6/5c, lets us
compare landscape PROPERTIES across scales (e.g. "fraction of LOs
in the global cluster" vs puzzle size).

## Cost

4×4 brute-force completion enumeration:
- Search tree maybe 10⁵-10⁷ leaves. At vanilla_fast 125M pp/s,
  even 10⁹ ops is 8 seconds. Feasible.
- Per-leaf LO check: 1920 swaps × O(1) score-recompute = ~100 μs.
  At 10⁵ leaves = 10 seconds total.

6×6 brute-force completion enumeration:
- Search tree probably 10⁸-10¹⁰ leaves. 10¹⁰ ops at 125M/s = 80 sec.
- Per-leaf LO check: 36 choose 2 × 16 = 10,080 swaps × O(1) = ~1 ms.
  At 10⁸ leaves = 28 hours. NOT feasible.

So: 4×4 is fully enumerable; 6×6 is not.

**Alternative for 6×6**: sample LOs from random starts, but use a
MUCH stronger LO-check (no swap + no rotation + no 2-cell-cycle
improves the score). This gives "stronger" LOs which may cluster.

## Implementation

`crates/bench-audit/src/bin/landscape_brute.rs`:
- Adapt vanilla_fast's row-major backtracker to size-parametric
  (compile-time const N, monomorphized for N=4 and N=6).
- Replace early-stop with continue-on-leaf (record + backtrack).
- Per-leaf: call piece_swap_hillclimb (already in localsearch); if
  it returns the same board, this leaf IS a LO.
- Save all LOs to disk.

Cost: 1 day code + 1 day analysis at 4×4. 6×6 requires a different
approach (see "Alternative" above).

## What we hope to find at 4×4

- Total LO count (likely 10²-10⁴ — much less than the raw 10²² config
  space, but more than the ~30 global solutions).
- Basin-size distribution (some LOs attract many random starts, some
  attract few).
- For the TOP-K LOs (highest scores), measure their Hamming
  neighbours. Are high-score LOs CLUSTERED in configuration space?
- FDC computed on the EXACT LO set.

If the exact-FDC at 4×4 is much more negative than the random-sample-FDC,
that's evidence that ALNS's LO-sampling has bias.

## Open questions

- Can we generalize vanilla_fast to const-N at the type level without
  rewriting? Or do we accept a separate bin per size?
- For 4×4 the result might be uninteresting because the puzzle is too
  small to have meaningful structure (similar to 6×6's null result).
  In that case the brute-force at 4×4 was wasted compute. Mitigation:
  run a quick smoke first (50 inits × 60s ALNS) to estimate the LO
  count before committing to full enumeration.

## Vol-35 T1 binding gate

Produce, for each of 4×4/4c, 6×6/5c, 8×8/5c, a LANDSCAPE FACT FILE:
- LO count (exact at 4×4; sampled at others)
- Score distribution
- FDC value
- Cluster count at H ≤ N/4

Use this to PREDICT the canonical-E2 landscape properties without
having to brute-force enumerate it (impossible).

If the predictions match the 50-restart canonical-E2 probe (already
in flight), the small-puzzle landscape mapping is validated as a
predictive tool. Vol-35 T1 PASS.

If they don't match, vol-35 T1 FAIL — but we'd have learned that
landscape structure is fundamentally non-monotonic with scale, which
is itself useful.
