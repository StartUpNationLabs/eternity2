---
name: lifted-lp-formulation
description: ~20-point integer gap on every sampled basin. To break records we
status: unbuilt
metadata:
  type: concept
---
# Polyhedral lifting of the E2 LP relaxation (vol-47)

**Status**: design phase.
**Origin**: vol-44/45/46 showed the standard LP relaxation has a
~20-point integer gap on every sampled basin. To break records we
need a TIGHTER LP. This is the design for a McCormick-lifted variant.

## The bilinear obstruction

The standard E2 LP (from `crates/bench-audit/src/border_ub.rs`) has:
- **x-vars**: $x_{c,p,r} \in [0,1]$ = mass of piece $p$ at cell $c$
  with rotation $r$.
- **y-vars**: $y_{e,k}$ for each I-I edge $e = (c_1, c_2)$ and color
  $k$, with $y_{e,k} \le a$ and $y_{e,k} \le b$, where
  $a = \sum_{p,r : \text{side}_{s_1} = k} x_{c_1, p, r}$ is the
  "side-color mass" on $c_1$'s side facing $c_2$, similarly $b$ for
  $c_2$.

The objective is $\sum_e \sum_k y_{e,k}$, plus B-I terms.

**The bilinear truth** the LP is relaxing:

$$\text{match}_e = \sum_{k} \mathbf{1}[\text{side}_{c_1,s_1}=k]
  \cdot \mathbf{1}[\text{side}_{c_2,s_2}=k]
= \sum_{p_1,r_1} \sum_{p_2,r_2}
  x_{c_1,p_1,r_1} \cdot x_{c_2,p_2,r_2}
  \cdot \mathbf{1}[\text{edge}_{p_1,r_1,s_1}=\text{edge}_{p_2,r_2,s_2}]$$

The product $x_{c_1,p_1,r_1} \cdot x_{c_2,p_2,r_2}$ is the bilinear
term. The standard LP replaces it with $\min(a, b)$, which is
**linear in $x$** but loose (allows fractional mass-spreading to
fake matches).

**Vol-44 measurement**: LP UB 478 vs combinatorial 480, integer best
458 (gap 20). Most of the 20-pt gap is **LP slack** from this
linearization.

## The lifting (McCormick on bilinear binary products)

Introduce **z-vars** for each I-I edge × matched-pair-of-piece-rotations:

$$z_{e, p_1, r_1, p_2, r_2} \in [0, 1]$$

defined only for $(p_1, r_1, p_2, r_2)$ tuples where the colors match:
$\text{edge}_{p_1, r_1, s_1} = \text{edge}_{p_2, r_2, s_2}$.

The McCormick envelope for $z = x_1 \cdot x_2$ with
$x_1, x_2 \in [0,1]$:

- $z \le x_1$
- $z \le x_2$
- $z \ge x_1 + x_2 - 1$
- $z \ge 0$

In our setting:
- $z_{e, p_1, r_1, p_2, r_2} \le x_{c_1, p_1, r_1}$
- $z_{e, p_1, r_1, p_2, r_2} \le x_{c_2, p_2, r_2}$
- $z_{e, p_1, r_1, p_2, r_2} \ge x_{c_1, p_1, r_1} + x_{c_2, p_2, r_2} - 1$
- $z_{e, p_1, r_1, p_2, r_2} \ge 0$

**Objective**: maximize
$\sum_e \sum_{(p_1,r_1,p_2,r_2)\text{ color-matched}} z_{e, p_1, r_1, p_2, r_2}$
+ B-I terms + 60 (B-B constant).

This **lifts** the LP into a higher-dimensional polytope where the
integer-feasible region is a face of the LP-feasible region. Bounds
from this lifted LP are at most equal to the standard LP and
typically much tighter.

## Tightening properties

**Claim 1**: lifted LP UB ≤ standard LP UB.

*Proof sketch*: any solution to the lifted LP induces a solution to
the standard LP by aggregating $y_{e,k} = \sum_{(p_1,r_1,p_2,r_2)\text{ with color }k} z_{e,p_1,r_1,p_2,r_2}$.
Constraints carry over. The objective coincides. So the lifted LP
is a tighter relaxation. □

**Claim 2**: at integer solutions, the lifted LP matches the integer
optimum exactly.

