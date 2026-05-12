# RESEARCH_NOTES_15.md — vol-15 session log

**Opened**: 2026-05-12, ~18:20 CEST (verified via `date`).
**Status**: open.
**Reads completed at start**:

- `MEMORY.md` (full index).
- `project_e2_vol14_session_summary.md` — vol-14 one-pager.
- `project_e2_vol14_rectangle_path_findings.md` — the user's
  "fail-fast around hints" insight that frames vol-15's
  priorities.
- `project_e2_vol14_alns_hint_bug.md` — the critical bug whose
  fix invalidates pre-fix vol-12/vol-14 scores; baselines must
  be re-derived on the patched binary.
- `project_e2_mcgavin_blackwood_gap_analysis.md` — what our
  stack is missing to reach 469.
- `RESEARCH_NOTES_15_PLAN.md` — the priority list.
- `V15_BLACKWOOD_SPEC.md` — full implementation spec for #1.
- `V15_FRAME_ENUMERATOR_SPEC.md` — implementation spec for #3.
- `project_e2_vol12_engine_profiles.md` — current engine
  registry the new code has to extend.

## Calibration anchor (vol-14 closeout)

| metric                                          | score |
|-------------------------------------------------|------:|
| baseline `joe_depth150_par` + ALNS-fill         | 442/480 (broken-binary; ~440 on fixed) |
| BP-seeded baseline + ALNS-fill                  | 443/480 (broken-binary; ~440 on fixed) |
| vol-6 PT-from-453 (PT had correct pinning)      | 454/480 |
| community SOTA (McGavin 2020)                   | 469/480 |

**Vol-14 honest cold-start best ≈ 440/480**, NOT 443 as previously
reported. Re-run with patched `alns_e2` is the prereq for any
fair vol-15 A/B.

## Vol-15 anchor commitment

**Priority 1 — Blackwood algorithm**. This is the only deliverable
in the priority list that has a path past the "without Blackwood
ceiling" of 446–454. Plus 1.5 (Blackwood × HintRectangle
composition) as a 4-hour follow-up once #1 lands.

Why this and not Priority 2 (hint-cluster sub-CSP enumeration):
sub-CSP enumeration is cheap and gives 0–15 matched-edge gain
without learning. Blackwood encodes the compile-time
"fail-fast against a global schedule" mechanism that the user's
vol-14 hint-rectangle hypothesis pointed at. McGavin/Blackwood
gap-analysis: until at least #1+#2+#3 (heuristic schedule +
break-index + in-place restart) ship, our ceiling stays at
446–454. Vol-15 must close the schedule gap first.

## Plan (in order)

1. Validate baseline. Re-run `joe_depth150_bp_par` + patched
   `alns_e2` once to get a fresh honest cold-start baseline on
   the fixed binary. Recorded as the vol-15 scoreboard reference.
   Pipelined alongside Blackwood implementation work.
2. Implement Blackwood per `V15_BLACKWOOD_SPEC.md` tasks
   B.1 → B.6 in `crates/solver-engine` (keep it on develop;
   don't create a separate crate — the spec actually says
   solver-engine extensions; vol-15 plan says
   `crates/solver-blackwood/` mirroring solver-verhaard would
   be acceptable; the engine-extension path is cheaper and the
   schedule lives naturally inside `EngineConfig`).
3. Unit-test the new pieces on synthetic small puzzles.
4. Validate on 12×12/12 testbed (8 seeds × 90s) before scaling.
   Beat baseline 247/264 with majority ≥ 255/264 ⇒ scale.
5. Canonical E2 pilot at 500M-iter scale.
6. Closeout block with Tier ranking and vol-16 recs.

## Bars

- Tier 1: ≥454/480 standalone Blackwood ⇒ catches up to vol-6.
- Tier 2: ≥469/480 ⇒ ties community SOTA.
- Tier 3: ≥470/480 ⇒ clears community SOTA.
- Tier 4: 480/480 ⇒ out of scope without McGavin throughput.

## Live log

(appended below as session progresses)

---

### 2026-05-12 ~18:30 — Blackwood injection-point design

Audit of `crates/solver-engine/src/lib.rs`:

