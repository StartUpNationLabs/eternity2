# Border-class enumeration with LP upper bound

**Status**: partial (design complete, smoke test passing, UB function in progress)
**Origin**: vol-43-reframing identified as high-EV unbuilt direction; vol-44 starts the build.
**Files**: `crates/bench-audit/src/bin/lp_smoke.rs` (toolchain check); upcoming `border_ub.rs`, `border_bb.rs`.

## Definition

Enumerate canonical-E2 *full border placements* (4 corners + 56 edge pieces, all rotations forced by piece BORDER sides) under symmetry break. For each candidate border, compute a *linear-programming relaxation* upper bound on the matched-edges score achievable by **any** legal interior completion. Discard borders whose UB < 458. Pipe survivors into the existing prune_restart + ALNS pipeline.

Cuts the question "what is the canonical-E2 5-clue ceiling?" down to a tractable form:
- If the LP UB is *tight enough*, the survivor set's empirical max-score gives a real near-ceiling.
- If most borders have UB ≥ 458 (loose relaxation), we'll know we need a stronger formulation (e.g. partial integrality, lifted constraints).

## LP formulation

### Setting

- Puzzle: 16×16 canonical E2, 22 colors {1..22} + BORDER=0. 256 pieces: 4 corners, 56 edges, 196 interior.
- Adjacency types on the grid:
  - **B-B** (border-border ring adjacencies): 60. Fully determined by border placement.
  - **B-I** (border-to-interior): 56. Interior side is variable.
  - **I-I** (interior-to-interior): 364. Both sides variable.
- 60 + 56 + 364 = 480 ✓

### Variables

`x[p, c, r] ∈ [0, 1]` for each interior piece `p`, interior cell `c`, rotation `r ∈ {0,1,2,3}`.

Continuous relaxation of the integer assignment problem. The LP relaxation does NOT enforce integrality; it gives an upper bound on the integer optimum.

### Constraints

1. **Cell coverage**: ∀ c ∈ C_int: Σ_{p, r} x[p, c, r] = 1
2. **Piece usage**: ∀ p ∈ P_int: Σ_{c, r} x[p, c, r] = 1
3. **B-I color match** (for each interior cell c adjacent to a border cell with fixed inward-facing color k on shared side s):
   Σ_{p, r : piece-p-rotated-by-r has color k on side s} x[p, c, r] = 1
4. **Hints**: ∀ canonical hint (c, p, r): x[p, c, r] = 1.

### Edge-match linearization

For each I-I adjacency (c1, c2) where c2 is right of c1 (similarly for vertical: c2 below c1):

Define mass-on-side aggregates (linear in x):
- `a[c1, side_right, k] = Σ_{p, r : (p rotated by r).right_color = k} x[p, c1, r]`
- `b[c2, side_left, k] = Σ_{p, r : (p rotated by r).left_color = k} x[p, c2, r]`

For each (c1, c2, k), introduce auxiliary `y[c1, c2, k] ≥ 0` with:
- y[c1, c2, k] ≤ a[c1, right, k]
- y[c1, c2, k] ≤ b[c2, left, k]

Sum-of-y ≤ 1 follows from cell-coverage constraint.

This is the standard LP-relaxation of `min(a, b)` and gives a valid upper bound on the integer match: `match[c1,c2] ≤ Σ_k y[c1,c2,k] ≤ Σ_k min(a, b)`, with equality at integer solutions.

### Objective

```
maximise   (fixed B-B match count, constant)
         + (fixed B-I match count, constant = 56 if all B-I borders feasibly matchable)
         + Σ_{(c1,c2) ∈ I-I, k ∈ colors}  y[c1, c2, k]
```

The constants give the contribution from already-determined / forced-by-constraint matches. The LP variable contribution is the I-I match upper bound.

### LP size

- x vars: ≤ 196 × 196 × 4 = 153,664. After B-I + corner-adjacency pruning, effective ~30k–80k.
- y vars: 364 × 22 = 8,008.
- Equality constraints: 196 (cell) + 196 (piece) + 56 (B-I) + ~25 (hint pins) ≈ 473.
- y inequality constraints: 2 × 8,008 = 16,016.

HiGHS should solve in 0.1–2s per call. With B&B at 10^6+ nodes, we need pruning *before* LP at every level.

## Enumeration tree

### Symmetry break

Canonical-E2 has:
- 4× rotational symmetry of the whole board (rotate the 16×16 grid).
- 2× reflection symmetry.

But canonical hints break most of this — they sit at asymmetric positions (34, 45, 135, 210, 221). Need to check: do the canonical hints break ALL board symmetries, or only some?

Quick check: positions {34=(2,2), 45=(13,2), 135=(7,8), 210=(2,13), 221=(13,13)}. Under 180° rotation around the center (7.5, 7.5): (2,2) → (13,13), (13,2) → (2,13), (7,8) → (8,7), (2,13) → (13,2), (13,13) → (2,2). The set {34,45,210,221} is preserved under 180°, but 135 → (8,7) which is position 8×16+7 = 135's image at 135' = ??? Actually 16×16: (8,7) = 7*16+8 = 120, so 135 → 120. The hints are NOT preserved under 180° rotation. Good — board symmetry is fully broken by the hints.

So no symmetry-break needed at the border-enumeration level; all 60-cell perimeter arrangements are inequivalent.

### Branching

Place corner pieces first, then edges. At each partial border:
1. **Cheap pruning** (pre-LP):
   - B-I supply check (Hall-like): each color k facing inward must be matchable to ≥ enough interior pieces with side-k.
   - Already-placed B-B matches give a lower-floor on B-B contribution.
2. **LP UB** (at full border, possibly at near-full borders):
   - If LP_obj_total < 458: discard.

### Complexity guard

Worst case: 56! edge-piece permutations, intractable. With LP pruning at full borders only, we still need a tractable number of leaves. Three mitigation paths:
1. **Aggressive cheap pruning** at internal nodes to cut the tree shallow.
2. **LP at intermediate depths** (e.g. every 10 edges placed) — slower per-node but cuts deep subtrees.
3. **Start with corner+1-side-edge enumeration** to estimate first-level branching factor and decide feasibility.

## Open questions

- Will LP UB be tight enough? Initial test on a known-feasible 458 board's actual border should give UB ≥ 458 (necessary) and ideally < 480 (otherwise relaxation is useless).
- What's the right depth to first apply LP? Possibly LP only at leaves with cheap UB elsewhere.

## Linked concepts

- [[scan-order]] — border-first is one specific scan order
- [[relaxed-bound]] — different relaxation (piece-uniqueness)
- [[dead-ends]] — vol-43-reframing identified the false-comfort lottery pattern

## Linked memory

- `project_e2_vol22_basin_escape.md`
- `project_e2_vol25_perf_push.md`