*Proof sketch*: when $x \in \{0,1\}$, the McCormick constraints
$z \le x_1, z \le x_2, z \ge x_1 + x_2 - 1$ force $z = x_1 \cdot x_2$
exactly. So the lifted LP's continuous relaxation equals the
integer LP at integer points. □

**Tightness depends on the LP corner.** The lifted LP doesn't always
match integer-optimum at fractional corners. But it's typically much
tighter than the standard LP relaxation.

## Size estimates

Standard LP on canonical-E2 458 border:
- ~108k x-vars
- ~8k y-vars (364 edges × 22 colors)
- ~16k constraints
- Solve time ~150s with HiGHS IPM + crossover.

Lifted LP, naive instantiation:
- ~108k x-vars (same).
- z-vars: 364 edges × (191 interior pieces × 4 rotations)² = 364 × 583k = **212 million z-vars**.
- Constraints proportional. **Intractable.**

**Sparse instantiation** (the key implementation trick):

For each I-I edge $(c_1, c_2)$, only instantiate $z_{e, p_1, r_1, p_2, r_2}$ for tuples where:
- $(p_1, r_1)$ is a *candidate* at $c_1$ (passes domain filters: not pinned, color-feasible).
- $(p_2, r_2)$ is a candidate at $c_2$.
- The edge color match constraint holds:
  $\text{edge}_{p_1, r_1, s_1} = \text{edge}_{p_2, r_2, s_2}$.

After border + hints are pinned, **most candidate counts per cell drop to
~500-700** (vol-44 measurement: avg 553 cands per interior cell on
the 458 board's border).

Per I-I edge, the matching count: for each color k, expected matches
= (cands at c1 with color k on side s1) × (cands at c2 with color k
on side s2) ≈ (550/22)² × 22 ≈ **14k color-matching pairs per edge**.

Total z-vars: 364 × 14k ≈ **5 million**. Still big, but tractable
with sparse LP + HiGHS. Memory ~1-5 GB. Solve time ~30-60 min per LP.

If too slow, **further restrict** to pairs where $(p_1, r_1)$ is in
the **top-K most-likely cands** at $c_1$ (e.g., K=50). This reduces
to 364 × 50² × 22 ≈ 40M / 22 ≈ a few hundred k z-vars. Fast.

## Expected outcome

**Vol-44 standard LP**: vol-32 458 → UB 478, gap 20.

**Lifted LP prediction**:
- If LP is now near-tight: UB drops to 459-462 (gap 1-4).
- If McCormick still leaves slack: UB drops to 470-474 (gap 12-16).

Either way, **a tighter UB tells us the true basin ceiling**. If
lifted UB on vol-32 458's basin is 460, we know that basin caps at
460. To break 458 → 462+ requires finding a basin with higher lifted
UB.

If lifted UB is **identical** to the integer optimum (458 here), the
formulation is **exact** on this instance. Useful diagnostic.

## Implementation plan

1. **Sparse z-var enumeration**: for each I-I edge, list color-matched
   (p1, r1, p2, r2) tuples. Pre-compute once.
2. **LP build**: x-vars + z-vars + McCormick constraints (3 per z-var) +
   piece-uniqueness + cell-coverage + B-I (as before).
3. **Solve with HiGHS** (good_lp interface, IPM + crossover, 8 threads).
4. **Compare lifted UB to standard UB** across our basin reps.

## Open theoretical questions

- **Does the lifted LP have an integrality gap on E2 at all?** If
  zero, this single LP gives integer optimum — but that would also
  imply we can solve E2 with LP, which seems unlikely.
- **Does adding ROTATION-LIFTING** (z = u·r where u = piece-at-cell,
  r = piece-uses-rotation, both fractional) help further? Multi-level
  lifting.
- **Could we use the LP DUAL** of the lifted LP to identify which
  specific edge-pair constraints are binding? That'd diagnose the
  basin structure.

## Linked

- [[border-enum-lp-ub]] — standard LP design
- [[lp-ub-478-basins]] — basin survey showing the 20-pt gap
- [[per-color-lp-ub-458]] — per-color analysis suggesting B-I bottleneck
- [[b-i-saddle-point]] — saddle structure in current LP
- [[vol-46]] — predecessor session
