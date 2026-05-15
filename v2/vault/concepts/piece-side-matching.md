# Piece-Side-Matching reformulation of E2 (vol-65 math)

**Status**: `design` (math-first) — vol-65 (2026-05-15).
**Type**: INVENTED ALGORITHM (per user directive vols 61-70).
**Inventor**: this autonomous run.

## Audit-at-design

Codebase audit (`grep -ri "side.match\|piece.side\|side_graph"
crates/`): no existing reformulation along these lines. Vol-12
edge-color BP is the closest — operates on EDGE variables, but at
the CSP-level (cell domains), not in the matching paradigm. This
reformulation moves the search space from cells-to-pieces to
**piece-sides-to-piece-sides** matchings.

## Standard E2 formulation (for contrast)

Variables: `x[c, p, r] ∈ {0, 1}` for cell `c`, piece `p`, rotation `r`.
- 256 cells × 256 pieces × 4 rotations = 262,144 binary variables.
- Constraints:
  - Cell coverage: `Σ_{p,r} x[c, p, r] = 1 ∀ c` (256 constraints)
  - Piece uniqueness: `Σ_{c, r} x[c, p, r] = 1 ∀ p` (256 constraints)
  - Edge matching: maximize `Σ y[e]` where `y[e]` is 1 if both
    endpoints of edge `e` show the same color
  - Frame constraints: corners only at corner cells, edge pieces only
    at edge cells (boundary respect)

This is a quadratic assignment with frame structure. Hard.

## Piece-Side-Matching reformulation

### Graph G_PS

**Nodes**: piece-sides. Each piece has 4 sides. 256 pieces × 4 sides
= **1024 nodes**. Each node is a triple `(p, s)` where `p ∈ [0, 256)`
is the piece-id and `s ∈ {N, E, S, W}` is the side-index. Each node
has a fixed color `col(p, s) ∈ [0, 23)` (the puzzle's 23-color
palette).

**Edges**: a piece-side pairing represents two sides being
*adjacent in the assembled board*. Two nodes `(p1, s1)` and `(p2, s2)`
can be paired iff:
- `col(p1, s1) = col(p2, s2)` (color match), AND
- `(s1, s2) ∈ {(N, S), (S, N), (E, W), (W, E)}` (sides face each other).

Count: at a single piece-side `(p1, s1)`, the valid partners are
those `(p2, s2)` with matching color and opposing side. On canonical
E2 each interior side-color appears O(20-30) times across all
piece-sides; opposing-side-of-same-color partners ~5-15. **Edge count
in G_PS is on the order of 1024 × 10 / 2 ≈ 5,000-10,000.**

### A "valid E2 solution" as a PS-matching

Claim: an assembled E2 board solving all 480 interior edges
corresponds to a subset `M ⊆ E(G_PS)` of cardinality 480 (the count
of interior edges in a 16×16 grid: `2 × 15 × 16 = 480`) satisfying:

1. **Side-coverage**: each non-perimeter side of each interior piece
   appears in exactly ONE edge of `M`. (Perimeter cells' outward
   sides don't appear in `M`; they're frame-edges.)

2. **Piece consistency**: for each piece `p`, the 4 sides
   `{(p, N), (p, E), (p, S), (p, W)}` that appear in `M` correspond
   to the SAME cell-position in the final board. Equivalently, all
   matchings incident on a single piece must "rotate" consistently:
   if `M` says `(p, s1)` matches `(p', s')` AND `(p, s2)` matches
   `(p'', s'')`, then the geometric placement implied by these
   pairings is consistent (the side-orientation of `p` is well-defined).

3. **Cell consistency**: at each interior intersection of 4 cells in
   the grid, the 4 sides meeting there belong to 4 distinct pieces.

Condition 1 is a **perfect matching** on the side-nodes, restricted
to interior cells. Conditions 2 and 3 are the **non-trivial part**.

## Why this matters

**Perfect matching is polynomial.** Given `G_PS`, finding a
max-cardinality matching takes `O(|V| × |E|)` via Blossom, plus
counting permutations of side-orientations. If conditions 2 and 3
could be enforced WITHIN the matching, E2 would have a polynomial
exact algorithm. Since E2 is NP-hard, this CANNOT close — the
"gap" is where the hardness lives.

Concretely: an unconstrained PS-matching with side-coverage and
color-match gives **an UPPER BOUND on the matchable edges**, but
typically fails conditions 2 and 3. Lagrangian relaxation of
conditions 2 and 3 yields a tractable bound.

## Lagrangian dual

For each piece `p` and each (side, side) pair `(s1, s2)` with
`s1 ≠ s2`, define a "co-occurrence indicator"
`z[p, s1, s2] = 1` iff both `(p, s1)` and `(p, s2)` are in M.
Condition 2 (piece consistency) demands a relationship between the
`z` values: all 4 sides of `p` that are matched must agree on
piece orientation. This collapses into:

- **Geometric constraint**: for each piece `p` placed at cell `c`,
  the side-assignment is a rotation of `(N, E, S, W)`. There are
  exactly 4 valid orientations. Within an orientation, the four
  partner edges are determined by `M`.

Equivalent Lagrangian formulation: introduce dual multipliers
`μ[p, c, r] ∈ ℝ` for "piece `p` is placed at cell `c` with rotation
`r`". The Lagrangian objective adds
`Σ_{p, c, r} μ[p, c, r] · indicator(M is consistent with this placement)`.

The DUAL gives an upper bound. Computed by solving the relaxed
matching (without condition 2) and projecting onto the consistency
manifold via the multipliers.

### How tight is this bound?

Conjecture: at canonical E2, the unconstrained matching admits
matchings of cardinality 480 (perfect matchings exist on the
multiset-equality reduced graph). The Lagrangian gap is the
distance to a CONSISTENT matching.

