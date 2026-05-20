# V183 SEMAPHORE — Per-Row Hungarian Optimization

Status: `unbuilt-rust` (Python PoC, 2026-05-20)
Origin: vol-183 (this volume)
Naming: **SEMAPHORE** — Greek for "sign-bearer"; per-row signals from above propagate to determine below.

## Idea

Existing beam search (V155, V175, V178) places pieces ONE AT A TIME, evaluating after each placement. Greedy + beam-width-K.

V183 SEMAPHORE: solve **ONE ROW AT A TIME**, exactly, via bipartite matching. Each row of 16 cells × ~30 candidate (piece, rotation) gets a Hungarian assignment that maximizes E-W matched edges within the row, subject to:
- N-edge of each piece matches the fixed S-edge of the corresponding cell in row above.
- Piece uniqueness across the board.

This is EXACT per-row, not greedy.

## Math — bipartite matching formulation

Given row $r-1$ fully placed (south edges $s_0, \ldots, s_{15}$ at cells), and a remaining piece set $P$ (256 - placed pieces).

For row $r$:
- Each cell $c \in \{0, \ldots, 15\}$ needs a (piece, rotation) such that the piece's N-edge after rotation = $s_c$.
- Adjacent cells must have E-W matching edges: cell $c$'s E-edge = cell $c+1$'s W-edge.

This is a **Hamiltonian path / assignment problem** on the row-graph:
- Nodes: (cell, piece, rotation) tuples that satisfy the N-constraint.
- Edges: between (cell, $(p_c, r_c)$) and (cell+1, $(p_{c+1}, r_{c+1})$) if the E-W constraint holds.
- Constraints: piece-uniqueness (each $p$ used at most once across all rows so far, and at most once within row).

For a 16-cell row, this is a 16-node path problem. With ~30 candidate pieces per cell and Hungarian for bipartite assignment, the **chain** can be solved via DP in $O(16 \cdot 30^2) = O(14400)$ ops per row.

### Constraint handling

The chain-DP works as follows:
1. For each candidate $(p_0, r_0)$ at cell 0 (with N-match to $s_0$): start chain.
2. For cell $c \to c+1$: extend chain by candidates $(p_{c+1}, r_{c+1})$ with N-match $s_{c+1}$ AND E-W match (cell $c$'s E-edge = cell $c+1$'s W-edge).
3. DP state: $\max_{\text{chain ending at } (p_c, r_c)} \text{matches}_{0..c-1}$.
4. Output the best terminating chain.

### Piece-uniqueness

Two phases:
- **Forward propagation**: solve each row top-to-bottom, marking used pieces. Greedy in row order.
- **Block-reorder**: try solving rows in different orders to escape "early piece commitment" failures.

### Optimality

Per-row: this is EXACT for the row given the row-above. NOT optimal globally because:
- The row-above might have been suboptimal (so the south edges constrain badly).
- Piece-uniqueness with sequential filling can starve later rows.

But for E2's 16-row structure, even an EXACT per-row solver is fundamentally different from greedy beam: it can find row placements with 14-15 matched edges that beam might miss because greedy can't see the cross-row constraints.

## Why this is genuinely new

| Method | Per-row optimality | Per-row budget |
|---|---|---|
| V155 beam K=256 | greedy by placement | 16 placements per row × beam |
| V175 GAUNTLET | greedy by scan-order | same |
| V178 STIGMA | greedy + pheromone | same |
| **V183 SEMAPHORE** | **EXACT per-row chain DP** | O(N·M²) = ~14400 ops |

Per-row exact + piece-uniqueness across rows is a fundamentally row-decomposed view. No previous E2 method (in our backlog) uses chain-DP at the row level.

## What we expect

H1: V183 SEMAPHORE single-row chain-DP from a FIXED row 0 (e.g., from V175) gives EXACT row 1 with maximum E-W matched. If V155's greedy row-1 had 13/15 matches, SEMAPHORE might find 15/15.

H2: Iterating row-by-row top-to-bottom, the cumulative match count exceeds V175 (which is greedy).

H3: With piece-set tracking, rows 0-11 fill cleanly; rows 12-15 may starve (only 16 × 4 = 64 pieces left, narrow choice space). This is the EXACT KIND of problem that breaks V182 ENGRAVE (CSP-rigidity in bottom rows).

## What's still open

- How to handle piece-uniqueness elegantly. ILP would do this exactly; chain-DP greedy across rows is approximate.
- Should we solve multiple rows JOINTLY (column-DP up + row-DP within)?
- Backtracking when row $r$ becomes infeasible — try alternative row $r-1$ from a stack of options.

## Linked

- [[../sessions/vol-183]] (planned)
- [[prior-data-augmented-beam]] (V155 — what SEMAPHORE replaces)
- [[../plans/INVENTIONS_BACKLOG]] (A6 iterative widening — related row-based idea)
