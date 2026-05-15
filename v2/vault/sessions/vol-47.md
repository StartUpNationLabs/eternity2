# Vol-47 — Polyhedral lifting of E2 LP (research session)

**Theme**: Tighten the E2 LP relaxation via McCormick on bilinear
edge-match terms. Multi-day research-paper-grade work.

**Status**: ongoing. First two formulations attempted, both incorrect
for different reasons. Real lifting requires careful column-generation
dualization.

## What was attempted

### Naive lifting (vol-47 milestone 4)

`crates/bench-audit/src/border_ub_lifted.rs::lifted_lp_ub`

For each I-I edge × color-matched (p1, r1, p2, r2) pair, introduce
$z_{e, p_1, r_1, p_2, r_2}$ with McCormick:
- $z \le x_1$, $z \le x_2$, $z \ge x_1 + x_2 - 1$, $z \ge 0$
- Per-edge cap: $\sum_z \le 1$.

Objective: $\sum z + B$-$I$ terms.

**Smoke tests**:
- 6×6/4: 22k z-vars, 2.5s. UB = 60 = standard ✓
- 8×8/4: 300k z-vars, 60s. UB = 112 = standard ✓
- 8×8/6: 200k z-vars, **TIMES OUT at 60s budget**. NoSolutionFound.
- 10×10/6: 1.25M z-vars, TIMES OUT. NoSolutionFound.

**Scaling problem**: canonical 16×16/22 would have 5-20M z-vars,
totally intractable for HiGHS.

### Column generation v1 (vol-47 milestone 5)

Two-phase:
1. Phase 1: standard LP, extract x-values.
2. Phase 2: lifted LP with z-vars ONLY for "active" pairs
   (where x > 0.05 in phase 1).

Phase 1 on vol-32 458 board: 1179 active candidates total, avg 6 per
cell (vs 764 total cands). z-vars dropped from 20M to **2067**.

**But result was WRONG**: UB = 402 < integer optimum 458. The LP was
under-counting because removing y-vars and only keeping z-vars for
active pairs gave NO credit to matches involving low-x candidates.

### Column generation v2 (hybrid z + y)

Kept y-vars in phase 2 as fallback for inactive pairs, added z-vars
for active pairs, per-edge cap = sum(z) + sum(y) ≤ 1.

**Result**: UB = 479.58 — **HIGHER than the standard LP UB of 478**.
That's invalid — adding constraints (McCormick) should only
decrease the LP optimum, never increase it.

**Why it's wrong**: z-vars and y-vars represent the SAME match
contribution in different forms. Allowing the LP to use BOTH paths
to credit a single edge match = double-counting.

## What I've learned (mid-vol)

1. **Naive lifting at canonical scale is intractable**. 20M vars exceeds
   HiGHS practical limits.
2. **Naive column generation is also wrong**: restricting z-vars
   under-counts; hybrid z+y over-counts. The correct formulation
   needs a different approach.
3. **The correct column generation** for this LP is essentially
   **Lagrangian relaxation with cutting planes**:
   - Start with standard LP (no z-vars).
   - Solve.
   - Look at the current LP solution. For each I-I edge, find pairs
     (p1, r1, p2, r2) where the McCormick LB ($z \ge x_1 + x_2 - 1$)
     would be VIOLATED by the current solution (if z = 0 but
     $x_1 + x_2 > 1$).
   - These are **violated McCormick LB constraints**. Add them as
     CUTS (with z auxiliary vars) to the LP.
   - Re-solve.
   - The LP UB decreases by each round of added cuts.
   - This is the standard cutting-plane method for tightening LP
     relaxations.

This is what I should have implemented. Open for next session.

## Open: correct column-generation cutting-plane algorithm

