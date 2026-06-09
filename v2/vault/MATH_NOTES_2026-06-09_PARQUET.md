---
tags: [math, bound, parquet, vol-203]
date: 2026-06-09
status: in-progress
---

# PARQUET — math notes (vol-203)

Goal: derive an UNCONDITIONAL upper bound on canonical E2 matched-edges
that is strictly below 480, using the 2×2 feasible-patch structure that
all prior LP/MIP relaxations relax away.

## Why every prior bound = 480

The per-color budget $\sum_c \lfloor N_c/2 \rfloor = 480$ is tight
(Selby-Riordan). The per-cell-pair LP (vol-44) and Hall (vol-122 B4)
both = 480 because each lets a piece's rotation/color be chosen
fractionally and independently per edge. The atomicity of a piece — that
its 4 sides rotate *together* — is relaxed. So is the fact that a piece
occupies *one* cell.

The 2×2 feasible-patch object is the smallest unit that encodes
piece-atomicity (4 sides locked by one rotation) **and** local 4-edge
coupling. 99.88% of random distinct 4-tuples have NO feasible rotation
assignment (measured vol-203). A perfect 480 board is a tiling whose
every 2×2 window (all 225 overlapping ones) is feasible.

## Formulations, from loosest to tightest

### F0. Aligned-block packing relaxation (counting only; loosest)

Partition the 16×16 grid into 64 disjoint 2×2 blocks (8×8 super-grid).
A perfect board assigns each super-cell an *internally-matched* block
(4 internal edges matched) AND the cross-block boundaries match.

**Relaxation F0**: ignore cross-block boundaries. Ask only:
> Can we choose, for each of the 64 super-cells, an internally-matched
> 2×2 block, using each of the 256 pieces exactly once?

This is a set-partition feasibility. If INFEASIBLE, then no board has all
256 block-internal edges matched simultaneously. Block-internal edges
number $64 \times 4 = 256$. If F0 is infeasible, **at least one
block-internal edge is unmatched in every board**, i.e. matched ≤ 479.
Weak, but a START — and unconditional.

Better F0-opt: **maximize the number of super-cells filled with an
internally-matched block** (piece-unique), via assignment/matching. If
the max is $K < 64$, then $\ge (64-K)$ blocks have ≥1 internal mismatch
⇒ matched ≤ $480 - (64-K)$. Still ignores cross-block edges (those could
add more mismatches, only lowering the true max — so this is a valid UB).

This is a degree-constrained matching / IP: variables $x_{v,b}=1$ if
block $b$ placed at super-cell $v$. Constraints: one block per super-cell
($\sum_b x_{v,b} \le 1$), each piece used ≤ once
($\sum_{v,b: p \in b} x_{v,b} \le 1\ \forall p$). Maximize $\sum x_{v,b}$.
LP relaxation gives an UB on $K$, hence a (weak) UB on score.

CAVEAT: this counts only the 4 ALIGNED partitions' internal edges. The
aligned partition is arbitrary; there are 4 ways to tile 16×16 with 2×2
blocks offset by (0,0),(0,1),(1,0),(1,1) (with border handling). Each
gives a DIFFERENT set of 256 "internal" edges. A valid bound: run F0-opt
on the offset that yields the *smallest* max-K → tightest of the 4.

### F1. Overlapping-patch LP (the real object)

Index all overlapping 2×2 patch-positions $q \in Q$, $|Q| = 15×15 = 225$.
For each $q$, its alphabet $A_q$ = feasible (4-tuple, rotation-tuple)
assignments respecting border colors at board-edge patches and the 5
hint pins. Variable $y_{q,a} \in [0,1]$, $a \in A_q$.

Constraints:
1. **One assignment per patch**: $\sum_a y_{q,a} = 1\ \forall q$.
   (Every 2×2 window of a real board IS some feasible patch — so in a
   real board exactly one $a$ is "active" per $q$. For a relaxation we
   can use $\le 1$ or $=1$; $=1$ is valid because a complete board fills
   every patch.)  --- BUT a board with mismatches has INFEASIBLE patches
   at some windows. So $=1$ over feasible-only $A_q$ is the **480
   feasibility** question, not a score bound. For a SCORE bound we must
   allow "this patch is one of the infeasible tuples" → see F2.