- `EngineConfig` is currently `Copy`. Adding `BlackwoodSchedule`
  with Vec fields forces a downgrade to `Clone`. The struct is
  referenced through `SearchState::config` (a copy) — replacing
  Copy with Clone is a one-line change. Cheap.
- `SearchState::place_and_propagate` does NOT verify edge-color
  matching against already-PLACED neighbors at the prune call;
  it relies on the symmetric prune installed when the earlier
  neighbor was placed (which removed any row from this cell's
  domain that wouldn't match). I.e., the engine maintains
  "domain only contains color-consistent rows" as an invariant.
- Consequence: **allowing 1 mismatch at a break depth requires
  expanding the candidate set beyond the current pruned domain**.
  The cleanest approach: at break depths, iterate over all
  rows-for-this-cell-class (matching border_mask) and admit those
  with ≤ 1 placed-neighbor edge mismatch AND piece-uniqueness.
  This is O(n_rows × 4) at break depths (12 of 256 cells) — fine.
- Once a row is placed with a mismatched edge, the **propagation
  to unplaced neighbors must skip the mismatched side**, else
  we'd wipe out a domain that's perfectly valid given the break.
  The `prune` closure in `place_and_propagate` needs to take a
  `mismatch_at_side: Option<usize>` parameter and short-circuit
  on that side.

### Decisions

1. `ScanOrder` ⇒ model as a new `path_skeleton` variant
   `PathSkeleton::BlackwoodScanOrder(ScanOrder)` that builds a
   full `path_order` of `n_pos` cells (full prefix-constraint).
   This is the cheapest insertion — reuses the
   `auto_skeleton_path_k` machinery already in `select_position`.
   Alternative considered: a new orthogonal `EngineConfig::scan_order`
   field. Rejected because `select_position` would need a
   third branch when no path is set — more code paths than
   benefit.

2. `BlackwoodSchedule` ⇒ new `pub struct` in lib.rs (small;
   keep it next to `PathSkeleton`). Added to `EngineConfig` as
   `pub blackwood_schedule: Option<BlackwoodSchedule>`. Drops
   `Copy` on `EngineConfig`; impl `Clone` instead. All
   downstream sites that take `EngineConfig` by value need
   to clone (small fan-out — verified in code).

3. `ValueOrder::BlackwoodHeuristic` ⇒ new enum variant. Score
   each candidate row by `Σ side count_heuristic_colors(row.edges[side])`
   descending, then sort. Independent of the schedule prune.

4. Schedule prune ⇒ at the top of `recurse()`, after select_position
   but before the value-order sort, count placed heuristic
   piece-occurrences and compare against piecewise-linear
   target at `depth`. Return `RecurseResult::Exhausted` if
   behind.

5. Break-index allowance ⇒ implemented in `recurse()` by
   *augmenting* `domain_snapshot` at break depths with rows
   admitting ≤ 1 placed-neighbor mismatch. Then plumb a
   per-row `mismatch_at_side: Option<usize>` into a new
   `place_and_propagate_with_break(side)` overload that skips
   propagation on that side.

This is the minimal feature surface for B.1–B.6. B.7 (parameter
search harness) is a separate bin in `crates/bench-audit/`.
B.8 (PT integration) is deferred.

### 2026-05-12 ~19:00 — user-flagged vol-16 anchor: code cleanup

User: *"I think session 16 will be focused on code clean up,
refactoring, deduplication etc.... our code is becoming quite a
mess"*

Endorsed. Capturing the specific debt that motivated the call,
so vol-16 has a concrete punch list rather than a vibes-based
"clean things up":

**Engine-config surface bloat (the most visible smell)**
- `EngineConfig` has 14 fields. Many are orthogonal in principle
  (variable_order × value_order × 5 propagator flags × depth gate ×
  parallelism × path_skeleton × scan_order × blackwood_schedule via
  EngineSolver builder).
- The const-profile table has 28+ named profiles built via FRU
  spreads; adding the Blackwood profiles required adding two more.
  The naming convention (`JOE_DEPTH150_BP_REC_LAYERED_PAR`) is a
  symptom of "feature flags multiplied together"; the profile
  table is approaching a combinatorial explosion.
- The proto registry comment + server::service::instantiate +
  list_solvers are three places that have to stay in sync.
  Already drifted (vol-15's `BLACKWOOD_BASE*` profiles aren't in
  the proto comment yet — TODO for vol-16's first commit).
- **Refactor target**: split `EngineConfig` into orthogonal
  sub-configs (`VarOrderConfig`, `ValueOrderConfig`, `PropConfig`,
  `PathConfig`, `BlackwoodConfig`), each with its own default,
  composed via a builder. Profile constants become builder
  combinations, named only when actually published.

**Bench-audit / benchmark crate sprawl**
- `crates/bench-audit/src/bin/` has 20+ harness binaries, many
  near-duplicates (`run_e2_5min`, `run_e2_5min_bp_ab`,
  `run_e2_rectangle_full_pipeline`, `run_e2_rectangle_path`,
  `run_e2_layered_pipeline`, vol-15's `run_e2_blackwood`,
  vol-15's `run_blackwood_12x12`...). Each duplicates ~80 lines
  of `score_board` + `placed_count` + `write_board_json` + CLI
  parsing.
- **Refactor target**: shared library module `bench_audit::pipeline`
  with `Pipeline::cp(...).alns(...).run(out_dir)`; thin bins call
  it. Aim: each new harness < 60 lines.

**Memory + research-notes accretion**
- `~/.claude/.../memory/MEMORY.md` is at 34 entries. Several
  pairs are duplicates with different framings
  (`project_e2_vol14_443_mismatch_geometry` +
  `project_e2_vol14_mismatch_geometry_universal`;
  `project_e2_vol14_scan_order_analysis` +
  `project_e2_vol14_hint_centric_null`). Some entries are stale
  (e.g., the rare-color geography numbers measured on canonical
  E2 are correct but the project_e2_vol14_framefirst_null entry
  references a lower-bound that's been corrected elsewhere —
  cross-references will rot fast).
- **Refactor target**: merge near-duplicates; promote a
  `project_e2_calibration` entry that's the single source of
  truth for "what score does what stack reach"; collapse vol-14
  five-finding entries into one rollup pointer.

**Dead code in solver-engine**
- `PruneResult::Removed(UndoEntry, u32)` and `PruneResult::Wipeout
  { entry, popcount: u32 }` — the popcount field is unused
  (compiler warned both times). Either remove or wire to a
  counter.
- `cell_class_matches` in `localsearch/src/lib.rs:143` flagged
  dead.
- Vol-14's `pos_backtracks` instrumentation was added for one
  measurement and is still in the hot path; if it has paid back
  the cost, document it; if not, gate behind a feature flag.
- **Refactor target**: one `cargo +nightly clippy --workspace
  -- -W clippy::all` pass; fix or `#[allow]` with reason.

**Backward-compat shims that are no longer needed**
- `EngineConfig` is `Copy + Clone + PartialEq + Eq`. The Eq isn't
  actually used anywhere — derive it removed.
- The `place_and_propagate` thin wrapper now calls
  `place_and_propagate_opts(None)`. Once vol-16 audits callers,
  either inline the wrapper or rename to make the relationship
  obvious.

**Tests that should be folded together**
- 5 `solves_*` integration-style tests in solver-engine that all
  exercise generator + solve roundtrip. Could be one parameterised
  test.
- `blackwood_solve_tiny_puzzle_still_finds_solution` and
  `blackwood_break_index_allows_one_mismatch_on_small_puzzle` test
  the same 2×2 puzzle with different schedules; could be a single
  table-driven test.

**Vol-15-specific cleanup vol-16 should do**
- Add the new Blackwood profiles to `proto/solver/v2/solver.proto`
  comment block + `server::service::instantiate` +
  `server::service::list_solvers`.
- Document `compute_heuristic_sides` + `blackwood_schedule_469`
  in `V2_DESIGN.md` (currently only in `V15_BLACKWOOD_SPEC.md`,
  which is a living spec, not a stable contract).
- If vol-15's canonical-E2 run lands Blackwood as a winner,
  promote to `joe_depth150_bp_blackwood_par` and retire the
  experimental name.

**Out of scope for vol-16 (but worth flagging)**
- The localsearch crate has its own register of duplicated score-
  computation logic across alns_e2 / pt_e2 / the bench-audit
  bins. Worth a parallel cleanup pass.
- `frontend/dist/assets/index-*.js` — generated artifacts
  showing up in git status. Should be .gitignored.

