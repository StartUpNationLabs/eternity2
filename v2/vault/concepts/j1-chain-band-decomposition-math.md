---
name: j1-chain-band-decomposition-math
description: "J1 chain-bands math: theoretical max score from sequential band processing. Each band 1+ adds 2·side - 1 new edges (next row's horizontals + next row's verticals to prior row)."
metadata:
  type: project
status: built
---

# J1 — Chain-Bands Decomposition (Math)

## Setup

A board is $n \times n$ with $n^2$ cells. Total internal adjacencies:
$$
E = 2n(n-1)
$$
For $n=16$: $E = 480$.

A "band" $r$ covers rows $r, r+1$ ($2n$ cells, $n$ columns).

Within band $r$ alone, the maximum matched edges = $3n - 2$:

- Top row horizontals: $n - 1$.
- Bottom row horizontals: $n - 1$.
- Vertical matches between top/bottom row: $n$.
- Total: $2(n-1) + n = 3n - 2$.

For $n=16$: $3 \cdot 16 - 2 = 46$. ✓

## Chained band processing

Process bands sequentially: band $0$ (rows $0, 1$), band $1$ (rows $1, 2$),
..., band $n-2$ (rows $n-2, n-1$). Each band $r$ has its top row FIXED from
band $r-1$'s bottom row.

**Per band, what's NEW (not yet counted)**?

For band $0$: all $3n - 2$ edges are new = $46$.

For band $r \geq 1$: the top row was already placed by band $r-1$.
The TOP row horizontals were ALSO counted in band $r-1$'s bottom row
horizontals. So:

New edges in band $r \geq 1$:
- Bottom row (new) horizontals: $n - 1$.
- Vertical matches between (fixed) top row and (new) bottom row: $n$.
- Total NEW: $2n - 1$.

For $n=16$: $2 \cdot 16 - 1 = 31$ new edges per band $r \geq 1$.

## Total maximum if all bands achieve perfect

$$
E_{total\ chain} = (3n - 2) + (n - 2)(2n - 1) = 3n - 2 + 2n^2 - n - 4n + 2 = 2n^2 - 2n = 2n(n-1) = E
$$

So **if all bands achieve perfect**, the total = $E = 480$. The chain
can in principle reach a perfect tiling.

## But: chained PERFECT is NOT guaranteed even if standalone PERFECT is

Band $0$ achieves $46/46$ standalone, committing rows $0, 1$. But the
SPECIFIC bottom row chosen by band 0 may make band $1$'s problem
INFEASIBLE or sub-optimal.

The greedy chain: commit band $r$'s best, then solve band $r+1$ given
that top row. Loses globally optimal solutions when band 0's choice
isn't globally compatible.

## Conjecture: chain achieves $E_{chain}$ where

$$
E_{chain} = E - n \cdot \delta_{boundary}
$$

where $\delta_{boundary}$ is the per-band "compatibility loss" from
having to live with the prior band's commitment.

## Empirical test (in flight)

Chain script running on canonical 16×16. Will measure:
- Per-band scores.
- Total full-board score.
- Bands that fail (no feasible top-row continuation).

Hypothesis: total will be $< 480$, likely in the $400-460$ range.
If it exceeds $459$ → record discovery via J1.

## Why chained might still discover a record

Band $0$ alone has $\binom{256 \cdot 4}{32}$ possible 2-row configurations
that achieve $46/46$. Many of these are NOT in vol-60's basin or
McGavin's basin (= unexplored basin space). Sequential chaining commits
to one, but the SPACE of starting bands is rich.

To explore basin diversity: try many band-0 solutions (top-K by score
+ second-K perturbations).

## Alternative: backtracking chain

Standard chain fails if band $r$ has no feasible continuation from
band $r-1$'s bottom row. Backtrack to band $r-1$ and pick the
SECOND-best (or 5th-best) bottom row, retry band $r$.

Combinatorially: $K_1 \times K_2 \times \ldots \times K_{n-1}$ paths.
For $K = 100$ per band and $n-1 = 15$ bands: $100^{15} = 10^{30}$.
Need beam-style pruning at chain level too.

## Status

`design-complete` for chain. PoC in flight on canonical 16×16. Math
shows chain CAN reach 480 if all bands perfect; conjecture is some
sub-perfect compromise.

## Linked

- [[j1-column-dp-design]]
- [[j1-poc-perfect-band-results]]
- [[vol-122]]
