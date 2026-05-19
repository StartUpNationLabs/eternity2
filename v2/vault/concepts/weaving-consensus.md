# WEAVING — Two-Axis Consensus Construction

**Status**: `designed` 2026-05-19 (Vol-150). Math written; PoC in
progress.

## Idea

A canonical 16×16 board has two natural axes: rows and columns. Score
decomposes additively across the 240 horizontal edges (intra-row,
between cells in the same row at adjacent columns) and 240 vertical
edges (intra-column, between cells in the same column at adjacent
rows). For a perfect 480 board: 240 + 240 matched.

WEAVING runs TWO independent constructive passes:

1. **Row-greedy**: build the board row-by-row (top to bottom). Each
   row $y$ is filled left-to-right, each cell chosen greedily to
   maximize the horizontal-edge match with the cell at $(y, x-1)$
   plus the vertical-edge match with the cell at $(y-1, x)$ if
   already placed.
2. **Col-greedy**: build the board col-by-col (left to right). Each
   col $x$ is filled top-to-bottom, each cell chosen greedily to
   maximize the vertical-edge match with the cell at $(y-1, x)$ plus
   horizontal with $(y, x-1)$ if placed.

Each pass produces a complete board. Call them $B_R$ and $B_C$. They
use the SAME piece inventory (256 pieces) but in different orders.

## The tension metric

For each cell $(y, x)$, define **tension**:
$$T(y, x) = \begin{cases} 0 & \text{if } B_R[y,x] = B_C[y,x] \\ 1 & \text{otherwise} \end{cases}$$

Total tension $T = \sum_{y, x} T(y, x)$. A perfect consensus has $T = 0$.

## The consensus iteration

Given $B_R, B_C$ with $T > 0$:
1. Pick a tension cell $(y, x)$ with $T(y, x) = 1$.
2. Compute: what's the score-cost of swapping $B_C[y, x]$ into $B_R$
   (replacing $B_R[y, x]$)? Both boards must remain piece-unique, so
   we have to evict the piece $B_C[y, x]$ from its OTHER position in
   $B_R$ (call it $(y', x')$) and swap in $B_R[y, x]$ to that spot.
3. The local effect on $B_R$ score: 4 edges around $(y, x)$ recompute
   + 4 edges around $(y', x')$ recompute. Net Δscore_R = computable.
4. Accept the swap if Δscore_R ≥ −ε (allow small score decrease in
   exchange for consensus). Symmetric for $B_C$.
5. Repeat until $T$ stops decreasing OR scores degrade too much.

The output is the higher-scoring of $B_R, B_C$ at termination.

## Why this should work

Row-greedy and col-greedy emphasize different edges. The pieces they
place at the same cell may differ because each greedy criterion saw
different info first. **The cells where they AGREE are the cells where
the right piece is locally obvious from BOTH directions** — these
are high-confidence cells. The cells where they DISAGREE are where
local greedy is misleading.

By iteratively reducing tension while preserving score, we propagate
high-confidence placements outward and force low-confidence cells to
reconcile. This is a form of **belief propagation** at the
construction phase, not the search phase.

## Falsifiable claims

Let scoring be matched-edges out of 480.

| Claim | Expected | Refutation |
|-------|----------|------------|
| Row-greedy alone scores ≥ 240 (matches all 240 horizontal) | YES (it's greedy on horizontal) | If < 240 then greedy is even weaker than expected |
| Col-greedy alone scores ≥ 240 | YES symmetrically | same |
| Row-greedy + Col-greedy initial $T \geq 100$ (significant disagreement) | YES (the two axes don't naturally agree) | If $T = 0$ initially, the two passes are degenerate |
| Consensus iteration reduces $T$ by 50%+ in 100 iterations | hypothesised | If $T$ doesn't decrease, consensus is undefined |
| Final board score $> 373$ (GRAIN PoC ceiling) | hypothesised | Falsifies the invention |
| Final board score $> 463$ (current V129-T12 best) | aspirational; would be a record | — |

## Connection to existing concepts

- **GRAIN** (vol-135): single isotropic grower, single board, no
  consensus.
- **Houdayer cluster swap** (in localsearch): swaps clusters between
  two replicas based on agreement. WEAVING borrows this idea at the
  PER-CELL level for CONSTRUCTION, not search.
- **Frontier-State Memoization** (vol-122 J6): caches partial-board
  states. WEAVING is orthogonal; could combine.
- **Belief Propagation** (W2, vol-123): BP marginals over pieces.
  WEAVING is "BP at construction" with each row/col build = one
  message pass.

## Day-1 deliverable

`scripts/v150_weaving/weaving_poc.py`:
- `build_row_greedy(pieces, size, seed)` → returns board scoring its
  horizontal + vertical matches.
- `build_col_greedy(pieces, size, seed)` → symmetric.
- `tension(B_R, B_C)` → returns int.
- `consensus_iterate(B_R, B_C, max_iters, eps)` → returns final boards.

5 seeds × canonical 16×16/22. Report min/median/max for each metric.

## Day-2 deliverable

If Day-1 results are encouraging, port the inner loop to Rust
(`crates/bench-audit/src/bin/v150_weaving.rs`) for 1000× speedup,
then run with K=100 seeds.

## Linked

- [[../sessions/vol-150]]
- [[grain-polycrystalline]]
- [[../plans/INVENTION_NAMES_2026-05-19]]
