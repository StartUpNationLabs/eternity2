# Lifted LP via per-piece column-generation — design

**Status**: `unbuilt` (design only) — vol-52 (2026-05-15).
**Origin**: vol-52 binding item, building on vol-50 LP-integer gap
analysis and vol-47's failed McCormick approach.

## The problem to solve

Vol-44/45/46 established that the LP UB on canonical-E2 borders is
~478, but the integer best in every basin is ~457-458, a uniform
**~20-point gap**. Vol-50's [[lp-integer-gap-anatomy]] showed:
- ~6 points of the gap are fractional LP values (closeable by classical
  cuts in principle, but Gomory rounds didn't help).
- ~12 points are integer-valued per-color LP UBs that cannot be jointly
  achieved due to **piece-uniqueness joint-infeasibility**.

Vol-47 tried naive McCormick lifting on bilinear products of x-binaries.
At canonical scale (n_pieces × n_cells × 4 rotations) the lifted problem
exploded combinatorially; column-generation v1/v2 variants under-
or over-counted match credit. Refuted as intractable.

**Open question**: is there a tractable lifted formulation that closes
the piece-uniqueness gap?

## Why per-piece decomposition is structurally different from vol-47

Vol-47's McCormick approach added auxiliary z-variables for products
`x[p, c, r] · x[p', c', r']` across PAIRS of placements. The number of
such pairs grows as O(n_pieces² · n_cells² · 16), which at 196 interior
cells × 192 interior pieces × 16 rotation pairs ≈ 10^9 variables —
intractable even at column-generation scale.

**Per-piece decomposition reframes**: instead of products across pairs,
treat each piece as a single integer subproblem and use **Lagrangian
relaxation** to couple them.

The master problem keeps the LP relaxation structure (continuous x and
y). The Lagrangian dual penalises violations of piece-uniqueness via
multipliers `λ[p]` per piece. Per-piece subproblems are then:

> "For piece p, choose at most one (cell, rotation) placement, maximising
> per-edge match credit minus Lagrangian penalty."

This is a small integer subproblem with **per-piece state space n_cells × 4 ≈ 800 placements** — solvable in O(800) per piece per Lagrangian iteration.

## Lagrangian formulation

### Master problem (unchanged from vol-44's LP)

Variables:
- `x[p, c, r] ∈ [0, 1]`: piece p in cell c with rotation r.
- `y[c, c', k] ≥ 0`: matched I-I edge between cells c, c' on color k.

Constraints (from [[border-enum-lp-ub]]):
1. Cell coverage: `Σ_{p, r} x[p, c, r] = 1 ∀ c`
2. **Piece usage: `Σ_{c, r} x[p, c, r] = 1 ∀ p`** ← this is what binds
3. B-I color match: forced equalities.
4. Hints.
5. y ≤ a (lhs piece side has color k), y ≤ b (rhs piece side has
   color k), `Σ_k y[c,c',k] ≤ 1`.

Objective:
```
max  60 + (B-I matches) + Σ_{(c,c') ∈ I-I, k} y[c, c', k]
```

LP relaxation gives UB ≈ 478. Constraint 2 is what makes the LP
fractional in x and creates the gap.

### Lagrangian dual

Relax constraint 2 by adding Lagrangian penalty:

```
L(x, y, λ) = (master objective)
           + Σ_p λ[p] · (1 - Σ_{c, r} x[p, c, r])
```

Note: piece-uniqueness equality is `Σ_{c,r} x[p, c, r] = 1`, so the
relaxation term is `λ[p] · (1 - Σ x[p, c, r])`. For `λ[p] ≥ 0` this
PENALISES using piece p more than once (negative residual).

Master is now separable by piece:

```
L(x, y, λ) = constant
           + Σ_p λ[p]                                              (Lagrangian constant)
           + Σ_p [ (per-piece y-credit when p is placed somewhere) - λ[p] · (uses of p) ]
           + (cell-coverage + B-I + hint constraints)
```

Per-piece subproblem: for each piece p, decide
```
x*[p, c, r] = argmax over (c, r) of:
    (sum over edges incident to (c, r): y-credit attributable to p)
    − λ[p]
```

Each subproblem has **800 candidate placements** for canonical 16×16.
Solvable in milliseconds via enumeration.

### Lagrangian dual maximisation

The Lagrangian dual is:
```
g(λ) = max_x L(x, y, λ)
```

We want `min_λ g(λ)` (the dual gives an upper bound on the integer
primal). Standard subgradient method:
1. Initialise `λ[p] = some prior` (e.g., uniform 1/n_pieces).
2. Solve per-piece subproblems (parallel, ~196 instances of size 800).
3. Aggregate `x*` solutions.
4. Update `λ[p] ← λ[p] + step_size · (Σ_{c,r} x*[p, c, r] - 1)`.
5. Repeat until convergence.

Convergence rate is `O(1/√t)` standard for subgradient. Should converge
within 100-1000 iterations on a well-conditioned problem.

### Why this closes the piece-uniqueness gap

The integer-rounding loss vol-50 identified (12 of 18 I-I gap points)
comes from fractional x at the LP optimum where the SAME piece is
"spread" across multiple cells in fractions. The Lagrangian dual
PENALISES this via λ[p]; at the dual optimum, fractional x is suppressed.

In the limit (large enough iteration count), the Lagrangian dual bound
EQUALS the integer programming primal bound, **closing the gap entirely**.

In practice, the dual is upper-bounded by the convex hull of the
per-piece subproblem solutions, which for integer subproblems is itself
integer. So the dual bound is tight on the piece-uniqueness constraints.

## Column-generation alternative

The Lagrangian dual is one approach. **Dantzig-Wolfe column-generation**
is the LP-dual viewpoint:

### Master LP

For each piece p, let `Z_p` = set of feasible placements (cell, rotation)
for that piece, given border + hint constraints. `|Z_p| ≤ 800` for
canonical.

Define LP variables:
- `z[p, k] ∈ [0, 1]`: weight of piece p's k-th placement.
- `y[c, c', k]` as before.

Constraints:
1. `Σ_k z[p, k] = 1 ∀ p` (each piece placed once, possibly fractionally
   across its candidates).
2. Cell coverage via z's induced occupancy.
3. y-match constraints, same as before but now in terms of z.

This is the SAME LP relaxation, just with a different basis.

### Pricing problem

In column-generation, the master starts with a small subset of placements
per piece. Pricing identifies new placements to add by their reduced
cost. The pricing problem is exactly the per-piece subproblem from the
Lagrangian view, parameterised by current LP duals.

**Equivalence**: Lagrangian dual and column-gen reach the same bound at
convergence. Column-gen is preferred in practice because it gives
**finite termination** (vs subgradient's asymptotic convergence) and
because modern LP solvers like HiGHS handle the master efficiently.

## Worked example sketch (6×6/5c)

To make this concrete, consider the 6×6/5c canonical puzzle: 32
pieces (4 corners + 16 edges + 16 interior). After hint pinning,
remaining problem: 12 interior pieces, 8 edge pieces, ~12 free cells.

Each piece has ≤ 50 feasible placements after border filtering.
Lagrangian or column-gen converges in 10-30 iterations.

Expected outcome on a 6×6/5c instance where LP UB = 22 but integer
best = 20 (made up numbers, exact need to be measured): the lifted
formulation closes the gap to UB = 20.

**This would be the proof-of-concept** that per-piece decomposition
works on small scale. The 16×16 question is then "does it scale?"

## Scaling estimate to 16×16/22c

| Component | Size | Per-iteration cost |
|---|---:|---|
| Per-piece subproblems | 196 pieces × 800 placements | ~80 µs each, 200 ms total per round (parallel) |
| Master LP solve | 196 pieces × ~50 active columns × y vars | HiGHS warm-start ~1-5 s after first solve |
| Pricing | 196 × 800 reduced-cost evals | ~10 ms total |
| Iterations to converge | ~100-1000 | 5-50 min wall on 8-core M1 |

**Estimated total**: 10 min - 1h per canonical-E2 basin to compute
the lifted LP UB, vs current standard LP at ~2.5 min. **2-25× slower
per basin**, but with potentially tighter bound (~5-15 points closer
to integer).

## Engineering cost estimate

To ship a working version:

1. **Lagrangian / column-gen master loop in Rust**: 3-5 days.
   - Reuses good_lp + HiGHS already in v2/.
   - Reuses vol-44 border_ub.rs infrastructure for the y-LP.
2. **Per-piece subproblem solver**: 1-2 days.
   - Pure enumeration; trivial parallelism.
3. **Convergence diagnostics + early-stop**: 1 day.
4. **6×6 validation**: 1 day.
5. **Canonical-E2 measurement + comparison to LP-478**: 1 day.

**Total: 7-10 days of focused engineering** to ship a measurable result.

## Comparison to vol-47's McCormick failure

| Aspect | Vol-47 McCormick | Vol-52 per-piece |
|---|---|---|
| Variable count | O(n²) lifted z | O(n) per-piece columns |
| Subproblem structure | None (monolithic) | Decomposable per-piece |
| Convergence | Pure LP solve | Iterative, but finite |
| Scaling at 16×16 | Intractable | 5-50 min/basin estimated |
| Failure mode | Computational explosion | Convergence rate / numerical issues |

**Key structural difference**: McCormick lifts the LP itself (more
vars, more constraints). Column-gen / Lagrangian DECOMPOSES the LP
along the piece-uniqueness axis (smaller subproblems, master is
still LP). The latter scales because subproblems are independent
and parallel-friendly.

## Open questions before any code

1. **Numerical stability of subgradient on 196-dim λ**: standard
   issue at this scale. Trust-region methods (e.g., bundle methods)
   may help. Out of scope for the design doc; flagged for build.

2. **Cuts for the master LP**: even with piece-uniqueness handled,
   the y-LP itself has its own fractional gap (~6 points per vol-50
   analysis). Standard Gomory + clique cuts may close part of this.
   Separate concern from per-piece decomposition.

3. **Termination criterion**: column-gen exits when no negative-reduced-
   cost column exists. Subgradient exits at fixed point or by step-size
   schedule. Choose based on master LP performance.

4. **Hot-start across basins**: when applied to a new border, can we
   warm-start λ from a similar border's converged values? Could save
   most of the iteration cost.

## Recommendation

Pursue per-piece column-generation as the LP-tightening approach for
vol-53+. The math is sound; the engineering is contained (7-10 days);
the expected payoff is closing ~12 of the 20-point LP-integer gap
(67% of it). This would not directly produce a 459+ record, but
would give us:

1. A tighter UB to use as CSP-search bound (prune more aggressively).
2. A way to **prove** basins are at their integer optimum (closing
   the dual gap = optimality certificate).
3. A foundation for any future no-good / CDCL learning.

The standing 458 record may indeed be the global optimum on class-A
border. A tight LP-UB-per-basin would confirm this within minutes of
compute per basin.

## Linked

- [[lp-integer-gap-anatomy]] — vol-50 measurement that motivates this
- [[lifted-lp-formulation]] — vol-47 McCormick design (refuted at canonical scale)
- [[lifted-lp-column-generation]] — vol-47 column-gen attempt (under/over-counting bugs)
- [[lp-ub-478-basins]] — vol-44 basin survey
- [[exact-joint-bound]] — earlier MaxSAT attempt (wont-do)
- [[border-enum-lp-ub]] — vol-44 LP formulation
- [[../sessions/vol-50]], [[../sessions/vol-51]] — predecessor sessions

## Vol-52 disposition

This concept page IS the vol-52 deliverable. No code shipped. The 7-10
day engineering build is **vol-53+ work** if/when a future volume
picks it up.
