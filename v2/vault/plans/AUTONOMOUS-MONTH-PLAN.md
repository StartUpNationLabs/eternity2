# Autonomous month plan (2026-05-15 → ~2026-06-15)

User left autonomous instruction: "User won't return for ≥ 1 month.
Research please. Explore stuff no one has thought about. The
algorithm that will solve E2 is not named yet."

## North star

Find a NEW algorithm, name it, characterize it mathematically, and
test it on E2. Negative results are fine if they're characterized.

## What "stuff no one has thought about" means

I went through the community corpus and the standard ML/CSP/heuristic
canon over vols 1-60. The gap-list:

1. **The PS-matching polytope** (vol-65, started). Standard E2 is
   formulated as quadratic assignment; PSM moves it to matching +
   consistency. Has 307 canonical-orientation bound — rotation
   absorbs the integrality gap. Rotation-aware LP is unexplored.

2. **Information-theoretic puzzle structure**. What's the
   conditional entropy of a piece-placement given its 4 neighbors?
   What's the Shannon-rate of E2 = `log2(solutions) / 256`? Has
   anyone measured this? Probably not — it requires sampling
   partial solutions and computing conditional distributions.

3. **Algebraic-geometric formulation**. The piece-rotation group is
   ℤ/4. The puzzle assembly is a section of a fibration over the
   16×16 grid with ℤ/4-fiber. Can we use sheaf cohomology /
   obstruction theory to bound the number of compatible placements?

4. **Topological data analysis of basin geometry**. Use TDA on the
   space of ~459-score boards we've found (vol-32, vol-35, vol-60).
   Connected components of basin graph; persistence of features.
   We have ~2,293 boards saved — enough to actually do this.

5. **Spectral analysis of the piece-compatibility hypergraph**.
   Eigenvalues of the adjacency operator on G_PS. If there's a
   spectral gap, it characterizes "natural cluster" structure of
   pieces — possibly informs decomposition.

6. **A genuinely new local move**. Vol-62 proved halo-1 local
   ops are dead. But the GLOBAL structure of swaps that DO
   improve isn't well-understood. The 470 Blackwood algorithm uses
   "scheduled relaxation" — let me characterize what kinds of
   high-K moves at WHICH boards yield improvements.

7. **Constraint propagation via piece-rotation-class quotients**.
   The orbit of a piece under ℤ/4 is its "rotation class". Pieces
   in the same class are interchangeable up to rotation. How many
   non-trivial rotation classes are there in canonical E2? If a
   rotation class has multiple distinct pieces, they're partially
   exchangeable — a basin-jumping primitive nobody has used.

8. **Generating-function approach**. Express the number of valid
   E2 placements as a coefficient of a multivariate generating
   function. This is the dimer-statistics / transfer-matrix
   approach used for grid puzzles in stat mech. Computing the
   full thing is exponentially hard; computing approximations
   isn't.

9. **Adversarial constraint construction**. Pick a forbidden
   pattern that would PROVE 480 impossible. If we can derive a
   simple combinatorial certificate (e.g., "every solution uses at
   least N pieces of class C, but only N-1 pieces of class C
   exist"), we prove E2 is < 480 matchable.

10. **The piece-pair-similarity flow**. For each pair of pieces
    (P, Q), compute their "matching propensity": probability they
    end up adjacent in a random solution. This induces a graph
    on pieces with edge weights. Cluster the graph — clusters may
    correspond to "regions" of the assembled board.

## Priority for next 7 days

- **Days 1-2**: Vol-65 rotation-aware LP. Concrete deliverable: a
  proper bound on rotation-aware-PS-matching with frame constraint.
- **Days 3-4**: Pick from gap-list item 7 (rotation class quotient)
  or item 10 (piece-pair similarity). Both are genuinely new and
  CPU-cheap.
- **Days 5-7**: Whichever of (3, 5, 8) seems tractable given days
  1-4 results. Algebraic-geometric is highest risk-reward; spectral
  is cheapest; generating-function might give a partition-function
  bound.

## After 7 days

If none of these has cracked something, pivot to item 9 (adversarial
certificate) — try to PROVE E2 is < 480 via a combinatorial
obstruction. That would be a publishable negative result.

## Don't lose

The user's directive doesn't say "break 459". It says "explore stuff
no one has thought about." Treat each gap-list item as a research
project independent of records. Some might just give papers, not
records. That's fine.
