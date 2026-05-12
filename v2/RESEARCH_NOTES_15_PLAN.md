# RESEARCH_NOTES_15_PLAN.md — vol-15 mission brief

**Written**: 2026-05-12 evening, at vol-14 closeout.
**Read first**: this doc, then:
- `~/.claude/.../memory/project_e2_vol14_session_summary.md` — the
  most up-to-date one-pager.
- `~/.claude/.../memory/project_e2_vol14_rectangle_path_findings.md`
  — captures the user's "fail-fast around hints" insight which
  shapes vol-15's priorities.
- `V15_BLACKWOOD_SPEC.md`, `V15_FRAME_ENUMERATOR_SPEC.md` — already-
  drafted implementation specs.

## Where vol-14 left things

**Best end-to-end on canonical E2**:
- Baseline `joe_depth150_par` + ALNS-fill: 442/480.
- BP-seeded baseline + ALNS-fill: 443/480.
- Vol-6 historical warm-PT from 453: 454/480.
- Community SOTA (McGavin 2020): 469/480.

**Vol-14 contributions**:
1. `ValueOrder::EdgeBpMarginals` — edge-color BP value-order. Net
   positive in pipeline (443 vs 442 baseline).
2. `PathSkeleton::HintRectangle{,Layered}` — user-proposed
   pre-commitment paths. Wins at 60s, loses at 300s. Ships as
   feature for short-budget regime.
3. Critical bug fix: ALNS was unpinning canonical hints, so all
   pre-vol-14-fix scores (vol-12's 443, vol-14's 442/443/436) were
   inflated. Honest baselines now in place.
4. Frame-first null: vol-12's 75 173 Hamilton frames are
   necessary-not-sufficient. Most are CSP-invalid as engine hints.
5. McGavin/Blackwood gap analysis: we're missing the heuristic-
   side schedule + break-index policy that gets the community to
   469.
6. Mismatch geometry: cluster is in center-bottom under top-down
   scan; same scan-order axis as community 469's top-region
   mismatches.
7. Per-cell backtrack distribution: 95% of search work is in the
   interior, peaking at layer-3 shoulder.
8. Initial domain map: 175 of 196 interior cells share the same
   764-plateau domain after hints + AC-3. Hint-adjacent cells
   (16) are 42-48; corners are 4; border is 56.

## The user's vol-14 insight that shapes vol-15

> "I feel like the faster we get stuck, the faster we will find
> the real solution?"

Half right. CSP theory says fail-fast IS good per-branch (MRV).
But to compound this across the search tree you need **learning**
between failures — no-goods (CDCL), conflict-directed backjumping,
or compile-time schedules (Blackwood). Our engine has none of
these, so vol-14's HintRectangle pre-commitments fail fast but
then exhaustively enumerate dead-end interior configurations
without learning.

**Vol-15 must capitalize on this insight by adding a learning
mechanism** of some kind.

## Vol-15 priority list

### Priority 1 (HIGHEST EV — Tier 4 attempt)
**Implement Blackwood's algorithm** per `V15_BLACKWOOD_SPEC.md`.

This is the production-tested "fail-fast against a global schedule"
approach. Reaches 469 in the community.

Components:
- Bottom-up row-major scan order (`ScanOrder::RowMajorBottomUp`).
- `BlackwoodSchedule { heuristic_sides, exhaustion_targets,
  break_indexes_allowed }`.
- `compute_heuristic_sides(puzzle, hints)` helper.
- `ValueOrder::BlackwoodHeuristic`.
- Hint × break-index collision handling (pos 45 hits bu_idx 221).

Estimated cost: 1-2 weeks.
Expected gain: +20-30 matched edges (443 baseline → 463+).

### Priority 1.5 (after Blackwood ships, test composition)
**Blackwood × HintRectangle / HintRectangleLayered composition**.

The two features are config-orthogonal (different EngineConfig
axes). Composing them is one line: set both `path_skeleton` and
`blackwood_schedule` on the same EngineConfig.

But composition might FIGHT because:
- HintRectangle forces a specific cell-order for the first ~49
  cells.
- Blackwood's heuristic-color exhaustion schedule expects a
  specific color-distribution at each depth.
- If the rectangle's first 49 cells under-exhaust heuristic
  colors vs the schedule, Blackwood will prune the whole branch
  immediately and the rectangle becomes a dead-end skeleton.

Test as a portfolio (parallel seeds, pick best):
- arm 1: Blackwood alone (validate standalone first).
- arm 2: Blackwood + HintRectangle (composition).
- arm 3: Blackwood + HintRectangleLayered (deeper composition).
- arm 4: HintRectangle alone (already shipped baseline).

~4 hours of integration + testing once Blackwood lands.

