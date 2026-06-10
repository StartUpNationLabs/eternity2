---
tags: [math, bound, vol-208]
date: 2026-06-10
status: derivation (pre-build)
---

# Strip-cut bound — can window-integer cuts break the 480 LP saturation? (vol-208)

Worked out while the TRANSEPT construction gates ran. Motivated by PARQUET's open
note ("per-window integer subproblem → board cutting plane, Anjou seqAMO-as-cut")
and today's gate measurement (bottom strata are integer-infeasible-to-perfect from
the depleted pool).

## The 480-saturation problem (why every cheap bound gives 480)

Canonical E2 per-color budget is exactly tight: $\sum_c \lfloor N_c/2 \rfloor = 480$
with zero slack (vol-65). Any relaxation that sees only **color counts** returns
480. PARQUET confirmed: base per-edge color-mass LP = 480.000 at 16×16 (though it's
within ~1 of true max on 5×5 — the gap is hidden by fractional freedom at scale).

To prove a board scores $<480$ we need an obstruction from the **adjacency
structure** that no color-count argument captures.

## Strip reformulation of a perfect board

Split rows into top $T=\{0..r-1\}$ and bottom $B=\{r..15\}$, seam = 16 edges with
color sequence $s=(s_0,\dots,s_{15})$. A board scores 480 $\iff$
$$\exists\,(P_T,P_B)\text{ partition of the 256 pieces},\ \exists\,s:\quad
T \text{ perfectly fills } 16\times r \text{ with bottom-colors } s,\ \wedge\
B \text{ perfectly fills } 16\times(16{-}r) \text{ with top-colors } s.$$
(The gate explores exactly this object — and finds the bottom half integer-
infeasible-to-perfect once $P_B$ is the greedily-depleted pool.)

## Why a *color* strip relaxation is still vacuous

Relax global piece-uniqueness across the seam (pieces usable in both halves) and
relax each half to color-flow. Each half then $\le$ its own per-color cap; the two
caps sum to $\ge 480$. **The seam adds no color-count obstruction.** Confirmed dead
— matches the gate's Q4 (per-stratum color balance non-selective).

## The non-vacuous cut: window-integer < window-LP

The leverage is the **integrality gap at the window scale**, surfaced as a cut on
the global LP. Algorithm (column-and-cut / Benders-flavored):

1. Solve global per-edge LP $\Rightarrow$ value 480, fractional assignment $z^\*$.
2. Pick a window $W$ (a $k$-row strip, or a $a\times b$ block) where $z^\*$ is most
   fractional / where $\sum_{e\in W} m^\*_e$ is closest to its perfect count.
3. Solve the window's **integer** max-matched conditioned on its boundary demands
   read from $z^\*$ (round/fix the boundary), via seqAMO-MaxSAT (Anjou-tractable:
   16×k strips solve to OPTIMUM in seconds). Get $\mathrm{opt}_W < |E_W|$.
4. If $\mathrm{opt}_W < \sum_{e\in W} m^\*_e$, add the **cut**
   $\sum_{e\in W} m_e \le \mathrm{opt}_W$ (valid: any integer board restricted to
   $W$ matches $\le \mathrm{opt}_W$ edges given that boundary class).
   — Subtlety: the cut must be conditioned correctly so it's valid for ALL integer
   boards, not just those matching $z^\*$'s boundary. Safer valid form: a
   **lifted** cut $\sum_{e\in W} m_e \le \mathrm{opt}_W + \sum (\text{boundary
   slack terms})$, or generate cuts over a COVER of boundary classes. This is the
   crux of soundness and where the real work is.
5. Re-solve LP with the cut. Repeat until LP $<480$ or no improving cut found.

## Open questions this build answers
- Does ANY window have integer-max < LP-value at 16×16 with a *valid* boundary-
  free (or boundary-lifted) cut? (5×5 had gap ~0.4; does a 16×3 strip have a usable
  integer gap once boundary is handled soundly?)
