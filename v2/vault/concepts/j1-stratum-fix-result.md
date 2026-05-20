---
name: j1-stratum-fix-result
description: "J1 stratum-fix empirical result: freezing rows 0..K and rebuilding K+1..15 with column-DP recovers J1-chain-no-FLH score (444) regardless of K. FLH gives +3 at last band; stratum-fix doesn't preserve that. Conclusion: lower-stratum loss is greedy-horizon, not piece-supply, dependent."
metadata:
  type: project
status: built
---

# J1 stratum-fix — empirical results

## Setup

`j1_stratum_fix` binary loads a J1 board, freezes rows 0..=K, and runs
J1 column-DP on rows K+1..=15 with the interface row fixed and the
remaining piece set.

## Tests (input = J1 FLH board, 447/480)

| freeze_through | rebuild | result | band-14 score | notes |
|---|---|---|---|---|
| 14 | row 15 only | 447/480 | 38 | reconstructs exactly: trivial case |
| 11 | rows 12-15 | 444/480 | 35 | -3 vs input |
| 7 | rows 8-15 | 444/480 | 35 | -3 vs input |

## Diagnosis

The stratum-fix Rust binary uses **greedy beam (sort by current band
score)** to advance band-by-band. This is the SAME algorithm as the
original `j1_chain_dp` WITHOUT FLH.

Result: stratum-fix matches the non-FLH chain (444/480) regardless of
freeze depth.

**The FLH +3 is the real algorithmic win.** The stratum-fix bound
$E_{\text{lo}}^{\text{internal}} = 215$ for a 463-record board would
require a search algorithm that does better than greedy beam — which
FLH partially does, but only at the very last band.

## Refutation (partial)

The theorem in [[j1-stratum-fix-repair-theorem]] gave a sound bound but
the construction (greedy J1 column-DP on lower stratum) does not
reach it. The bound is $\le E_{\text{lo}}^{\text{internal}} = 232$;
greedy J1 reaches $196$; we are 36 short of bound, same as J1 itself.

So: stratum-fix with greedy column-DP **does not provide an algorithmic
gain over J1 chain**.

## What stratum-fix DOES rule out

- It confirms that the upper-stratum-frozen piece set is a HARD
  constraint: the 128 leftover pieces simply have a piece-supply /
  color-distribution that makes 36 missing edges unavoidable in greedy
  beam.
- ALNS-on-J1-board sees the same constraint and likely won't improve
  much; the upper stratum 232+16 = 248 edges are TRUE local maxima.

## Pivot: where to look next

1. **MIP on lower stratum.** The piece-permutation-rotation search on
   128 pieces with fixed interface is a constrained matching problem.
   A MIP formulation (binary $x_{p,c,r}$ for piece $p$ at cell $c$ with
   rotation $r$ + matching constraints) could PROVE the local-optimum
   ceiling at $E_{\text{lo}}^{\text{internal}} \le \tau$ for some $\tau$.
2. **Multi-start FLH on lower stratum.** Instead of one FLH+chain, do
   FLH at EVERY band (not just the last), with random tiebreaking.
   Sweep across $\beta$ in the FLH weighting.
3. **Stratum-fix-with-FLH (proper).** Implement FLH inside the
   stratum-fix bin's solve_band. This is the immediate ablation.
4. **Pivot upward**: rebuild the UPPER stratum from the J1 board's
   LOWER stratum. The math may favor doing this in either direction.

## Linked

- [[j1-stratum-fix-repair-theorem]]
- [[j1-loss-localization-math]]
- [[j1-forward-look-heuristic]]
- [[j1-rust-beam100k-first-complete-board]]
