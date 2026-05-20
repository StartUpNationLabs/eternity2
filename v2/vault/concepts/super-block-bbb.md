---
name: super-block-bbb
description: "Vol-125 design — Bourreau-style Block-Backtracking-on-Blocks (BB&B). Use the W14 2×2 super-block alphabets as the variable domains of a CSP at the SUPER-CELL level: 64 super-cells, each with ~2M block candidates after AC-3. Enforce adjacency (boundary equality) + piece-uniqueness. Drastically smaller than the 256-cell native CSP."
metadata:
  type: project
status: built
---

# Super-block BB&B (Bourreau 2020 reformulation)

## The reformulation

Standard E2 CSP: 256 cells × 256 pieces × 4 rotations = ~64k slots, each
with up to 1024 candidates. Search tree depth = 256. AC-3 + class
filter help, but piece-uniqueness + edge-match propagation are weak in
the early levels (high-domain plateau).

**Super-block BB&B**: collapse each 2×2 cell group into one "super-cell"
with alphabet = all 4-piece, 4-rotation tuples that are INTERNALLY
edge-matched. Vol-124 W14:

- 64 super-cells (8×8 super-grid).
- 127.6M total blocks across all super-cells, ~2M per super-cell on
  average.
- Pairwise AC-3 (boundary-tuple equality across adjacent super-cells)
  reduces this by ~8% — too weak alone.

**BB&B does NOT need full propagation to be useful.** Even with 2M
blocks per super-cell, the search tree depth is 64 (vs 256 native).
Each level of search prunes via:

1. **Boundary-tuple equality**: my N-side tuple must match the cell-above's
   S-side tuple. Constant-time check.
2. **Piece-uniqueness ACROSS super-cells**: each of the 256 pieces appears
   in exactly one super-cell's selected block. A piece used in super-cell
   sc1 cannot appear in any block at sc2.

When a piece becomes "scarce" (appears in N>0 alphabets but only in
M<N selected blocks), it's a propagation signal.

## Why this might be the right level of abstraction

- **64 decisions** vs 256: a 4× shorter search tree.
- **Each decision is a 2×2 block of pieces+rotations**: a much richer
  unit than a single piece-rotation. The internal edge-match is
  pre-validated.
- **Adjacency constraints are O(1) per pair**: boundary-tuple equality
  is a 2-color tuple lookup vs a 22-way disjunction in the cell-level
  CSP.
- **Piece-uniqueness is enforced "in bulk"**: when you pick a block,
  you eliminate 4 pieces from all other super-cells' alphabets at once.

## Concrete design

Variables:
- `b_{sc}` ∈ alphabet(sc) for each sc ∈ 0..63.

Constraints (hard):
1. Each `b_{sc}` is in its alphabet (typed: each alphabet is a set of
   blocks).
2. For each adjacent super-cell pair (sc_a, sc_b):
   `boundary_tuple(b_{sc_a}, side_a) == boundary_tuple(b_{sc_b}, side_b)`.
3. Piece-uniqueness: ∀p ∈ 0..255, at most one sc has `b_{sc}` using p.

Objective (soft, for MaxSAT variant):
- Maximize the count of matched cross-super-cell edges. Since blocks
  are internally matched, only inter-block edges (between adjacent
  super-cells) are at risk. With 8×7 + 7×8 = 112 inter-block edges,
  each carries 2 sub-edges → 224 sub-edges to match.

But canonical E2's total edges = 480. Internal-to-super-cell edges
= 64 × 4 (each block has 4 internal edges between its 4 cells) — wait
let me recount. Each 2×2 block has 4 internal edges? No. A 2×2 block
has 4 cells; the internal edges of the block (edges between the 4
cells inside the block) are: 2 horizontal (between row-0 cells, between
row-1 cells) and 2 vertical (between col-0 cells, between col-1 cells)
= 4 internal edges per block. 64 blocks × 4 = 256 internal edges.

Inter-super-cell edges: between super-cells. Each super-cell has up to
4 inter-cell edges (one per side). The 8×8 super-grid has
8×7×2 + 7×8×2 = 224 inter-super-cell edges, BUT each "inter-super-cell
edge" between two adjacent super-cells consists of 2 sub-edges (e.g.,
the E side of super-cell (0,0) and W side of super-cell (0,1) are 2
cell-edges). So 224 inter-super-cell sub-edges.

Total edges = 256 (block-internal) + 224 (inter-super-cell) = 480. ✓

In super-block BB&B:
- **Block-internal edges are AUTOMATICALLY matched** (because we only
  enum'd internally-matched blocks).
- **Inter-super-cell edges are matched ⇔ boundary-tuple constraint
  satisfied**.

So if BB&B finds ANY consistent assignment, the resulting board IS
the 480 solution. **There's no objective in this formulation — it's
pure SAT.**

## Wait — that's a much stronger claim than I realized

If we only enumerate internally-matched blocks AND require boundary-
tuple equality across super-cells AND require piece-uniqueness, ANY
satisfying assignment IS a 480 board.

This means: BB&B is the SAT decision problem for 480. It is exactly as
hard as the canonical SAT — but the search tree is 64 deep instead of
256, with bigger domains. Whether it's tractable depends on:

1. How tight does AC-3 (per-pair boundary equality) prune?
2. How much does piece-uniqueness help once a few super-cells are
   assigned?
3. How effective is value ordering (best-fit blocks first)?

Vol-124's 8% AC-3 reduction is on PAIRWISE adjacency alone — no piece-
uniqueness yet. With piece-uniqueness (a fundamentally global constraint),
reduction could be much higher.

## Why this is the highest-EV multi-week build

- **64-depth tree is provably smaller than 256-depth.** Logarithm.
- **Each level's branching is bounded by 2M but typically much smaller**
  after constraint propagation.
- **The 5 canonical hints fix 5 specific cells inside specific
  super-cells**, immediately reducing 5 super-cells to alphabets that
  contain those specific (pos, piece, rot) at the hint's sub-position.
- **The community 469 records can be used as warm-starts**: dump 469's
  64 super-cell assignments, verify they're in the alphabets, run BB&B
  from there.

## Build plan (~1 week of focused Rust)

1. **Day 1**: Regenerate W14 alphabets (28s). Compute per-piece occurrence
   counts across super-cells. Identify "rare" pieces (those in few
   blocks across all super-cells) — these are the high-leverage
   variables for ordering.
2. **Day 2**: Build "block-CSP" — represent each super-cell's alphabet
   as a packed binary structure. Encode boundary-tuple as 16-bit key.
3. **Day 3-4**: Implement BB&B: variable ordering by min-domain;
   boundary AC-3 (already done); piece-uniqueness propagation: when
   block b is pinned at sc, remove all blocks at other sc's that use
   any of b's 4 pieces.
4. **Day 5**: Apply 5 hints. Run from blank. Time-budget 24h.
5. **Day 6-7**: If undecided, add cube-and-conquer on top — split on
   the highest-arity super-cell.

## Linked

- [[w14-super-block-unviable]] (vol-124's AC-3 weakness; this page
   shows it was the wrong reduction — needed piece-uniqueness too).
- [[bourreau-2020]] (the paper).

## Next steps

1. Write `super_block_uniqueness.rs` extending the W14 AC-3 pruner
   with piece-uniqueness.
2. After W14 alphabet regen, dump per-piece counts.
3. Build the BB&B search itself.