2. **Overlap consistency**: adjacent patches share 2 cells; the shared
   piece-ids + rotations must agree. Linear equalities linking $y$'s.
3. **Piece-uniqueness**: each piece in exactly one cell ⇒ appears in the
   1–4 patches covering that cell with consistent id. Linear.

If F1 with $=1$ is LP-INFEASIBLE → no 480 board exists (unconditional!).
If LP-feasible → inconclusive for existence but the dual may still bound.

### F2. Score-LP via patch-defect counting (tightest, the target)

Allow every patch to be any 4-tuple (feasible or not), but charge the
*minimum internal mismatches* of the chosen tuple. Define for a patch
the internal mismatch count $\mu(a) \in \{0,1,2,3,4\}$ = min over
rotations of #unmatched internal edges. Feasible patches have $\mu=0$.

Each interior edge belongs to exactly 1 or 2 overlapping 2×2 patches
(edges on the patch grid interior belong to 2; near board border, 1).
We want to MAXIMIZE matched = $480 - (\text{total mismatches})$.

The subtlety: an edge shared by 2 patches is double-counted in
$\sum_q \mu$. Need a careful accounting so each edge's mismatch is
counted once. This is the crux of getting a valid, tight LP. See
"edge-accounting" below.

## Edge-accounting for F2 (the careful part)

A clean route: do NOT sum patch-defects. Instead use patches only to
generate VALID INEQUALITIES (cutting planes) on an edge-matching LP.

Base LP (gives 480): binary $m_e \in [0,1]$ per interior edge = "matched".
Objective $\max \sum_e m_e$. With no constraints, $=480$.

Patch cut: for any 2×2 window $q$ with cells assigned, the 4 internal
edges cannot ALL be matched unless the 4-tuple is feasible. Since
99.88% of tuples are infeasible, *generically* $\sum_{e \in q} m_e \le 3$.
But this depends on WHICH pieces are at $q$ — which the edge-LP doesn't
track. So the cut must be over a formulation that ties edges to pieces.

⇒ The honest tight formulation coAuples pieces and edges. That is exactly
F1 + objective. Resolve by: variable $z_{c,p,r}$ = piece $p$ at cell $c$
rotation $r$ (assignment polytope: $\sum_{p,r} z_{c,p,r}=1$ per cell,
$\sum_{c,r} z_{c,p,r}=1$ per piece). Edge matched indicator derived from
$z$. The 2×2 feasibility becomes: forbid the 4 specific $z$'s of an
infeasible patch from being simultaneously 1 — a clause / cover
inequality. Adding ALL such cuts to the assignment LP and solving gives
an UB ≤ 480, possibly strict.

This is large (256 cells × 256 pieces × 4 = 262k z-vars) but the
assignment LP is totally unimodular at the per-cell/per-piece level; the
patch cuts break unimodularity and create the gap. The question is
whether the LP with patch cuts has optimum < 480.

## Plan of attack (compute order)

1. **F0-opt first** (cheap, decisive direction): max-K aligned-block
   piece-unique packing, all 4 offsets, LP + IP. If max-K < 64 on any
   offset → immediate unconditional UB < 480. This is the fastest
   possible win and uses the existing super-block enumerator.
2. If F0 gives 64 (no bound), go to F1 existence-LP (does a 0-defect
   patch tiling LP exist?).
3. F2 assignment-LP + patch cuts for the tight bound.

Step 1 is today's compute. Everything hinges on whether the
piece-supply for internally-matched blocks can cover all 64 super-cells.

## What would make this publishable

A bound of the form "matched ≤ 480 − k for some k ≥ 1, unconditionally"
would be the FIRST nontrivial UB on canonical 5-clue E2 score. Even k=1
is a real result (proves 480 is not achievable... only if k≥1 AND sound).
Conversely a clean proof that F0/F1 = 480 tells us the obstruction is
NOT at the 2×2 scale — pushing us to 2×3 / 3×3 (where forbidden-rate is
100% on random tuples, vol-138).