- Does the cut loop converge below 480, or does the fractional LP always route
  around finitely many window cuts (as it routed around 2×2 cuts in PARQUET)?
- If it converges below 480 → **proves 480 impossible on canonical E2** (major).
  If it plateaus at 480 after many cuts → strong evidence 480 is LP-unreachable
  only via exponentially many cuts (also informative).

## Soundness hazard (the thing that killed naive versions)
PARQUET's 2×2 cut was sound because it was an *unconditional* per-window cover cut
(all 4 edges matched ⟹ a feasible patch is active), NOT conditioned on a boundary.
A strip integer-max IS conditioned on its boundary; making it a valid global cut
requires either (a) min over all boundary classes (expensive but sound), or
(b) a lifted inequality with boundary slack. Getting this right is the gate before
any number is trustworthy. **Do NOT report an LP < 480 until the cut is proven
valid unconditionally** (anti-pattern #1: never call a non-bound a bound).

## ★ STRATEGIC RE-EVALUATION (vol-208) — the sub-480 bound is probably chasing a non-existent object

Two analyses collapse the bound frontier:

**(1) Single-window cuts are vacuous or unsound.**
- *Unconditional* window cut (max internal-matched over free piece choice, valid
  globally): a small window (≤ a few rows) is **internally perfectible** from the
  256-piece set (only 16H pieces needed, huge freedom) ⇒ opt_W = perfect ⇒ cut
  trivial. **CONFIRMED empirically** (`window_maxsat`, free piece choice from 256):
  every interior window ≤16 cells is internally PERFECT — 2×3→7/7, 3×3→12/12,
  2×5→13/13, 3×4→17/17, 4×3→17/17, 2×8→22/22. opt_W = perfect for all tractable
  windows ⇒ the unconditional window cut adds nothing.
- *Conditional* window cut (opt_W given a boundary) is **unsound** as a global cut.
- Only a lifted/disjunctive cut with correct boundary-slack is both valid and
  non-vacuous — a hard multi-week build, and the fractional LP likely routes
  around finitely many such cuts (as it did the 2×2 cuts in PARQUET).

**(2) The deeper point: a 480 solution almost certainly EXISTS.**
E2 is a commercial puzzle designed by Monckton/Selby/Riordan to be **solvable**
with its 5 canonical clues (the €2M prize presupposes a complete solution; it went
unclaimed because no one *found* it, not because none exists). Therefore the TRUE
maximum matched-edge count on canonical E2 **is 480**. Consequently:
- **No sound upper bound below 480 can exist** — the bound *is* 480, exactly, and
  every correct relaxation (per-color, base per-edge LP, Hall, PARQUET) returns 480
  not because they're weak but because **480 is the right answer**.
- "Prove 480 impossible" (the theorem upside of frontier #2) is **chasing a false
  target**. Dropped.
- The entropy/transfer-matrix count W(16) is ≥ 1 (a 480 exists), so it can't show
  impossibility either.

**Redirection.** The bound direction can at best *confirm* 480 (already known to be
the answer), never beat it. The real game is squarely **finding** the 480 or a
record by construction/search — frontiers #1 (from-scratch into a higher novel
basin), #3 (σ-cycle-scale non-local construction), #4 (distributed-exact emulation).
This note is kept as the rigorous reason the bound frontier is closed, not as an
active build. (Caveat: if one doubted 480's existence, the bound would matter — but
the design + community consensus make that doubt unwarranted. The honest statement
is "no sub-480 bound exists *because* 480 is achievable.")

## Linked
- [[parquet-overlapping-patch]] — the 2×2 predecessor (capped at 480); this is the
  larger-window + integer-cut successor it explicitly left open
- [[transept-strip-assignment]] — the construction-side sibling (gates run same session)
- [[MATH_NOTES_2026-06-09_PARQUET]] — base LP derivation reused here
- `reference_anjou_experiments_2026_06_09` — seqAMO window-MaxSAT tractability (the cut engine)