If the conjecture holds, the dual bound is 480, providing zero
information. But: the conjecture probably fails — the
multiset-equality condition (vol-11 Δ-invariant) tells us 480
matchings exist only when all 23 colors have balanced
interior-occurrence. The vol-11 result that "canonical E2 partials
at 448-480 have Δ ∈ {0,1,2,4}" hints that PS-matching may already
reflect this — Δ might be the integrality gap.

### Variables count

- 1024 side nodes
- ~5000-10000 candidate edges
- Plus 256 piece-orientation variables (rotations) for consistency

Linear program size: `O(10⁴)` variables and `O(10³)` constraints.
**Tractable in HiGHS in seconds.** This is a key advantage over the
quadratic-assignment formulation (262k binary variables).

## Empirical findings — day 1 (2026-05-15)

### |E(G_PS)| measurement

Ran `scripts/vol65_ps_graph.py` on canonical E2:

- 1024 nodes (256 pieces × 4 sides)
- **5,206 edges** in G_PS (counting opposed-direction color-matches only)
- 23 distinct colors (matches canonical)
- 126 isolated nodes — all border-color sides + a few rare minority-color sides
- Degree distribution bimodal: perimeter pieces deg 1-2, interior pieces deg 10-40

### LP-relaxation of CANONICAL-ORIENTATION PS-matching

`scripts/vol65_ps_matching_lp.py` solves
`max Σ x_e s.t. Σ_{e ∋ v} x_e ≤ 1, x_e ∈ [0, 1]` via HiGHS.

**Result: 307.00** (integer-valued solution, no fractionals).

This bound is sound IF we fix piece orientation to the canonical
(piece-side labels match world directions). Closed-form check:
`Σ_c min(E_c, W_c) + min(N_c, S_c) = 307` (= LP).

### Why 307 ≠ E2 ceiling

The canonical-orientation analysis IS NOT the real PS-matching for
E2. **E2 allows piece rotations**, and the PS-graph must reflect
this: any piece can have any of its 4 sides facing any of {N, E, S,
W} in the assembled board.

In other words: the side-label `s ∈ {N, E, S, W}` is internal to
the piece, but the WORLD direction the side faces depends on the
piece's rotation. The LP should NOT condition the match on
`(s1, s2) ∈ opposing-pairs`; instead, any two sides on different
pieces with matching color can be matched, provided the joint
rotation choice is geometrically consistent.

### Correct formulation (vol-65 day 2)

Variables:
- `r[p, k] ∈ {0, 1}` for piece `p` and rotation `k ∈ {0, 1, 2, 3}`.
  Constraint: `Σ_k r[p, k] = 1`.
- `x_e` for each color-compatible (p1, p2) pair of side-occurrences
  — note: now there are MORE candidate edges per piece-pair because
  any side-of-p1 can match any opposing-side-of-p2 after rotations.

Rotation degrees of freedom multiply the candidate edge count by
roughly 4 (each pair has 4 valid rotation combinations). Expected
LP cardinality ≈ 480 (the puzzle is "color-feasible" by
construction — Selby-Riordan guarantees integer-feasibility under
some piece-placement; relaxed-LP should reach 480 trivially).

The interesting bound is the **rotation-aware** relaxation with the
ADDITIONAL frame constraint: corners only at corners, border-pieces
only on perimeter cells.

## Concrete plan

### Day 1 (tonight)

- [x] Write this math sketch.
- [ ] Compute `|E(G_PS)|` exactly on canonical E2 by iterating piece
  edges. Verify the count is small enough for LP.
- [ ] Build the PS-graph as a JSON dump (one-time precompute).

### Day 2

- Write a HiGHS LP that solves the relaxed PS-matching (without
  consistency). Measure: what's the unconstrained UB?
- Add piece-orientation variables + consistency constraints. Run
  the constrained LP. Compare bounds.

### Day 3

- If the gap is small, formulate it as a MIP (binary matching
  variables) and let HiGHS try to solve. May actually find 469+
  matchings via a cleaner search space.
- If the gap is huge, characterize WHY: are there color-mismatch
  obstructions? Multiset-equality blockers? Piece-uniqueness
  violations?

## Why this is NOT a variant

- Existing CP formulations search over (cell, piece, rotation) tuples
  and enforce edge-matching as a constraint. PS-matching INVERTS
  this: searches over (side, side) pairings and enforces
  cell/piece consistency as a constraint.
- Existing matching-relaxation work in E2 literature (Bucas's "match"
  view) is a visualization, not a search algorithm.
- Naming: **Piece-Side-Matching** (PSM) or "Side-Conjugate Flow" —
  neither in any literature I know of (auditable via web search at
  vol-65 close).

## Open mathematical questions

1. **What is the LP-relaxation bound on E2 via PSM?** If LP < 480,
   we have a sound combinatorial bound on the puzzle itself.
2. **Does the consistency Lagrangian close at canonical E2?**
   Empirically: how many dual iterations until feasibility?
3. **Is the integrality gap of PSM tighter than the
   cell-piece-rotation MIP?** Both are NP-hard but the polytopes
   differ.
4. **Connection to vol-11 Δ-invariant**: does the PSM dual surface
   the same multiset-equality structure that Δ captures?

## Linked

- [[../sessions/vol-65]] (TBD)
- [[mip-local-optimality-459]] — vol-62's MIP-bound, complementary
  (cluster-MIP is also a polytope analysis but local-only)
- memory: [[project_e2_ns1_deficit_invariant]] (vol-11 Δ-invariant)
- memory: [[reference_e2_bp_measurements]] (vol-11 BP on factor graph)
