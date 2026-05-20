---
name: sb-ble-invention
description: "Vol-125 invention: SB-BLE (Super-Block Bandwidth-Limited Enumeration). Row-by-row DP over super-block rows, with frontier state = south-edge tuple × piece-set. Designed to break the BB&B depth-40 plateau."
metadata:
  type: project
status: unbuilt
---

# SB-BLE — Super-Block Bandwidth-Limited Enumeration

**Status**: `unbuilt` (invented 2026-05-18, vol-125)
**Origin**: senior-researcher pivot after BB&B v5/v6 plateau at depth 40 of 64.

## Definition

Decompose canonical Eternity II's 16×16 cell-grid into the 8×8 super-block
grid (each super-cell = 2×2 piece block). Instead of cell-by-cell BB&B, run
a **row-wise DP** where each "stage" enumerates one super-row (8 super-cells)
and merges with the previous row via a "frontier" matching.

### Math setup

Let $G = (V, E)$ be the 8×8 super-grid. Each super-cell $v = (sr, sc)$ has an
alphabet $A_v$ of valid blocks (precomputed by W14 enumerator).

A **super-row** is the 8-tuple $(B_{sr,0}, B_{sr,1}, \ldots, B_{sr,7})$ of
block selections at row $sr$.

A super-row is **internally valid** if:
- adjacent blocks share matching vertical inner-edges:
  $B_{sr,sc}.E == B_{sr,sc+1}.W$ for $sc \in \{0, \ldots, 6\}$
- (where $.E$ is the east-edge tuple = (TR.E_color, BR.E_color))

A super-row's **frontier** is $(B_{sr,0}.S, B_{sr,1}.S, \ldots, B_{sr,7}.S, P_{sr})$
where $P_{sr} = \bigcup_v \{\text{piece IDs in } B_{sr,sc}\}$ is the 32-piece
set used by that row.

Two consecutive super-rows are **compatible** if:
- row $sr+1$'s north edges match row $sr$'s south edges:
  $B_{sr,sc}.S == B_{sr+1,sc}.N$ for all $sc$
- $P_{sr} \cap P_{sr+1} = \emptyset$ (piece-disjointness)

### DP recurrence

Let $f(sr, \text{frontier}) = $ True iff some valid assignment exists for rows
$0..sr$ ending in that frontier state.

**Base case**: $f(0, \text{frontier})$ = True for every internally-valid row-0
super-row (with $N$-edges = border + hints in row 0 obeyed).

**Transition**: $f(sr+1, (\text{S}_{sr+1}, P_{sr+1}))$ = True iff
exists $\text{S}_{sr}, P_{sr}$ such that:
- $f(sr, (\text{S}_{sr}, P_{sr}))$ = True
- internally valid row $sr+1$ with N-edge = $\text{S}_{sr}$ and pieces $P_{sr+1}$ disjoint from $P_{sr} \cup P_{sr-1} \cup \ldots \cup P_0$.

Wait — the piece-disjointness needs to be against ALL previous rows, not just
the immediate predecessor. So the frontier state must include $\bigcup_{r \leq sr} P_r$,
not just $P_{sr}$.

That's 256 bits → 2^256 states → infeasible.

### Bandwidth limit

To make this tractable: **bandwidth-limit the frontier**. Keep only the top
$k$ frontier states by some heuristic (e.g., maximum unused-piece count, or
minimum south-edge color rarity).

This gives a **beam search** over super-rows. Beam width $k$ controls memory:
$k \cdot 8 \cdot 256 \cdot 1$ bytes per state ≈ tiny.

### Why this might break depth-40 plateau

- Each super-row is enumerated in **isolation**, so we explore all $\sim 10^8$
  internally-valid row sequences per row, not just one branch deep.
- The piece-disjointness check happens at the row-boundary level, catching
  conflicts early (within 8 super-cells = 32 pieces).
- The bandwidth $k$ trades memory for completeness; with $k = 10^6$ we cover
  more of the state space than DFS could in the same time.

### Row enumeration cost analysis

Each super-row has 8 super-cells, each with $\sim 10^3$-$10^5$ blocks. Naive
8-cell sequence enumeration = $10^{24}$ to $10^{40}$. Way too much.

**Constraint propagation per row**: at each step in the row, the next cell's
domain is filtered by:
- E-edge of previous cell must equal W-edge of next cell (~10 candidates remain)
- piece-uniqueness within the row (~half remain after 4 cells)

So within-row enumeration with greedy propagation gives ~$10^3$ valid rows
in practice (numbers TBD via experiment).

### Implementation sketch

```rust
struct RowFrontier {
    south_edges: [(u8, u8); 8],      // 8 south-edge color pairs
    pieces_used_total: u256,         // bitmask of pieces used so far
    pieces_used_this_row: u256,      // for the deduping
    row_chosen: Vec<(u32, u16, u8)>, // the 8 block placements for this row
}

fn enumerate_row(
    sr: usize,
    n_edges: &[(u8, u8); 8],         // north edges constraint (from prev row's south)
    pieces_forbidden: &u256,         // pieces already used
    alphabets: &[Vec<Block>; 8],
) -> Vec<RowFrontier> { ... }

fn solve() {
    let mut current_layer: Vec<RowFrontier> = enumerate_row(0, &border_north, &empty, ...);
    for sr in 1..8 {
        let mut next_layer: Vec<RowFrontier> = Vec::new();
        for state in &current_layer {
            let new_rows = enumerate_row(sr, &state.south_edges, &state.pieces_used_total, ...);
            // ... combine ...
            next_layer.extend(...);
        }
        // bandwidth limit: keep top-k by heuristic
        next_layer.sort_by_key(|s| /* some signature */);
        next_layer.truncate(BEAM_WIDTH);
        current_layer = next_layer;
    }
    // Check final layer for completeness
}
```

### Hint constraint

5 canonical hints fix specific (piece, rotation) at specific super-cells.
Each hint forces its super-cell's block selection to ones containing that
piece at that slot with that rotation. Prune alphabets accordingly before
enumeration.

### Open questions before building

1. **How many internally-valid row 0 super-rows are there?** Need to measure.
   If $> 10^7$, we need within-row propagation more aggressive.
2. **Is bandwidth-limited beam sound?** No — it can miss the unique solution
   if pruned too aggressively. We accept this as a heuristic; 480 attempts
   guided by good signatures may still find solutions.
3. **What if 480 doesn't exist?** Then SB-BLE gives an EMPTY final layer,
   which is itself a useful research result (would suggest the W14 alphabet
   has no global solution).

### Why this is "invented" not "literature"

The closest existing work is "profile DP" for placement problems (used in
domino tilings, m × n exact-cover). Standard profile DP keeps the south-edge
state but NOT the piece-set. SB-BLE adds the piece-set dimension via
bandwidth-limiting, which is novel for this problem.

Bourreau's 2008 BB&B uses depth-first super-block CSP — not row-wise DP.

## Status

Building now (2026-05-18 18:25). First milestone: enumerate row 0 and report
internally-valid count + sample sizes per super-cell.