---

## RESULTS (2026-06-09, vol-203)

All experiments use the independent verified loader/scorer (McGavin 469/480 ✓).
Test instances: generated small puzzles, perturbed to be unsatisfiable-perfect
with KNOWN true maxes (brute-force B&B, validated against no-bound DFS).

### Soundness gate
- Known solutions of generated puzzles score PERFECT (24/24, 40/40, 60/60,
  112/112) — after fixing the piece-id-ordering trap (CSV must be written in
  canonical id order; see memory project_e2_small_puzzle_pieceid_trap).
- Integer assignment model = exact true max on every test (40,38,37,37,58).
- PARQUET sound tightening: LP-UB ≥ true max on every instance. ✓ sound.

### The per-edge color-mass LP is already strong
On COLOR-BALANCED unsatisfiable-perfect instances (counts preserved, so the
per-color budget stays = #edges — the canonical-E2 regime):

| instance | #edges | true max | base per-edge LP | PARQUET (2×2 cuts) |
|---|---:|---:|---:|---:|
| g5_bal_k1 | 40 | 38 | 38.410 | 38.337 |
| g5_bal_k2 | 40 | 37 | 38.318 | 38.112 |
| g5_bal_k3 | 40 | 37 | 38.275 | 38.179 |
| g6_bal_k1 | 60 | 58 | 58.000 | 58.000 |

The base per-edge LP (color-mass `t[e,k] ≤ min(ΣL_k, ΣR_k)` + assignment) is
already within ~1 of the true max on geometric obstructions — much stronger
than the vault's "per-color LP = 478/480" because it couples color
availability to the actual piece assignment at both edge endpoints.

### F0 counting bound is vacuous
Aligned-block alphabets: corner 1312, edge 73003, interior 4,059,952 (3
translation-invariant classes; 147.9M total). Per-color budget = 480 with
ZERO slack, all 22 colors even. Supply is ample ⇒ no counting obstruction.

### 2×2 patch cuts barely tighten, and CANONICAL LP = 480
- The sound 2×2 patch cut `Σ_{e∈q} m[e] ≤ 3 + Σ_a w[q,a]` is valid but the
  fractional LP relaxes around it (puts fractional w-mass) ⇒ Δ ≤ 0.2.
- On canonical 16×16 the base per-edge LP = **480.000** (perfect color
  balance + rotation freedom let the LP saturate every edge fractionally).
  2×2 cuts cannot remove that fractional 480 point.

### CONCLUSION — the LP-bound direction is capped at 2×2 scale
The 2×2 patch is too local to bound canonical below 480 via LP: the
fractional polytope contains a balanced 480 point that no 2×2 cover cut
removes. To get an unconditional sub-480 LP bound would require:
- 2×3 / 3×3 patch cuts (100% forbidden on random tuples, vol-138) lifted to
  valid inequalities — much larger alphabets, column generation needed; OR
- the INTEGER solve (exact but intractable at 16×16, = the kissat-UNKNOWN
  regime Anjou confirmed); OR
- a genuinely different relaxation (SDP / Lasserre level-2 on the patch
  polytope) — open.

This is a clean NEGATIVE result: **2×2-patch LP relaxation does not crack
480.** It also REPOSITIONS the research: the leverage is constructive
search, not bounds (see [[lague-rubik-transfer-ideas]]). The per-edge LP's
surprising near-tightness on small geometric obstructions is itself a useful
artifact (a strong, cheap UB oracle for sub-boards / windows — reusable as an
admissible bound in an IDA* constructive search).

### What WOULD still be worth trying on the bound side (backlog)
- Lasserre/SOS level-2 moment relaxation restricted to 2×2 patch monomials.
- 2×3 patch cuts via column generation (separate only violated 2×3 covers).
- Per-window INTEGER subproblems as cuts (solve a window's 6-cell MaxSAT to
  get an exact local mismatch floor, lift to a board inequality) — this is
  Anjou's seqAMO-strip idea applied as a cutting plane rather than a final
  optimum.
