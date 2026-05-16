---
title: Mathematical structure of the 459-level set on canonical E2
date: 2026-05-16
status: synthesis
---

# Math notes — structure of the 459-level set (vol-110)

A theoretical synthesis of the empirical data accumulated through
vol-110, framing the canonical 5-clue E2 459 problem in
mathematical language.

## Notation

- $W = H = 16$, board cells indexed by $p \in \{0, ..., 255\}$.
- $\mathcal{P}$ = set of 256 piece-rotations × 4 rotations.
- A board is $b: \{0, ..., 255\} \to \mathcal{P}$ injective.
- Matched-edge score $s(b) \in \{0, ..., 480\}$.

## Empirical observations (rigorously measured)

### (E1) The 459-level set is non-singleton

There exist $b_{60}$ (vol-60) and $b_{110}$ (vol-110 pipeline)
with $s(b_{60}) = s(b_{110}) = 459$ but
$|\{p : b_{60}(p) = b_{110}(p)\}| = 3$ (the 5 canonical hints minus 2).

### (E2) Both basins are MIP-halo-1 locally optimal

For each $i \in \{60, 110\}$ and each defect cell $c \in D_i$
(cells where $b_i$ has unmatched edges), the joint MIP over
$\bigcup_{c} \mathcal{N}_1(c)$ returns $\Delta = +0$. That is, no
local permutation of pieces within a halo-1 region improves score.

Concretely:
- $b_{60}$: 4 defect components, 35 defect cells, 59-cell joint
  region, $\Delta = +0$ proven in 1800s (vol-90).
- $b_{110}$: 2 defect components, 33 defect cells, 52 + 4 cells,
  $\Delta = +0$ proven (vol-110).

### (E3) σ-permutation between basins is board-spanning

