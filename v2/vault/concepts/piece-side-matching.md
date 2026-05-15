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

### Rotation-aware formulation (vol-65 day 2 — built)

Drop the canonical-direction constraint. A piece's 4 sides can be
arranged in any of 4 rotations relative to the world. The LP just
asks: can we PAIR UP non-border piece-sides by color?

Variables:
- `x_e ∈ [0, 1]` for each candidate edge e = (piece-side, piece-side)
  with matching color on DIFFERENT pieces.

Constraints:
- **Side-coverage**: `Σ_{e ∋ v} x_e ≤ 1` for each non-border piece-side v.
- **Piece-budget** (optional): `Σ_{e ∋ any side of p} x_e ≥ required(p)`
  where `required(corner)=2, edge=3, interior=4`. (Encodes that
  every piece-side must be matched in a valid assembly.)

Objective: `max Σ x_e`.

### Day-2 LP results (2026-05-15)

Built `scripts/vol65_ps_graph_rotaware.py` + `scripts/vol65_ps_lp_rotaware.py`.

| graph                       | vars  | rows | LP UB    | integer-1 | fractional |
|-----------------------------|-------|------|----------|-----------|------------|
| Rotation-aware (baseline)   | 21636 | 1024 | **480.00** | 414       | 132        |
| Rotation-aware + budget     | 21636 | 1280 | **480.00** | 433       | 94         |

**Both LP relaxations reach 480 exactly.** Rotation absorbs the
canonical-orientation 307 bound. The relaxation is NOT tight —
there are fractional vertices.

### What the fractional solution tells us

132 fractional edges in scenario 1. These represent **edges that
"want" to be in the matching but compete with one another for
shared piece-sides**. The MIP integer-optimum will be ≤ 480.

### Structural fact — exact piece-side counts

Canonical 16×16 E2 has:
- 4 corner pieces × 2 non-border sides = 8
- 56 edge pieces × 3 non-border sides = 168
- 196 interior pieces × 4 non-border sides = 784
- **Total non-border sides = 960**
- 480 interior edges × 2 sides per edge = **960 sides needed**

The puzzle is **EXACTLY non-border-side-balanced**. Selby-Riordan
generator designed this. The PSM matching has zero slack — every
non-border side must be matched, NONE can face the frame instead.

### What this means for E2 solvability

The LP-relaxation 480 says color-matchings exist for 480 edges in
the rotation-aware polytope. But:
1. The fractional solution can't be rounded directly (132 fractional
   edges sharing piece-sides).
2. We haven't added piece-rotation CONSISTENCY: 4 matched sides of
   one piece must be a permutation of (N,E,S,W) under some rotation.
3. We haven't added piece-uniqueness in cells (QAP layer).
4. We haven't added geometric tiling: the matching has to form an
   actual planar tiling of a 16×16 grid.

### Day-3 LP — added rotation consistency (2026-05-15)

Built `scripts/vol65_ps_lp_rotconsistent.py`. Adds:
- `r[p, k] ∈ [0,1]` for piece p, rotation k. Σ_k r[p,k] = 1.
- For each piece-pair (p1, p2), 16 auxiliary `z[p1, k1, p2, k2]`
  with McCormick `z ≤ r[p1,k1], z ≤ r[p2,k2]`.
- For each candidate edge e = ((p1,s1),(p2,s2)) with parity
  `δ = (s1+s2) mod 4`: `x_e ≤ Σ_{(k1,k2): k1+k2 ≡ (2-δ) mod 4} z[p1,k1,p2,k2]`.

LP size: 262,900 vars / 503,076 constraints / ~1.1M nnz.
LP solve time: **290s** in HiGHS via scipy.linprog.

**Result: LP UB = 480.00 still.** Rotation-consistency alone doesn't
tighten the bound. Diagnostics:
- 0 integer-1 edges, 2,218 fractional (all edges blended)
- 0 pieces with integer rotation; rotation entropies span 0.084-1.962

The LP is using FRACTIONAL rotations to keep 480 feasible. Each
piece is partially in each rotation. To tighten, we need to FORCE
piece rotations to be integer-valued, OR add cell-placement
variables (the QAP layer).

### What's still missing

The PSM polytope after rotation-consistency is STILL a relaxation
of E2. The remaining gaps:
- **Piece-uniqueness in cells**: each piece occupies exactly 1 cell.
  Adding `y[p, c] ∈ [0,1]` with Σ_p y[p,c] = 1 and Σ_c y[p,c] = 1.
  But linking y to x_e requires identifying which pairs (p1, p2)
  can be neighbours — depending on cell-pair adjacency, this
  becomes the full QAP.
- **Geometric tiling**: the matching graph must be a 4-regular
  planar graph isomorphic to the 16×16 grid (minus border edges).

Hypothesis: at some level of these added constraints, the LP drops
below 480. If it drops below 469, we have a NEW BOUND tighter than
McGavin's empirical ceiling. If it stays at 480 even with full
QAP, the puzzle is "LP-tight" — all the hardness is in integrality.

### Vol-65 day 4 plan

Add piece-uniqueness via cell-assignment without going full QAP.
One angle: use the parametric LP `r[p, k]` consistently with the
known FRAME structure (corner pieces only at 4 corner cells,
edge pieces only at perimeter, interior pieces only at interior).
This is a polynomial number of new constraints and significantly
tightens.

Specifically, add:
- For each corner-piece p (4 pieces), only 4 candidate placements
  (one per corner cell). The cell-placement is correlated with
  rotation.
- Similar for edge-pieces (56 pieces, 56 perimeter-non-corner cells,
  each cell has 1 valid rotation per piece given border-direction).

This adds ~256 piece-placement constraints, all polynomial.

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
