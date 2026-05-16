# Directive — Vols 106-115: Blank-Puzzle Speedup + Innovation

**Issued by user**: 2026-05-16 ~07:30 CEST.
**Supersedes**: vols 61-70 "invented algorithm" directive (which
covered vols 62-70, now considered closed).
**Status**: BINDING for vols 106 through 115 (10 volumes).

## The directive (paraphrased + structured)

> "I want our next 10 volumes at least to be, starting from a BLANK
> puzzle, how can we reach faster a state that seems to bear more
> answers."

The user wants the research pivot:

- **OLD framing**: improve our SOTA score (459 → 460+) from existing
  basins / partials.
- **NEW framing**: from a BLANK board, reach high-information /
  high-promise states FASTER and CHEAPER. The unit of progress
  shifts from "score" to "time to reach informative partials".

A "high-information state" is the kind of board that suggests where
the rest of the answer might live — call it a "knee" of the search
tree. Examples:
- Deep CP-partials with consistent propagation state.
- Cross-validated piece-placement constraints reached from multiple
  independent starts.
- States that survive multiple ablations.

## The three avenues (user-stated)

1. **Code optimization of our DFS**
   - Hot-paths inside `solver-engine` (vol-25 already shipped 7 fixes
     giving joe +22.4%, BLACKWOOD_RAW +27%).
   - Remaining wins enumerated in
     [[plans/BACKLOG#engine-perf-—-remaining-wins]] (5 items, est.
     +30-40% potential).

2. **Code optimization elsewhere** (search/heuristics/repair)
   - ALNS, PT, score_board, piece-cache, propagator hot paths
     outside engine.
   - Multi-core scaling — current parallelism is rayon::scope; could
     be improved with structured work-stealing or fork-join.

3. **NEW algorithm classes — paper-publishable inventions**
   - Crucial: "if no one solved this puzzle, then the algorithm to
     solve it does not exist". The path to publishability is to
     CREATE an algorithm.
   - User-given example: take 8×8 puzzle, relax constraint k for
     k=1..many times, collect each near-solution, then CROSS the
     solutions to combine them into a real high-score (or 480).
   - The relax-and-cross example is itself the kind of structure to
     pursue: a NEW algorithm class with a name and a paper.
   - Other invention directions worth exploring:
     - SDP / Lasserre at small grid sizes.
     - Continuous-relaxation gradient descent (IDEAS doc, idea B).
     - Multi-agent search across 24 corner perms (IDEAS doc, D).
     - Joint piece-set + cell-set MIP (IDEAS doc, E) — vol-105 T1
       was about to test this on 80-cell σ-cycle.
     - Group-theoretic σ-cycle enumeration (IDEAS doc, F).
     - Symmetry-breaking constraints (IDEAS doc, J).

4. **New ways of seeing the problem** (user-stated)
   - Reformulations: think of edges as a hypergraph, pieces as
     atoms with quantum-states, scores as Hamiltonians.
   - Cross-domain analogues: jigsaw puzzles, tile-set covering,
     graph homomorphism, polytope vertex enumeration.

## User-provided concrete example (CRITICAL — save this)

> "What if we took an 8x8 and computed relaxed solution (like -1
> constraint, for multiple times on different constraints) and then
> crossed the solution to see if a real solution/high score emerges
> from them."

Concretization:
1. Take 8×8 / 7-color / 4-clue toy puzzle (close to E2's structure,
   tractable).
2. For each constraint k = 1..N, RELAX constraint k (drop it), solve
   the modified problem.
3. Each relaxed solution scores ~480 against modified puzzle but
   matches the original puzzle in 7 of 8 columns / rows / colors.
4. CROSS-PRODUCE: build a combined board by majority-vote / median /
   piece-set-intersection across the relaxed solutions.
5. Hypothesis: the cross-product is closer to the true solution than
   any single relaxed solution, because the constraint that's relaxed
   in each is satisfied in N-1 of them.

This is a NEW algorithm class. It has the flavor of:
- **Iterative consensus** (à la voting / median absolute deviation).
- **Majority-rule cooperative search** (parallel solvers agree on a
  basin).
- **Constraint-relaxation Lagrangian-decomposed crossover** (similar
  spirit to alternating direction method of multipliers, ADMM).

Suggested vol name: **"Relax-and-Cross"** or **"Constraint-Vote
Crossover"** (CVC). To be tested first on 8×8 (per user), then
scaled if signal emerges.

## What this directive DOES NOT mean

- We do NOT pause score-axis work entirely — if a record-class break
  emerges during one of these vols, document it.
- We do NOT abandon the rigidity theorem / PAPER work — that's
  durable knowledge.
- We do NOT undo committed code.

## What this directive DOES mean

- New vols (106+) are framed around BLANK-PUZZLE COLD START, not
  warm-start from records.
- "Time-to-informative-state" is the new metric, alongside score.
- Innovation tracks (algorithm invention) take priority over "more
  ALNS lottery" patterns.
- Code-quality and speedup investments are first-class deliverables.

## Vol-106 binding items (suggested, user to confirm on return)

T1: Code-optimization audit at canonical scale.
- Profile vanilla_fast + joe_depth150_bp_par with `samply` /
  `cargo-flamegraph` on a 5-minute canonical run.
- Identify the top 3 wall-clock hot paths; ship the cheapest two.
- Target: ≥ 15% time-to-depth-150 reduction.

T2: Build the "Relax-and-Cross" (CVC) algorithm on 8×8 / 7-color
- Implement the relax-by-1-constraint loop.
- Generate N ∈ {16, 32, 64} relaxed solutions.
- Build a crossover operator (majority-vote per cell + piece-set
  consensus).
- Measure: does the crossed board score higher than the mean of N
  relaxed solutions? Higher than the best single one?

T3: Concept-page write-up of CVC — first algorithm-class invention
of the new directive series.

## Linked

- [[IDEAS_FROM_BLANK_2026-05-16]] — original ideas catalogue.
- [[plans/BACKLOG]] — perf items.
- [[PAPER_2026-05-16_canonical_E2_rigidity_theorem]] — what we
  already proved structurally.
- [[INDEX]]
