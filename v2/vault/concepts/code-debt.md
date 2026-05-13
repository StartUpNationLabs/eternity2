# Code restructure proposal (vol-25 audit, 2026-05-13)

**Status**: `unbuilt` — audit complete, no extractions shipped.
**Origin**: vol-25 (2026-05-13), user-requested code-quality audit at session open.
**Files audited**: all of `v2/crates/`, `v2/server/`, `v2/wire/`, `v2/wasm/` (18 crates, 76 bins, ~19K lines of bin code).

## Definition

A prioritized refactor plan for the v2 Rust workspace, surfacing god files, duplicate utilities, and modularity smells. The audit was triggered by the recurring symptom of every new bin reinventing the same plumbing (Bucas URL, scoring, board serialization, hint loading), and the `solver-engine` crate growing into a 5 011-line monolith.

## What we measured

| Item | Finding |
|---|---|
| `solver-engine/src/lib.rs` | **5 011 lines** — search algorithm + 22 EngineConfig profiles + 7 Blackwood schedule builders + parallel harness + ~25 hint/edge utilities, all in one file. |
| `localsearch/src/alns.rs` | 2 013 lines — operators + repairers + portfolio runner. |
| `localsearch/src/lib.rs` | 1 619 lines — SA core + State + Houdayer + ALNS support. Already has internal sub-files; acceptable. |
| `bench-audit/src/bin/` + `benchmark/src/bin/` | **76 bins**, ~19K lines, with ~250 lines of boilerplate per bin. `alns_only.rs` and `alns_portfolio.rs` share identical `build_ops()`. |
| `bench-audit` dependencies | 9 sibling crates |
| `benchmark` dependencies | 11 sibling crates — pulls in nearly every solver. |

## Five duplicated utilities (the core of the debt)

### 1. Clock implementations — byte-identical

- `crates/solver-engine/src/clock.rs` (25 lines)
- `crates/solver-naive/src/clock.rs` (31 lines)

Same `Clock` struct (`now()`, `elapsed_us()`), differing only by one comment. CLAUDE.md predicts: every new solver crate needs the same wasm32 shim.

**Target home**: new `eternity2-time` crate, or `eternity2-core::time` module.

### 2. Board scoring / edge matching — two implementations, neither shared

- `crates/bench-audit/src/lib.rs:112–142` — `score_board(puzzle, board) -> (matched, total)`
- `crates/benchmark/src/report.rs:60–94` — `score_matched_edges(puzzle, board) -> (matched, total)`
- `crates/benchmark/src/report.rs:123–124` — inline scoring inside `write_report()`

