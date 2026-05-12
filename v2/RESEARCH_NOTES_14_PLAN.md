# RESEARCH_NOTES_14_PLAN.md — vol-14 mission brief

> **🛑 VOL-14 RETROACTIVE CORRECTION (2026-05-12 evening)**: this
> plan cites "75,173 valid 60-cell frames" as if it were a
> complete enumeration. Vol-14 discovered it is a lower bound from
> a 120-second time-budgeted DFS. The plan's expectation that 75k
> covers the Hamilton-ring space was wrong. The frame-first
> direction (#4/#5 below) is still valid, but the input set is a
> sample, not a population.

**Written**: 2026-05-12 14:40 CEST, at vol-12/vol-13 closeout.
**Read first**: `RESEARCH_NOTES_12.md`, `RESEARCH_NOTES_13.md`, the
memory entries listed below.

## Where we stand at vol-14 start

**Our stack ceiling**: 454/480 (vol-6 PT warm-started; cold-start CP+ALNS
in vol-12 hits 443/480 in ~10 min combined).

**Verified community ceiling**: 469/480 (McGavin 2020).

**Bar for vol-14**: ≥454 cold-start (catch up to vol-6 without warm-
start), ≥469 anywhere (tie SOTA), ≥470 anywhere (clear SOTA, session-
defining).

### Calibrated baselines from tonight's runs

| stack | budget | score | notes |
|---|---|---|---|
| vol-12 `joe_depth150_par` CP cold | 5 min | depth 174, 303/480 | bitset + NS-1 + depth-150 gate + multi-core; ~14k nps aggregate |
| vol-12 CP → vol-9 ALNS fill | 5 + 5 min | **443/480** in 15 s, flat for 285 s | ALNS hits local opt at iter 30; can't escape |
| vol-6 warm-started PT (historical) | many h | 454/480 | the bar to beat from cold start |

### Diagnostics from vol-12 + vol-13

1. **Engine throughput** is no longer the binding constraint single-
   thread (+63% nps, +5 depth from bitset; +6.6× from multi-core).
   The depth-174-in-5-min plateau is **algorithmic-bound**, not
   throughput-bound.
2. **ALNS plateaus at iter 30** with constant-T SA. Net improving
   accepts: 0 in 5 min after the initial fill. The destroy/repair
   ops find the same local opt repeatedly.
3. **Edge-color BP** carries 2.24× more signal than vol-11's cell-BP
   (18.84% vs 8.4% interior reduction) and *beats random* as value-
   order in Python — but is not yet wired into the Rust engine.
4. **Hamilton-cycle frame enumeration** on canonical 5-clue yields
   **75,173 valid 60-cell frames** in 120 s. Frame-first decomposition
   is tractable.
5. **vol-13 structural finding**: rare colors {1..5} live exclusively
   on the parallel-to-border axis of edge pieces — interior pieces
   have **zero** rare edges. The 56 edge pieces' E/W edges form a pure
   rare-color sub-CSP (56 cells × 5 colors, 24 of each, paired around
   the ring). Solvable in isolation and decouples the ring problem
   from the interior.
6. **vol-13 null**: tensor-network / boundary-MPS at any bond dim can't
   break the 10¹⁰¹ overcounting factor — global piece-uniqueness is
   the binding rigidity, not local matching.

## Vol-14 mission

The user instruction from vol-12 carries forward: *"do everything, do
not wait for confirmation, no time estimates, explore unwalked
paths"*. Vol-14's contribution should be a **portfolio of all v6-v13
learnings composed in one runnable stack**, not another isolated probe.

### Punch list (ranked by EV)

**1. Port edge-BP marginals into the Rust engine as a value-order**
   *(highest EV — directly attacks the depth-plateau, smallest scope)*
- New `ValueOrder::EdgeBpMarginals` variant in `EngineConfig`.
- Load `output/v12_bp/edge_bp_60i.json` (284 KB) at solver init.
- In `recurse()`, score candidates by `Σ_side marginal[edge_id][color]`.
- Combine with `joe_depth150_par`. Honest expected outcome: depth
  220+ in 5 min on canonical E2 cold-start, possibly above vol-6's
  cold-start 308 ceiling.
- Scope: ~2-4 focused hours.

**2. Joe-Saunders TRUE RESTART loop (not just gate)**
   *(2nd highest — breaks ALNS plateau analogue for CP)*
- Outer loop wrapping `recurse()`: after N=1600 iterations at depth
  >T=150 without progress, prune back to depth T and rerandomize seed.
- Documented empirically at 17-49% iteration reduction by Joe
  (`docs/community-mining/05_Joe_pruning_method_thread.md`).
- Combine with edge-BP value-order.

**3. Replace ALNS constant-T with PT replica-exchange or cooling**
   *(addresses tonight's "0 improving accepts in 285s" plateau)*
- Vol-9 saw the same diagnostic. ALNS at T=1.0 wanders without
  escaping. Either:
  - **Cooling schedule**: T_start=2.5, T_end=0.05 over the budget;
  - **PT replica-exchange**: 8 ALNS replicas at different temperatures,
    swap rarely (vol-6 used PT for this reason).
- Wire as `localsearch::run_alns_pt` or extend existing `run_pt`.

**4. Rare-color edge sub-CSP (vol-13 Finding 2 actionable form)**
   *(novel, decouples a hard subproblem)*
- Build a 56-variable CSP: variables = the 56 edge-piece cells, domains
  = 60 (piece × rotation), constraints = pair-wise rare-color matching
  along the ring × rare-color multiset {12,12,12,12,12}.
- Solve with the engine (or kissat — 56 vars × 5 colors is well within
  10×10 SAT reach).
- Yields **all valid edge-piece-on-ring arrangements**. Filter the
  75,173 Hamilton frames by which rare-color assignment they realize.
- Feed surviving (frame, rare-coloring) pairs to the 14×14 interior
  solver.

**5. Frame-first × interior sweep**
   *(uses vol-12's 75k frames)*
- For each of the (≤ 75k) frames surviving the rare-color filter:
  pin the 60 border cells, run `joe_depth150_par` on the residual
  14×14 with a 30 s budget per frame.
- Parallel over cores. With 8 workers × 30 s/frame, full coverage
  is ~6-12 wall hours; 1 hour gets ~5,000 frames.
- This is the systematic "for each starting border, try the interior"
  attack the community has never done on canonical 5-clue.

**6. Remaining bitset polish + verhaard preferred-pieces wiring**
   *(low risk, integrative — combines vol-9's Verhaard work with v12's
   bitset engine)*
- vol-9's `VERHAARD_PREFERRED` profile is built but only useful when
  `SolveOpts.preferred_pieces` is populated. Wire a phase-0 SA pass
  that produces the preferred list, then run CP with PreferredFirst.

**7. ALNS Houdayer cluster moves**
   *(higher-variance escape mechanism)*
- `crates/localsearch/houdayer_offline.rs` already exists. Plug in
  as an ALNS destroy operator. Vol-6 mentioned this as an escape
  mechanism for stuck SA.

### What success looks like

- **Tier 1**: edge-BP value-order ported, measurable depth lift.
- **Tier 2**: ≥454 cold-start (catch up to vol-6 without warm-start).
- **Tier 3**: ≥460 cold-start, or measurable structural artifact from
  rare-color sub-CSP / frame-first.
- **Tier 4**: ≥469 (tie SOTA), or ≥470 (clear SOTA, session-defining).

### Risks / failure modes

- **The 10¹⁰¹ overcounting (vol-13)** says local methods are bounded.
  Anything in the v14 portfolio that doesn't enforce global piece-
  uniqueness rigidly is bounded — that includes edge-BP. The CP engine
  enforces it, so plug-ins (BP marginals as heuristic) are safe; pure-
  BP solvers are not.
- **ALNS plateau (tonight)** suggests cooling alone may not be enough.
  Be prepared to also ship Houdayer if cooling-only PT also plateaus.

### Operating rules (carried from v12)

- Read-only on v6-v13 artifacts unless updating stale memory.
- New files go in `output/v14_*`, `scripts/v14_*`, new
  `crates/<new>` or extend `solver-engine` / `localsearch`.
- All commits to `develop` with `Co-Authored-By: Claude Opus 4.7
  (1M context) <noreply@anthropic.com>`.
- Update auto-memory when finding something session-defining.
- Honest framing: failure is information. Calibrate against ≥454
  for cold-start and ≥469 for ceiling — anything else is below.

### Initial actions for vol-14

1. **Read** `RESEARCH_NOTES_12.md`, `RESEARCH_NOTES_13.md`, and the
   following memory entries (in this order):
   - `project_e2_state.md`
   - `project_e2_vol12_engine_profiles.md`
   - `project_e2_edge_bp_measurement.md`
   - `project_e2_hamilton_frame_count.md`
   - `project_e2_rare_color_geography.md`
   - `project_e2_mps_relaxation_null.md`
   - `project_e2_ns1_deficit_invariant.md`
   - `project_e2_dead_ends.md` (READ CAREFULLY — vol-11 mistake)
   - `project_todo_engine_bitset.md` (now mostly complete)
2. **State the plan** (which 1-2 punch-list items to do tonight) and
   commit `RESEARCH_NOTES_14.md` before writing code.
3. **Ship #1 (edge-BP value-order port)** as the safest highest-EV
   first deliverable. Measure depth vs `joe_depth150_par` baseline
   on canonical E2 5 min.
4. Pick a #2 based on time remaining: #2 (Joe restart) and #3 (PT
   cooling) are independent and can run in parallel with #1.

### Files of record at vol-14 start

- `output/v12_run/run_e2_5min_board.json` — cold-start CP 5 min,
  303/480.
- `output/v12_fill/alns_443.json` — ALNS fill from above, 443/480
  in 5 min (plateaued).
- `output/v12_bp/edge_bp_60i.json` — converged edge-BP marginals
  (the input for v14 #1).
- `output/v12_hamilton/frames_30s.json` — 100-frame sample of the
  75k Hamilton frames; full enumeration is 56 MB and gitignored.
- `output/HISTORIC_first_454_1778567792.json` — vol-6 record board
  (used as warm-start in v14 #5 if frame-first stalls).

Session closed at 2026-05-12 14:40 CEST. Vol-14 starts whenever the
user spins up the next session.