**Backtracking subtlety**: PathPolicy::PrefixConstraint forces
*cell order* at depths < k but does NOT prevent backtracking. If
Blackwood detects schedule violation at depth 50, the engine
backtracks normally — depth 50 → 49 → ... possibly all the way to
depth 0 — trying different pieces at each rectangle cell. This is
correct behaviour.

The risk: if NO (piece, rotation) combination at the rectangle's
49 fixed cells satisfies Blackwood's exhaustion schedule, the
search will exhaust and return Exhausted with 0 found. The cells
are fixed; only the pieces vary. Diagnostic: monitor outcome type.
- Exhausted with depth < 50: composition infeasible at current
  schedule; LOOSEN Blackwood's `exhaustion_targets` at early
  depths (try (idx 26 → exhaust 14), down from 28).
- TimedOut with depth ≥ 50: composition feasible; compare score
  to standalone Blackwood.
- Solved at depth 256: 480 found, vol-15 done.

### Priority 2 (CHEAP — capitalize on user's fail-fast insight)
**Hint-cluster sub-CSP enumeration**:

1. Identify the 21-cell "hint-anchored region" (5 hints + 16
   neighbours, all with domain ≤ 50 after AC-3).
2. Enumerate all valid configurations of this sub-region in
   isolation. Should be tractable (seconds-to-minutes given
   the small domains).
3. For each enumeration, commit as additional Hints, run
   `joe_depth150_bp_par` + ALNS-fill on the rest.
4. Multiplex across all sub-CSP solutions in parallel.

This is "fail fast where it's cheap, cache the results" — the
buildable version of the user's insight without needing full
CDCL. Each sub-CSP solution becomes a known-valid anchor; the
outer search no longer has to discover them.

Estimated cost: 1-2 days.
Expected gain: 0-15 matched edges. Main value: learning whether
the global ceiling we hit is truly an ALNS-side problem or a
CP-side one.

### Priority 3 (ENGINE HYGIENE)
- CSP-aware frame enumerator per `V15_FRAME_ENUMERATOR_SPEC.md`
  (3-5 days; replaces vol-12's pairwise-only catalog).
- ALNS `pinned_positions` bug fix (already in vol-14 — verify
  it didn't regress).
- ALNS adaptive-k destroy operator sized to connected
  mismatch components (1 day).
- PT tabu list (LRU over board fingerprints) per
  `project_e2_vol14_pt_no_tabu.md` (1-2 days).

### Priority 4 (LONGER-TERM)
- Lightweight no-good cache in `solver-engine` (LRU over the
  last K dead-end position prefixes). 3-5 days. Lets the
  HintRectangle / HintRectangleLayered features actually pay off
  at long budgets.
- McGavin-style fit_table for raw throughput (~1-2 weeks of
  engineering).

## Validation protocol (use the 12×12/12 testbed)

12x12 / 12-color generated puzzles are the vol-15 testbed (per
`project_e2_vol14_12x12_testbed.md`). They exhibit the same
plateau dynamics as canonical E2 with 7× faster turnaround.

Baseline to beat:
- 8 seeds × (30s CP + 60s ALNS) parallel = 90s wall-clock.
- Median ALNS-final: 247/264 (93.6%). None solved.

If a vol-15 algorithm gets ≥ 255/264 on the majority of 12×12/12
seeds, scale up to canonical E2. Otherwise re-tune.

## Honest expected outcomes for vol-15

- **Tier 1** (improve over vol-14): implement Blackwood
  correctly, hit 460+/480 on canonical E2 end-to-end. **Hard but
  achievable.**
- **Tier 2** (catch up to community): hit 469/480. Requires
  Blackwood + significant tuning. **Plausible in 2-3 weeks.**
- **Tier 3** (surpass community): hit 470+/480 on canonical
  5-clue. **Possible** but uncharted — no community board exists.
  Would be a real result.
- **Tier 4** (solve E2): 480/480. Out of scope of any reasonable
  vol-15 effort; would need throughput engineering at
  McGavin scale (~weeks separately).

## Operating rules

- Vol-15 is read-only on vol-14's commits and output files. Use
  new directories: `output/v15_*`, `crates/solver-blackwood/`,
  etc.
- Use 12×12/12 as the testbed before canonical E2.
- Add **end-to-end metric scoring** (matched/480) to every new
  bin from the start — don't replicate vol-12's CP-partial-score
  trap.
- All commits to `develop` with `Co-Authored-By: Claude Opus 4.7
  (1M context) <noreply@anthropic.com>`.

## How to start vol-15

1. Read this doc + the three memory entries cited at top.
2. Pick Priority 1 (Blackwood) OR Priority 2 (sub-CSP). Both are
   defensible vol-15 anchors.
3. Set up `crates/solver-blackwood/` mirroring
   `crates/solver-verhaard/` if Priority 1.
4. Write tests on 12×12/12 BEFORE running on canonical E2.
