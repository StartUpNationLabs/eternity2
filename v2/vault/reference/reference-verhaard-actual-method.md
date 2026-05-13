---
tags: [reference, method]
status: documented
---

# Reference — Verhaard's actual method

Mirror of memory `reference_verhaard_actual_method`. Authoritative content lives in [[verhaard-set-sa]].

## TL;DR

Verhaard's actual 467-on-5-clue algorithm (groups.io msg 105190116, 2008-04-11) is **set-composition swap-annealing**:

1. Pick a random ~180-190-piece subset of the 196 interior pieces.
2. Swap-anneal subset composition under the **2×2-tiling-count metric** until local optimum.
3. The 10-20 worst performers form the "loser group".
4. Backtrack the first ~80 placements preferring loser-group pieces (front-load the hard pieces).
5. Remaining 170-180 pieces searched in the sub-tree under that 80-piece scaffold.

## Vol-7 correction

Vol-7's recorded "2×3" granularity was wrong — it's **2×2** per Verhaard's own words. Probably came from a downstream summary.

## Tilability metric

Count of 2×2 sub-tilings achievable on the candidate set. O(n⁴). Verhaard validated R² = 65% with `log(total 2×2 tilings)` on random subsets.

## Linked

- [[verhaard-set-sa]] — full method page
- [[reference-community-e2-ceiling]] — 469 is the actual ceiling now
- [[reference-blackwood-decoded]] — what moved the ceiling 467 → 469