Two independent edge-count implementations with slightly different defensive postures (bench-audit's eagerly `unwrap()`s placed cells; report.rs uses `let Some(...)` checks).

**Target home**: new `eternity2-export` crate.

### 3. Bucas URL encoding — not exported

- `crates/benchmark/src/report.rs:16–58` — `color_to_bucas`, `board_to_bucas_edges`, `bucas_url`.

Buried in `benchmark::report`; not re-exported. Bins can't generate a Bucas URL without pulling the whole report module.

**Target home**: `eternity2-export::bucas`.

### 4. Board serialization — two incompatible formats

- `crates/benchmark/src/board_io.rs` (67 lines) — `DumpedBoard` JSON with metadata.
- `crates/bench-audit/src/lib.rs:180–193` — `render_board(puzzle, board) -> String` (ASCII).

No interchange between them.

**Target home**: `eternity2-export::board_io` + `eternity2-export::render`.

### 5. Hint loading — only in benchmark

- `crates/benchmark/src/loader.rs` (140+ lines) — `load_puzzle()`, `load_puzzle_with_hints()`.

Hints are a canonical E2 concept (the 5 clue pieces) but loading lives in a "benchmark" crate. Invisible to solvers from naming.

**Target home**: `eternity2-puzzle-io` crate (with CSV parsing + hint decoding).

## The proposed restructure

### Phase 1 — extract duplicate utilities (~1 day)

```
crates/
├── time/              NEW   ~25 lines        (clock shim)
├── export/            NEW   ~600 lines       (bucas + scoring + board_io + report)
├── puzzle-io/         NEW   ~150 lines       (CSV + hints + canonical bootstrap)
└── (existing crates updated to import from these)
```

Order: time → export → puzzle-io (puzzle-io depends on export for report writing). Each ships independently; downstream bins adjust imports.

### Phase 2 — split solver-engine into 5 modules within one crate (~4 hours)

Verdict from the in-session deep dive: 3-way split is too coarse, 5-way is right, multi-crate is overkill.

```
crates/solver-engine/src/
├── lib.rs              ~3 200 lines  SearchState + recurse + propagate_ac3 + tests
├── config.rs           ~200 lines    VariableOrder, ValueOrder, ScanOrder, Parallelism, PropagatorConfig, EngineConfig + 22 profiles
├── profiles.rs         ~350 lines    EngineSolver + 40+ factory methods
├── schedule_builders.rs ~410 lines   7 Blackwood schedule builders + helpers
├── paths.rs            ~330 lines    compute_chess_rank, build_hint_rectangle_path, *_layered_path, *_x_skeleton_path
└── parallel/, clock.rs (existing, unchanged)
```

**Implementation order** (lowest-risk first):
1. `paths.rs` — pure geometry, zero backlinks to SearchState. **Ship first.**
2. `config.rs` — pure enums + struct defs.
3. `schedule_builders.rs` — pure factories.
4. `profiles.rs` — mechanical, mirrors profiles table.
5. `lib.rs` is what's left.

**Anti-splits** (DO NOT touch):
- `SearchState` mega-struct (40 fields, cache-aligned, accessed every node).
- `BlackwoodSchedule` struct itself (woven into `recurse` at 4 distinct call sites).
- Value-ordering dispatch inside `recurse` (lines 3847–4013) — extracting helps clarity but adds fn-call overhead in a hot path.

### Phase 3 — bin harness consolidation (~8–10 hours)

76 bins share ~250 lines of boilerplate each (CLI parsing, puzzle load, ProgressSink, solver instantiation, report writing). After Phase 1 (export crate exists), all bins can shrink to ~80–120 lines:

```
crates/bin-common/src/         (or benchmark::bin_harness module)
├── cli.rs           common args: puzzle, seed, budget
├── runner.rs        load + instantiate + run + report
└── solver_registry.rs  encapsulate the 11-solver fan-out so bins don't need to import each solver directly
```

Net: ~7K lines of copy-paste eliminated.

## Priority order (the ship list)

1. **Extract `eternity2-time`** — 1 h, trivial.
2. **Extract `eternity2-export`** — 4–6 h, 5 dedups in one crate.
3. **5-way split of `solver-engine/lib.rs`** — 4 h, all sequential, each independently shippable.
4. **Extract `eternity2-puzzle-io`** — 3–4 h.
5. **`bin-common` harness** — 8–10 h.

Total: ~25 h spread across ~5 sessions. None of this changes algorithm or correctness; it's pure organization.

## Why this matters

The duplicate-utility problem isn't aesthetic. Right now:
- Adding a new solver bin requires re-implementing scoring + Bucas + report.
- A bug in any of the 5 duplicate utilities can only be fixed in N places.
- Cross-crate deps form a "every bin imports every solver" mesh that breaks on any sat-encoder API change.

The phase-1 extractions (time + export) are the highest-leverage because they remove 80% of the friction for the other 4 phases.

## Linked concepts

- [[engine-perf-hot-paths]] — the perf push that surfaced the file size issue
- [[engine-profile-registry]] — the 22-profile table that should move to `profiles.rs`

## Linked memory

- [[../../../../.claude/projects/-Users-raphaelanjou-Documents-dev-projects-polytech-eternity2/memory/project_e2_vol16_closeout|Vol-16 cleanup anchor]] — prior cleanup vol that handled algorithmic debt but not these structural issues.
