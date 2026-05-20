---
name: v186-pool-biased-top-down
description: V184 LIGHTHOUSE (hard interface) failed: 0/1024 valid pairs.
status: refuted
metadata:
  type: concept
---
# V186 Pool-Biased Top-Down — LIGHTHOUSE wall fix design

Status: **refuted** — built + tested at γ ∈ {0.5, 2.0}; pool-bias shifts which pieces top consumes but does NOT fix the structural row-12 wall.
Origin: vol-186 (after V186-T1 LIGHTHOUSE-SOFT row-12 wall refutation).

## Problem

V184 LIGHTHOUSE (hard interface) failed: 0/1024 valid pairs.
V186 LIGHTHOUSE-SOFT (soft interface, ≤ 4 N-edge mismatches) ALSO failed
— but not at the interface. The wall is at **row 12** (bottom-up direction)
because the residual piece pool (256 − pieces-in-top) cannot form a valid
chain through rows 12–14.

This is the same wall as V183 SEMAPHORE.

## Hypothesis

The top-down search greedily picks pieces that maximize edge-matches in
the top half, **without regard for whether the bottom half can still be
built**. Some pieces are *globally bottom-row-critical* (their edge colors
make them rare and necessary for rows 12–15); when top-down consumes
them, no bottom completion exists.

A pool-biased top-down search penalises consumption of bottom-critical
pieces.

## Math

### Bottom-criticality score

For piece $p$ with edges $(N, E, S, W)$ over all 4 rotations, define the
**bottom-row affinity** $\beta(p)$ as the corpus-empirical frequency of
$p$ being placed in rows 12–15 across our ≥440 corpus:

$$
\beta(p) := \frac{1}{|\mathcal{B}_\tau|} \sum_{b \in \mathcal{B}_\tau} \mathbb{1}\big[\, \text{row}_b(p) \in \{12, 13, 14, 15\}\,\big]
$$

For canonical corpus boards (≥440 score, $B = 938$), $\beta(p) \in [0, 1]$.
We expect ~16 pieces with $\beta > 0.5$ (highly bottom-row-preferred) and
the rest below.

### Pool-bias penalty

The top-down beam ranker (V155 / V181 KEYRING) maximises a score $R(b)$.
We add a penalty term:

$$
R'(b) = R(b) - \gamma \sum_{p \in \text{used}(b)} \beta(p)
$$

with $\gamma \in [0.1, 1.0]$ to be calibrated.

This makes the top-down beam prefer pieces that are **NOT** typically in
the bottom half, **leaving bottom-critical pieces for the bottom-up
search**.

### Symmetric variant

For full bidirectional, define top-criticality $\tau(p)$ analogously
(rows 0–3). The bottom-up beam uses $R'(b) = R(b) - \gamma \sum_{p}
\tau(p)$.

### Expected effect

If the row-12 wall is caused by 5–10 pieces being globally bottom-critical
but consumed in the top half, then:

- Without bias: top consumes 0–5 of those pieces (whichever fit edge
  constraints); bottom-up starves at row 12.
- With bias $\gamma = 0.5$: top avoids those pieces, takes ≤ 1 of them;
  bottom-up has the full bottom-critical pool, survives to row 8.

The cost: top-half score drops because we're picking sub-optimal pieces
there. Empirically, vol-181 KEYRING reached top-7 score 232 — a 5-point
drop (to ~227) at the top should be acceptable if it enables the bottom
to score 200+ instead of starving.

## Implementation plan

1. Compute $\beta$ from existing corpus matrix `scripts/v155_prior/prior_matrix_high459.json` (just sum rows 12–15 per piece).
2. Add `--bottom-bias gamma` flag to `v186_pool_biased_lighthouse.py` (fork of `v186/build_bidir_soft.py`).
3. Sweep $\gamma \in \{0.1, 0.3, 0.5, 1.0\}$ × 4 meet-rows {6, 7, 8, 9}.
4. Measure: does bottom-up reach row M with score > 0 for any (γ, M) pair?

## Status pivot trigger

If γ sweep still hits row-12 wall on > 50% of top states, the
piece-pool problem is **structural**, not pool-allocation. In that case
the next angle is **joint top+bottom search** with shared piece-pool
constraint — much heavier compute but no greedy partition.

## Empirical result (vol-186 close)

Built `scripts/v186_lighthouse_soft/build_pool_biased.py` + computed
β-affinity (31 pieces with β > 0.5 across rows 12–15).

| γ_top | β-top10 used in top half (out of 31) | bottom-up wall row |
|---|---|---|
| 0.0 (baseline) | ~5 | row 12 |
| 0.5 | 2 | row 13–14 (mixed) |
| 2.0 | 1 | row 13–14 (mixed) |

The bias is **measurably effective** — top-down consumes fewer
bottom-critical pieces — but the wall persists. The row-12/13/14
infeasibility is therefore a **structural edge-chain constraint** between
adjacent rows, not just a piece-pool issue.

This is the same wall as V183 SEMAPHORE just shifted by 1 row due to
bias. Genuine refutation of pool-bias as an independent fix.

## Refutation

The piece-pool problem has TWO layers:

1. **Which pieces are in the pool** (pool-bias fixes this — measurably).
2. **Whether the edge-chain S-constraint at row r can be satisfied with
   the current pool** (the structural wall — pool-bias does NOT fix
   this).

Layer 2 is the wall. The bottom-up beam at row r demands a 16-element
chain whose S-edges match row r+1's N-edges; even with the "right"
pieces available, valid chains may not exist.

This is fundamentally the same obstruction as V184 LIGHTHOUSE: the
interface match is 16 tight constraints on a discrete alphabet of 22,
which has near-zero hit rate without coordination between the two halves.

## Linked

- [[lighthouse-bidirectional-row]] (V184/V186-T1 refutation)
- [[semaphore-row-hungarian]] (V183 row-10 wall, same family)
- [[keyring-patch-prior]] (V181 ranker we'd extend)
- [[prior-data-augmented-beam]] (V155 corpus prior)
