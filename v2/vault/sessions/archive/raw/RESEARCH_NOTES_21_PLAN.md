# RESEARCH_NOTES_21_PLAN.md — vol-21 entry plan

Date: 2026-05-13 (drafted at vol-20 close).
Read [[RESEARCH_NOTES_20.md]] first if you haven't.

## State at vol-20 close

- **Cold-start ceiling**: 457/480 — proven a strict local maximum
  under every local move family of cardinality ≤ 5 we measured.
- **Operator-lock confirmed across basins**: pinned-blackwood and PT
  from 445/441 basins also lock at their respective scores.
- **Bottom-left "backbone" is scan-order artefact** (vol-17 finding
  corrected): only 5 canonical hints have cross-source structural
  agreement.
- **The 457 basin strongly attracts**: basin-hop perturbations of
  Δ=-2,-4 are reabsorbed by 30s ALNS.

We have used all the *local-search-on-one-axis* tools we have. To
go past 457, we MUST do at least one of:
1. Find a *genuinely different* 457-class basin (one with different
   geometry that admits its own +1).
2. Build a *new operator class* on a different axis or higher K.
3. Build a *new algorithm* (prune-restart, edge-grid dual).

## Vol-21 priorities (ranked by EV × build-cost)

### T1 — McGavin in-place prune-restart engine (1-2 days build, est. +5..10)

Memory `project_e2_mcgavin_blackwood_gap_analysis` (vol-14) describes
this exactly. Algorithm sketch:

1. Run standard Blackwood CP until reaching a hard wall (e.g. depth ~150).
2. *Instead of backtracking past depth d*, treat the current partial
   as having locked-in pieces 0..d-1 with their domains.
3. Re-prune the remaining cells from depth d onwards using these
   locked pieces as constraint sources (richer than starting AC-3).
4. Restart depth-first search from depth d under the new pruning.
5. Iterate the prune-restart cycle.

Key implementation: the engine needs `PruneAndRestart` policy that
"forgets" recent backtracking history but keeps deeper constraint
inferences. Memory of failures = no-good learning at the lock depth.

**Why this matters**: McGavin's 469 is reached by exactly this. Joe's
2019 result was 11h SAT-solve on a pre-pruned domain that took 2 weeks
of Blackwood pre-search. Both rely on in-place prune-restart that we
don't have.

Implementation file: `crates/solver-engine/src/lib.rs` — add
`PruneRestart` variant of `EngineConfig::variable_order` or a new top-
level policy. Reuse `EngineSolver::blackwood_raw_par`.

### T2 — Cooperative-pair swap operator from N4 Δ=-1 candidates (3-4 hours)

N4 found 23 pairs at Δ=-1 (single transpositions) all in the top-band.
Many share endpoints. Conjecture: 2 of these Δ=-1 swaps, *composed*,
might give Δ=0 or +1 (R5f cooperativity).

Build ALNS op `CooperativePairSwap`: pre-compute the 23 Δ=-1 swap
edges; offer pairs (i,j) that share an endpoint as a single move.
Each move = 3-cell permutation (a→b→a' with shared b). Test against
the 457 board: do any 2-Δ=-1 compositions give Δ ≥ 0?

If yes: ship it as a new ALNS op + use in hot-PT.

### T3 — Edge-grid dual reformulation PoC (1-2 days build, exploratory)

Variables: 480 interior edge colors instead of 256 cell pieces.
Constraints: each cell's 4 edge tuple ∈ piece multiset / 4 rotations.
Move: flip one edge color → check if both adjacent cells still admit
a piece.

This is N1 from vol-20 catalog. Different basin geometry; the 76-cell
σ-cycle in vol-18 might correspond to a much shorter edge-flip path.

Build: `crates/edge-search/` new crate. Need:
- Edge variable encoding.
- Piece-table lookup by (N,E,S,W) tuple modulo rotation.
- Edge-flip SA.
- Sanity-check: solver should reach the same scores as our current ALNS.

### T4 — Color-relabel as search variable (4-8 hours)

Joint search space: (placement, color-permutation π ∈ S_23). At
stuck plateau, try π that swaps two color labels — physics
unchanged, but Blackwood/BP/gacolor heuristics re-rank cells. This
is N2 from vol-20 catalog.

Build: extend `gacolor` propagator to test multiple π in parallel.
At plateau, fan out across `π` choices; pick best.

### T5 — Diverse 457 search (overnight compute)

Generate many 457-class basins by:
- 50+ different CP partials (chunks 0001-0021 + new top-down ×
  schedule-variant combinations).
- Apply OracleCycleSwap from our known 456 oracles to each.
- Run hot-PT from each.

Goal: find ≥3 distinct 457 boards, then re-run operator-lock
analysis on each. The 457 lock might be specific to OUR basin.

Build cost: 0 (uses existing pipelines, just orchestration).
Compute cost: ~6-12h.

### T6 — Build basin_hop into ALNS as new op (2-3 hours)

The basin_hop perturbation test (in vol-20) showed that ALNS reabsorbs
Δ=-2 perturbations. **But a larger perturbation might escape.** Try
Δ=-6,-10,-15 perturbations: force-break k matched edges, run ALNS.

If escape rate > 0 at some k, build "ForcedPerturb" as a meta-op that
intermittently injects a Δ=-k jolt into PT chains.

## Vol-21 entry tasks

1. Read this plan.
2. Read [[RESEARCH_NOTES_20.md]] for the operator-lock measurements.
3. Read memory `project_e2_vol20_operator_lock` for the exhaustive
   move-family null record.
4. Pick T1 (prune-restart engine) as the highest-EV. Start building.
5. In parallel, run T5 in background (cheap).

## Out-of-stack ideas (parking lot)

Beyond T1-T6, the following are *future* directions:
- Implement Joe's 2019 SAT post-pruning approach (1-week build).
- Build piece-orbit-as-atom search (N9 from vol-20).
- Hardness-map adaptive pinning (N10, easy).
- Hash-cons tabu in PT chains (N8 from vol-20, mentioned in vol-14
  memory as missing).