```
loop:
    solve current LP
    for each I-I edge e:
        for each color-matched (p1, r1, p2, r2):
            if x[c1, p1, r1] + x[c2, p2, r2] > 1 + epsilon:
                # current LP allows two pieces to be "both placed"
                # at adjacent cells — but they're competing
                add cut: z auxiliary + McCormick LB
    if no cuts added: converged
    re-solve with new cuts
```

The cuts SHOULD tighten the LP because they add new constraints.

**Probability of meaningful tightening**: depends on whether the
standard LP's fractional solution has $x_1 + x_2 > 1$ for many
adjacent-cell candidates. From the col-gen v1 finding, the standard
LP concentrates on ~6 candidates per cell with x > 0.05. Most
$x_1 + x_2$ should be ≤ 1.05. Probably **not many cuts will fire**.

But even a few cuts could tighten the LP a couple of points. Worth
implementing.

## Theoretical analysis of why this is hard (vol-47 conclusion)

The McCormick lifting on bilinear binary products is **theoretically
correct** but has two practical obstructions on E2:

### Obstruction 1: variable count

The naive lifting introduces $z_{e, p_1, r_1, p_2, r_2}$ for every
color-matched (piece-rotation, piece-rotation) pair across every
I-I edge. For canonical-E2 with the 458 board's border:
- 196 interior cells × ~764 candidates = ~150k x-vars (manageable).
- 364 I-I edges × ~14000 color-matched pairs = ~5 million z-vars.
- 3 McCormick constraints per z = ~15 million constraints.

HiGHS, even at 8 threads, presolve + IPM + crossover, can't handle
this in reasonable time. We saw on 10×10/6 (1.25M z-vars) the LP
times out at 60s. Canonical is 4× larger.

### Obstruction 2: column-generation pricing is non-trivial

Standard column generation: start with subset of z-vars, find which
to add via reduced-cost. For the lifted LP, the **reduced cost of a
missing z-var depends on dual values of ALL constraints**, including
the McCormick LBs of OTHER z-vars not yet added.

Without exact reduced costs, heuristic pricing (e.g., "add z-vars
for pairs where x1+x2 > 1 in current LP") **doesn't preserve the
relaxation property**. We demonstrated:
- v1: dropping y-vars makes the LP STRICTER than integer feasible
  (UB = 402 < integer 458). Invalid bound.
- v2: keeping both y and z double-counts match credit
  (UB = 479.58 > standard 478). Invalid relaxation.

### Why this matters for E2 research

The standard LP UB 478 on the 458 board is the best LP-relaxation
bound we can compute in tractable time. The 20-point integer-LP gap
is REAL relaxation slack, but the McCormick lifting that should
close it is computationally intractable AND requires careful
column-generation algebra that good_lp doesn't natively support.

**This is a documented negative result**: McCormick lifting on the
canonical-E2 edge-match LP is *theoretically valid but practically
intractable* at the puzzle scale, given current LP solver
technology and our column-generation expertise.

For future work in this direction, the correct path is **Lagrangian
relaxation with cutting planes**, implemented at a lower level than
good_lp (direct HiGHS API access to add cuts incrementally and
extract correct duals). That's a multi-week build, not multi-day.

## Pivot decision

Given:
1. Naive lifting is intractable.
2. Heuristic column generation produces invalid bounds.
3. Correct cutting-plane requires deeper LP infrastructure than
   good_lp provides.

The next research direction should NOT be more lifted-LP work. Better
candidates:
- **Multi-day Blackwood algorithm port** — known successful target
  (community 469), vol-15 has groundwork.
- **RL self-play for value-order** — vol-30 T2, deferred several
  volumes. Only direction that can structurally beat the imitation
  ceiling.

Both are ~1-2 week investments. The lifted-LP exploration produced
real research-grade output (the documented negative result) but
won't break records in the time available.

## Linked

- [[lifted-lp-formulation]] — design doc for naive lifting
- [[lifted-lp-column-generation]] — design doc for col-gen (had bugs)
- [[border-enum-lp-ub]] — standard LP
- [[vol-46]] — predecessor session