Define $\sigma_{b \to b'}$ on positions by
$\sigma(p) = (b')^{-1}(b(p))$ (where $b$ is read as the piece
at $p$). The cycle decomposition of $\sigma_{b_{60} \to b_{110}}$
has cycle lengths $[143, 31, 28, 25, 20, 2, 2, 2]$. The giant
cycle has 143 cells — 56% of the board.

### (E4) σ-subsets between 459 basins are score-preserving / decreasing

The full 143-cell cycle, applied as a permutation to $b_{60}$,
yields $b_{110}$ with score 459 (preserving). Subsets applied
in isolation yield boards with score < 459 (vol-99 generalisation
of the indecomposability finding).

### (E5) σ-permutation 459 → McGavin 469 is also board-spanning

From vol-65/99/101: $\sigma_{459 \to 469}$ has cycle lengths
including a giant ~80-cell cycle. Applying the full cycle to a 459
gives the 469 board. Applying any proper subset gives a board with
score $\le 459 - 4$.

## Theorem candidates

### Conjecture C1: The 459-level set is a clustered rigid set

**Claim**: The set $L_{459} = \{b : s(b) = 459, b \text{ valid placement}\}$
decomposes into $K \geq 2$ "basins" where each basin is the
connected component under halo-1 local moves, and each basin is
MIP-halo-1 locally optimal.

**Evidence**: (E1), (E2) prove $K \geq 2$. Sweep of more
seed-offset pipeline trajectories could find more.

**Open**: Is $K$ finite? Likely yes (finite cells × finite pieces).
Counting / enumeration is open.

### Conjecture C2: σ-orbits on $L_{459}$ are large

**Claim**: The σ-permutation group acting on $L_{459}$ has
orbits whose elements are connected by σ-cycles of cardinality
$\geq 80$ cells (board-spanning).

**Evidence**: (E3), (E4), (E5).

**Open**: Whether the σ-orbit graph on $L_{459}$ is connected
(i.e., all 459 basins reachable from one via repeated σ-cycle
moves).

### Conjecture C3: Local-search lower bound

**Claim**: No deterministic algorithm using only halo-$r$ moves
for $r \leq R$ can lift a 459 basin past 459, for some
$R \leq 4$ that's MIP-provable per basin.

**Evidence**: (E2) at halo-1, vol-93/100 at halo-2/4 on $b_{60}$.

**To do**: extend MIP halo-2 / halo-3 / halo-4 to $b_{110}$.

### Conjecture C4: 460+ requires board-spanning structural move

**Claim**: Any operator $\phi$ that satisfies $s(\phi(b)) \geq 460$
for some 459-basin $b$ must touch at least $K$ cells where
$K \geq 80$ (lower-bounded by the smallest 459→469 σ-cycle).

**Evidence**: (E4), (E5) plus MIP rigidity at all tested radii.

**Implication**: local ALNS (max destroy-set 30-80 cells, but
typically constrained to halo-3 regions ≤ 50 cells) cannot lift
459. The 451-459 plateau we've measured is structural.

## Constructive paths to 460+

Given the theorem candidates, three paths emerge:

### Path A: Subset σ-cycle + compensating local fixes

Find a $\sigma$-cycle subset of cardinality $K \leq 80$ that
loses $L$ edges via the subset application AND find local moves
that recover $L+1$ edges. The combined move has $\Delta = +1$.

**Mathematical structure**: this is a bi-objective IP:
- σ-variables: 80-cell cycle subset selection.
- Local-move variables: K cells whose pieces are re-chosen.
- Constraints: piece-uniqueness, edge-match consistency.
- Objective: maximize $s$ post-move.

**Tractability**: hard but bounded — at most $2^{80}$ σ-subsets ×
finite local moves. Branch-and-bound with σ-cycle structure should
be feasible for $K \leq 20$.

### Path B: Multi-basin σ-merge

Find two 459 basins $b, b'$ such that mixing them (selecting some
cells from $b$, others from $b'$) yields a 460+ board. This is a
piece-set blend problem: each cell can take from $\{b(p), b'(p)\}$.

**Bound**: There are at most $\binom{253}{k}$ blends differing in
$k$ cells between $b$ and $b'$. Exhaustive at small $k$, sampled
at larger $k$.

**Empirical link**: today's pipeline finds 459 from offset=100. The
new 459 differs from vol-60 459 by 253 cells. Some blend might be
460+.

### Path C: Reformulation via piece-set similarity to McGavin

Build a feature: cluster-count, total-defect-cells, σ-distance-to-McGavin.
Train an ML model that predicts "lift-potential" from these features.
Use the prediction to bias ALNS / pipeline. Vol-30+ RL self-play
mentioned but not built.

**Cost**: model training is multi-week. RL self-play has
unbounded reward search space.

## What to do next (implementation)

In order of effort vs payoff:

1. **MIP halo-2/3/4 on $b_{110}$** (1-2 hours): confirms C3 at higher
   radii. If $b_{110}$ is halo-3 rigid, then path A is the only
   one with theoretical support.

2. **Pipeline orbit characterization** (1 day): apply the pipeline
   100 times from different starts; count distinct 459 basins
   reached. Tests C1's $K$ count.

3. **Subset σ-cycle CP** (path A) on a 459→459 σ-cycle (which we
   have between $b_{60}, b_{110}$): can a 20-cell subset + 5-cell
   local-move achieve $\Delta = +1$? Multi-day formulation +
   implementation.

4. **Piece-set blend** (path B) on $b_{60}, b_{110}$: sample 1000
   blends, score each. Cheap (~minutes).

## Path B + Path A simple form: EMPIRICALLY REFUTED (2026-05-16)

Tested both in their simplest forms:

**Path B test**: enumerated all $2^n$ σ-cycle subsets between 4
distinct 459 basins (6 pairs total). **No subset gives score > 459.**
Best non-trivial = 451-455. (See [[concepts/multiple-459-basins-rigid]].)

**Path A test (small cycles)**: applied a single σ-cycle subset (size
2-11) between two 459 basins, then ALNS-recovered. Results:

| pair / cycle | intermediate score | post-ALNS |
|---|---:|---:|
| pipeline ↔ pipeline, size 3-11 | 445-456 | 458-459 |
| vol-60 ↔ pipeline, size 2     | 452-455 | **459** |

**All ALNS-recovered scores ≤ 459.** ALNS recovers the lost edges
but does not exceed 459.

**Generalised empirical claim**: across direct ALNS, pipeline
(bound-ascent + Hungarian + ALNS), σ-subset + ALNS (within cluster),
and σ-subset + ALNS (cross cluster), the score CEILING is 459. The
459-level set is an absorbing region for these algorithmic operators.

Path A's full version (subset σ-cycle + compensating local fix via
CP, not ALNS) might still work — it'd need to explicitly construct
the +1 move via constraint programming, not rely on ALNS's local
search. **Multi-day formulation; defer to vol-111+.**

## Linked

- [[concepts/multiple-459-basins-rigid]] — empirical foundation.
- [[concepts/new-459-from-bf-pipeline]] — origin of $b_{110}$.
- [[PAPER_2026-05-16_canonical_E2_rigidity_theorem]] — vol-83-101
  rigidity theorem foundation.
- [[concepts/sigma-cycle-topology-3-basins]] — vol-65 σ-cycle theory.
- [[sessions/vol-110]] — session journal.
