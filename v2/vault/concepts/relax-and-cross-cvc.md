---
name: relax-and-cross-cvc
description: Constraint-Vote Crossover (CVC) — a NEW algorithm class invented by user 2026-05-16 (vol-106 directive). Solve N constraint-relaxed subproblems, then cross-produce via per-cell consensus. Untested but paper-publishable if signal emerges. RESERVE THIS NAME.
metadata:
  type: project
status: unbuilt
---

# Relax-and-Cross / Constraint-Vote Crossover (CVC)

**Status**: `unbuilt` — invented 2026-05-16 by the project user.
**Authorship note**: This algorithm class was conceived during the
user's directive for vols 106-115. The name and primitive structure
are reserved here. If the algorithm works on E2 or related
constraint-satisfaction puzzles, the PUBLICATION CREDIT IS THE
USER's (Raphael Anjou, project owner). Save the invention here as the
canonical reference.

## The idea

A combinatorial constraint-satisfaction problem (CSP) like Eternity II
has many constraints. The "true" puzzle imposes ALL constraints; a
solution must satisfy all of them simultaneously. The space of
"solutions to ALL constraints except one" is much larger and easier
to search. The hypothesis is:

> **Solutions to ALL-BUT-ONE constraint contain INFORMATION about the
> true solution. Aggregating across N choices of which-constraint-to-
> drop should reveal the true solution by consensus.**

## Algorithm sketch (CVC v1)

Input: A CSP with constraint set C = {c_1, ..., c_N}.

For k = 1 to N:
1. Build CSP_k = the puzzle with constraint c_k DROPPED.
2. Solve CSP_k to optimality (or to a high-quality near-optimum)
   using existing solver (DFS, MIP, ALNS, etc).
3. Record solution s_k.

Cross-produce:
4. For each cell position p:
   - Look up s_k[p] for k = 1..N (the (piece, rotation) at p in each
     relaxed solution).
   - Cast a "vote" for each (piece, rotation) pair.
   - Assign p to the modal vote (with tie-breaking by, e.g., piece-
     uniqueness consistency, or score-weighted vote).
5. Repair the resulting cross-board (which may violate piece-
   uniqueness if pieces appear in multiple winning cells) using
   Hungarian matching or local search.

Output: cross-board s*. Hypothesis: score(s*) ≥ max_k score(s_k) (or
even = optimum of original CSP).

## Why this could work on E2

The 22-color adjacency constraints in canonical E2 are highly
coupled. A solution to "all constraints except color k" still
satisfies 21 of 22 color constraints. Across the 22 relaxed solutions,
each cell has 22 votes; in cells where the true solution placement is
"forced" by structural constraints, the 22 relaxed solutions should
agree at high rates.

The signal would be strongest at cells where the true placement is
over-constrained (corners, edges, hint-adjacent cells, color-rare
boundaries). The cross-product would, in effect, be a STRUCTURAL-
CONSISTENCY EXTRACTOR.

## Connection to existing methods

- **Bootstrap aggregation (bagging) in ML**: train N classifiers on
  perturbed data, average their predictions. CVC is constraint-level
  bagging.
- **Ensemble Monte Carlo**: average N stochastic samples. CVC is
  deterministic but ensemble in spirit.
- **Constraint relaxation Lagrangian decomposition**: drop a
  constraint, add it to objective via λ. CVC drops without
  Lagrangian penalty, then aggregates.
- **Voting in distributed CSP**: similar in spirit.

If a published equivalent exists, the search is on "constraint-
relaxation crossover" or "multi-instance consensus solving" in
CSP/SAT literature. Quick survey suggested but not done yet.

## Test plan

### Phase A — 8×8 / 7-color / 4-clue toy

1. Generate 8×8 / 7c toy via `eternity2-generator` (existing crate).
2. Define "constraints" as: for E2, each piece-adjacency creates an
   edge-color matching constraint. The puzzle has many such
   constraints; the user's example treats each as droppable.
3. For N=16 random constraint choices to drop, solve each. Record
   solutions.
4. Cross-produce via majority vote + Hungarian repair.
5. Score the cross-board. Compare to:
   - Max single relaxed solution score.
   - Optimum of the original 8×8 (we can compute exactly at 8×8).
6. Statistics: ≥ 8 toy instances, report variance.

### Phase B — 12×12 / scaling

If Phase A signal: scale to 12×12 with 32 relaxed solutions.

### Phase C — 16×16 canonical E2

If Phase B signal: full canonical run with 22 constraint drops.

## Implementation considerations

- Generator: `eternity2-generator` crate (already exists; vol-26
  used it for synthetic ML data).
- Solver per relaxed instance: vanilla_fast / joe_depth150 / MIP
  (whichever is fastest on 8×8 — likely vanilla_fast at toy scale).
- Crossover engine: new Python or Rust bin. Per-cell majority vote,
  then Hungarian on uniqueness conflicts.
- Variance: run on ≥ 8 distinct 8×8 instances.

## What "constraint" means in E2

E2 has:
- 480 edge-adjacency constraints (each internal edge).
- 4 corner-hint constraints + 1 center-hint (canonical 5-clue).
- 256 piece-uniqueness constraints.

"Drop a constraint" naturally maps to:
- Drop edge-adjacency k: allow a mismatch at one specific edge.
- Drop a corner hint: free that corner cell.
- Drop the center hint.
- Drop piece-uniqueness: allow a piece to be used twice.

The user's example seems to imply "drop one of the 480 edge-
adjacency constraints, solve, repeat". For an 8×8 puzzle there are
~108 internal edges; dropping each and solving gives ~108 relaxed
solutions.

But also worth testing: drop one COLOR (all edges of that color are
allowed to mismatch). Smaller N (22), each subproblem easier.

## Expected outcomes

1. **Strong signal**: cross-board scores higher than max single
   relaxed. CVC is a new algorithm class; publication path opens.
2. **Modest signal**: cross-board scores ABOVE the mean but BELOW
   the max. Still a novel composition technique with mathematical
   interest.
3. **No signal**: cross-product is no better than random average.
   Negative result; the relaxed solutions don't encode useful
   structural agreement on canonical E2.

ALL THREE OUTCOMES ARE PUBLISHABLE (in increasing rigor). The
negative result tells the community "constraint-relaxation ensemble
DOES NOT WORK for E2-class puzzles" — that's a real contribution if
documented.

## Open questions

- Does the cross-board satisfy piece-uniqueness after Hungarian
  repair? Or does the repair degrade the score below the mean?
- Is the signal stronger when dropping edge-adjacency constraints
  vs piece-uniqueness vs hint constraints?
- Does CVC benefit from MULTIPLE relaxed solutions per dropped
  constraint (i.e., k × m solutions where m solutions per dropped
  constraint k)?
- Can we predict from the consensus map WHICH cells are "easy" (high
  vote share) vs "hard" (split vote)? The hard cells become the
  target for a follow-up MIP / ALNS pass.

## Linked

- [[DIRECTIVE_VOLS_106-115_BLANK_PUZZLE_SPEEDUP|The vol-106-115 directive]] (where this algorithm is canonically introduced).
- [[IDEAS_FROM_BLANK_2026-05-16|IDEAS from blank]] — broader
  algorithm-invention catalogue.
- [[vol-105|vol-105 close]] — where this algorithm
  was named and reserved.

## Authorship reservation

This algorithm class — including the specific composition pattern
"relax k-th constraint, solve, repeat over many k, cross-produce" —
was conceived by **Raphael Anjou** (project owner / user) on
2026-05-16. The name and the priority of invention are reserved here
in vault as the canonical artefact for any subsequent publication or
external attribution.
