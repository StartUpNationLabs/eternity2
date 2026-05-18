---
name: wall-breaking-inventions
description: "Vol-125+ backlog: 6 invention paths to break the depth-40 phase-transition wall in W14 super-block BB&B for canonical Eternity II. User noted these all need to be tried, even across multiple sessions. KNOWN: the puzzle DOES have a 480 solution — finding it is hard, but the target exists."
metadata:
  type: project
---

# Wall-breaking inventions backlog

**IMPORTANT FACT** (confirmed by user 2026-05-18): canonical Eternity II
HAS a 480 solution. We don't have it, but it exists. Each of these
inventions targets reducing search cost to find it.

**Current standing record**: 461 matched-edges (community convention),
458 strict-canonical. Community 18-year wall is 459. The 480 target
exists somewhere in the W14 search space.

## The wall (depth-40 phase transition)

W14 BB&B plateaus at depth 40 of 64 super-cells because at pin fraction
$p = 0.625$, the expected fraction of unpinned cells with ≥ 3 pinned
neighbors crosses 50%, triggering near-zero alphabets. See
[[depth-40-phase-transition]].

To find 480 we MUST cross this wall. The 6 inventions below are ranked
by EV.

---

## T20: Backbone-frozen sub-CSP via LP relaxation (rank 1, **HIGHEST EV**)

**Idea**: build LP relaxation of W14 super-block CSP. Variables
$x_{cell, block} \in [0, 1]$. Constraints:
- $\sum_{block} x_{cell, block} = 1$ per cell (one block per cell)
- $\sum_{cell, block : piece p \in block} x_{cell, block} \leq 1$
  per piece (each piece used ≤ 1 time globally)
- edge-match feasibility (only blocks compatible with neighbors)

Solve LP. Cells where LP rounds $x ≈ 1$ for some block are FROZEN to
that block (provably must be in any integer solution if LP optimum is
tight enough).

**Why it works**: If LP fixes, say, 30 cells, BB&B only needs to search
34 remaining → effective pin fraction shifts. If frozen cells are
"strong" (near phase-transition cells), the remaining CSP is below the
wall.

**Template**: `crates/bench-audit/src/border_lp_ub.rs` already does this
for borders. Extend to interior.

**Status**: `unbuilt` (2026-05-18, vol-125)
**Effort**: 1-2 days build, plus LP solve time (HiGHS handles ~10^5
variables routinely)

---

## T21: Vertex-consistency propagation (rank 2)

**Idea**: instead of edge-AC-3 (cell.east-edge = neighbor.west-edge),
propagate via **vertex colors**. Each interior vertex is shared by 4
super-cells; each cell contributes 1 corner color at that vertex; all
4 must agree (or be compatible via piece constraints).

The phase-transition math assumes per-edge constraints are independent.
Adjacent super-cells share edge endpoints (a corner color is shared by
2 cells). Vertex-consistency makes the correlation EXPLICIT in
propagation, potentially collapsing the effective constraint count.

**Sketch**: define 81 interior vertices (7×7 inner grid + 7+7+1 boundary). For each vertex, the 4 adjacent cells' corner-color choices must agree. This is a constraint graph with **fewer effective variables** than the edge-based one.

**Why it works**: reduces correlated double-counting in AC-3, gives
stronger pruning per propagation step. Possibly enough to delay the
phase transition past depth 40.

**Status**: `unbuilt` (2026-05-18, vol-125)
**Effort**: 2-3 days

---

## T22: Cooperative BB&B + ALNS tunneling (rank 3, **partial precedent**)

**Idea**: at depth ~35 (just before the phase transition), EXPORT the
current partial as an ALNS starting point. Score by matched-edges (whatever
is implied by the partial + greedy completion). Let ALNS perturb around
this partial to find higher-scoring full boards.

This DUAL of bf_bw + ALNS uses BB&B as a "structured prefix generator"
and ALNS as a "score-maximizing completer". The 458 strict-canonical
record was found via similar (vol-122 K11).

**Why it works**: BB&B and ALNS suffer DIFFERENT failure modes. BB&B
gets stuck at phase transition. ALNS gets stuck in basin attractors.
A handoff lets each cover the other's blind spot.

**Status**: `partial` (precedent in vol-122; needs systematic build)
**Effort**: 1-2 days to build the export+handoff pipeline

---

## T23: Color-balance Lagrangian bounds (rank 4, **publishable**)

**Idea**: each interior color appears EXACTLY twice on each interior
super-edge (matched). Total count of each color across all interior
super-edges is FIXED by piece set. Add **Lagrangian color-balance
constraints** to LP relaxation. Possibly tight enough to prove either
"480 reachable from partial X" or "no 480 below corner-perm Y".

**Why it works**: gives provably-sound bounds on subspace of the
search. If a partial can be proven INFEASIBLE for 480, prune entire
subtree.

**Status**: `unbuilt` (2026-05-18, vol-125)
**Effort**: ~1 week. This is the most ambitious + most publishable.

---

## T24: Spectral piece-graph decomposition (rank 5, **high-uncertainty**)

**Idea**: build graph where nodes = pieces, edges = "these pieces could
be placed adjacent (some edge color matches)". Find **Fiedler vector**
(spectral clustering). Distinct piece clusters may map to spatial
regions of the board.

If clusters exist, they SUGGEST a decomposition (not predetermined like
W14) that may align better with the CSP natural structure → break the
phase transition by aligning with natural cuts.

**Why it might fail**: pieces might not cluster spectrally (Selby-Riordan
was designed for max asymmetry). But worth measuring.

**Status**: `unbuilt` (2026-05-18, vol-125)
**Effort**: 2-3 days

---

## T25: Graph-coloring reformulation (rank 6, **uncertain**)

**Idea**: each cell has 4 corner colors (TL, TR, BL, BR). These match
diagonally adjacent cells (corner of cell (sr,sc) BR = corner of cell
(sr+1,sc+1) TL).

Build a graph where vertices = (super-cell, corner) pairs and edges =
"must match". Find a **proper k-coloring** of this graph that respects
the W14 alphabet.

If we can find such a coloring fast (heuristic algorithms for graph
coloring), then BB&B reduces from "search 64-tuple of blocks" to
"verify each cell's chosen block matches the corner-color assignment".

**Why it might fail**: graph coloring is NP-hard; constraint may
already be implicit in edge-matching.

**Status**: `unbuilt` (2026-05-18, vol-125)
**Effort**: ≥ 1 week

---

## Cross-cutting infrastructure (T26+)

Beyond these 6, supporting infrastructure that helps multiple:

- **T26**: faster LP solver bindings (HiGHS C API directly) — speeds up
  T20 and T23
- **T27**: incremental LP via column generation — for T20 when freezing
  changes the basis
- **T28**: vertex-consistency benchmark harness — measure pruning
  strength vs. AC-3 for T21
- **T29**: ALNS-from-partial interface — for T22

---

## Working order

Recommended sequence:

1. **T20 (LP backbone)** — week 1 — concrete, sound, attacks state space directly
2. **T22 (BB&B+ALNS tunneling)** — week 1-2 — proven principle, refine
3. **T23 (color-balance LP)** — week 2-4 — publishable
4. **T21 (vertex propagation)** — week 2-3 — orthogonal improvement
5. **T24 + T25** — week 4+ — high-uncertainty, exploratory
