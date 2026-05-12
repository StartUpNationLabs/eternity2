# Eternity II v2 — Design Document

This document captures the v2 rewrite plan, derived from a deep audit of the
current codebase (solver, frontend, API, infra, benchmarks, heuristics,
PathManager, generators). It is a working document, not a contract.

## Goals

- Rewrite the solver core in Rust as a **portfolio of strategies**, easy to
  extend with new algorithms.
- Rebuild the frontend with modern components, splitting into **Educational**
  (kids/students learn the puzzle, algorithms, complexity) and **Research**
  (researchers study problem complexity, hard vs easy positions, heuristic
  behavior) modes.
- Ship to Terra Numerica with a **one-command deploy**, fewer moving parts than
  today's CMake+vcpkg+Nix+Makefile+Envoy+4-compose-files setup.
- Preserve everything that currently works: the SVG board renderer, the four
  pages of UX (Home, DIY, Solver, Stats, PathManager), the benchmark corpus,
  the proto telemetry shape (extended, not replaced).
- Add what's missing: real reproducibility (seeds), a typed event stream from
  solver to UI, cancellation, parity/island propagators (Gemini gaps).

## Non-goals

- Not a new algorithm. v3's DLX-with-edge-propagation is the canonical target.
  v0/v1/v2 stay as comparators.
- Not Kubernetes. Compose is the deployment target.
- Not GraphQL or a database. Solver runs are stateless; persistence is
  per-run JSON files.
- Not a microservices split. Monolith is correctly sized.

---

## Findings summary (from the audit)

### Performance picture (from `data/partial_results/results_v3.csv`)

| Puzzle class | V3-Parallel (DLX) | V2-Par-BorderFirst (CSP) | Verdict |
|---|---|---|---|
| 2×2 – 4×4 | 0.2–1.2 ms | 1.2–2.0 ms | V3, 2–6× |
| 5×5 – 6×6 | 0.9–6.9 ms | 2.6–85 ms | V3, 5–50× |
| 7×7 (low color) | 1.5–35 ms | 6–3792 ms | V3, ~100× |
| 7×7 colors=6 | timeout (5+ hr) | timeout (1+ hr) | both wall |
| 8×8 – 9×9 (low color) | 18–6960 ms | 43–9710 ms | V3 slightly |
| 8×8 – 9×9 (colors ≥6) | timeout | timeout | both wall |

V3 solves 55/60, V2 solves 46/52. No puzzle class where V2 wins. V3 is the
canonical default for v2.

Both wall at size ≥7, colors ≥6. That's the actual research frontier and
neither algorithm solves it. Benchmarks have no seeds, no warm-up, no
statistical rigor — directional only.

### Heuristic profiles — consolidation

12+ profile names today across v2 and v3, with duplicates and dead branches.

**Original plan** kept 6+1 distinct strategies across three solver families
(naive, csp, dlx). **Implementation revealed** that the legacy V2 (CSP)
and V3 (DLX) families converged into a single backtracker once written
in Rust: both used domain-pruning + edge-color propagation, and the
performance gap the audit measured lived entirely in propagation, not in
search strategy. The CSP family was kept in the original plan as the
home for AC-3 / parity / island propagators — but those become *new
propagator configs under the unified engine* rather than a new family.

**Final registry (2 solver_ids × 7 profiles):**

| # | (solver_id, profile) | Propagators | Why keep |
|---|---|---|---|
| 1 | (naive, row_by_row) | none | Educational baseline — no propagation, row-major DFS. |
| 2 | (naive, spiral) | none | Pedagogical contrast: same dumb DFS, different order. |
| 3 | (engine, border_first_lcv) | edge_color + piece_unique + class_balance | Research default. |
| 4 | (engine, rare_color_first) | edge_color + piece_unique + class_balance | Different variable-ordering regime. |
| 5 | (engine, border_first_random) | edge_color + piece_unique + class_balance | Portfolio diversification, seeded. |
| 6 | (engine, border_first_parity) | …​ + parity | Step 8: checkerboard parity propagator. |
| 7 | (engine, border_first_full) | …​ + parity + island | Step 8: all available propagators. |

**Drops vs original plan:**
- `s_heuristic_lcv` — with propagation active, pure MRV picks corners
  anyway (smallest domains). Silently identical to `border_first_lcv`.
- `csp / border_first` — was a placeholder for AC-3/parity hosting; with
  the engine unified, those configurations become new `engine/*` profiles.

**Step 8 additions** ship as new `engine/*` profiles (`border_first_parity`,
`border_first_full`, etc.) once parity/island/AC-3 propagators land.
The proto/wire/portfolio code does not change.

### Propagator landscape (post-Step 8)

Implemented:
- **edge_color** (always on) — neighbor edge matching after each placement
- **piece_unique** (always on) — each piece used once
- **class_balance** (default on for `engine/*`) — corner/edge/inner counts
  must match between unplaced positions and unplaced pieces. Cheap, often
  pruning. Caught a class of wrong placements early in development.
- **island** (opt-in) — every unplaced piece must have a remaining home
  somewhere. Measured ~3% node reduction on a 5-seed 6×6 sample.
- **parity** (opt-in) — checkerboard color-balance. Currently weakly
  pruning (~0% on the same sample). The check is correct but enforces
  only end-state feasibility; the strong incremental "per-side per-color
  budget" formulation from the EII literature is v2.1 work.

Not yet implemented:
- **AC-3** — full arc consistency. Strictly stronger than the
  edge-color check we already do on placement; useful only when the
  puzzle is hard enough that the extra work pays off. Wire is ready.

Lesson learned: a propagator is "v1" the moment the integration point
exists and the algorithm is correct. Tuning its pruning strength is
ongoing work that doesn't change the engine API.

Drop: `MRV_ONLY_LCV`, `STATIC_LCV`, `STATIC_RANDOM`, `DEGREE_ONLY` (never
wired), `CORNER_HEAVY` (silently identical to BORDER_FIRST_LCV),
`REVERSE_LCV` (silently identical to RARE_COLOR_FIRST), `order_values_none`,
the commented-out rare-color bonus.

### Missing strategies (Gemini gaps)

- **Parity/checkerboard constraint propagation** — Gemini estimated ~10⁹×
  pruning. Zero implementations today. Highest-leverage missing piece.
- **Island/connectivity detection** — unreachable-region prune, real wins on
  size ≥7.
- **Edge-color frequency dynamic histogram** — v2 sketched it then disabled
  citing overhead. In Rust with cheap incremental updates it should be free.

### PathManager — broken backend contract, salvageable concept

- v1 consumes `solvePath`. v2 and v3 ignore it. Frontend sends it to all.
- Hints saved in PathManager are never sent to the solver. Dead feature.
- Not persisted across page reloads.

The concept ("design an ordering, see what happens") is sound. What changes is
*what the ordering means* to each solver. See the PathPolicy section below.

### Generators — two of them, one bug

- `generate_puzzles.js` (Node, root) — CLI flags, all-combos, ensures every
  color appears at least once.
- `frontend/.../logic.tsx` — used in DIY and Statistics. Does NOT guarantee
  color coverage. Pure random.
- Neither has seed control. No benchmark on the books is reproducible.

v2: one canonical Rust generator, compiles to native + WASM, seeded,
color-coverage-correct.

### Infra — collapse three layers into one

- Today: CMake + vcpkg + Nix + Makefile + 4 compose files + Envoy.
- v2: Cargo + Docker + 1 compose file. Drop Envoy in favor of `tonic-web`.
  Drop Nix (or keep flake.lock for dev shells, optional).

### Frontend — pick a stack, commit

- Today: MUI + Tailwind + shadcn (only one shadcn component used). Recoil
  (maintenance mode). No tests. No error boundaries. No persistence.
- v2: Tailwind v4 + shadcn/ui (full commit). Zustand for client state,
  TanStack Query for server interactions. Vitest + Playwright. Persist
  preferences to localStorage.

---

## Architecture

### Solver portfolio — the trait

```rust
pub trait Solver: Send {
    fn id(&self) -> SolverId;
    fn supports_path_policy(&self, p: &PathPolicy) -> bool;
    fn solve(
        &mut self,
        puzzle: &Puzzle,
        opts: SolveOpts,
        sink: &mut dyn EventSink,
    ) -> SolveOutcome;
}
```

Design points:

- `SolverId` is data (enum or string), not a generic type parameter. Lets the
  portfolio name solvers in config and event streams without infecting every
  call site with generics.
- `supports_path_policy` lets the UI gray out incompatible combos *before*
  the user clicks solve. No more silent ignored paths.
- `&mut dyn EventSink` keeps zero-cost when nothing is listening
  (`NullSink` monomorphizes to nops) and JSON-streamable when on the wire.
  Same solver code path for benchmark, test, and production.
- `SolveOutcome` is `{ Solved(Board) | Exhausted | TimedOut | Cancelled |
  Error }` — typed, not a status code.
- `Send` because the portfolio runs them on rayon threads. Not `Sync` — each
  solver owns its state.

### PathPolicy — path semantics per solver

The user's path is interpreted differently depending on the solver and the
selected mode:

```rust
pub enum PathPolicy {
    Strict,                  // walk the path cell by cell (v1 / educational)
    OrderingPrior,           // path is MRV tie-breaker (v2/v3 / research)
    PrefixConstraint(u32),   // first K cells forced before heuristic takes over
    Ignored,
}
```

Support matrix:

| Solver | Strict | OrderingPrior | PrefixConstraint | Ignored |
|---|---|---|---|---|
| v1 naive | ✅ | ❌ | ❌ | ✅ |
| v2 CSP | ❌ | ✅ | ✅ | ✅ |
| v3 DLX (3 variants) | ❌ | ✅ | ✅ | ✅ |

Hints are sent alongside the path via the same request envelope and honored
by all solvers regardless of policy.

### Event stream — the wire contract

```rust
pub enum SolverEvent {
    Started { solver_id, puzzle_hash, config, seed },
    VariableSelected { depth, position, domain_size, score, reason },
    ValueTried { depth, position, piece_id, rotation },
    ConstraintPropagated { from_pos, to_pos, removed_count },
    DomainWipeout { position },
    Backtrack { from_depth, to_depth, cause },
    PartialSolution { snapshot_id, board_delta },   // throttled, deltas only
    Stats { time_ms, nodes, backtracks, ... },      // throttled
    Solved { board_state, time_ms, final_stats },
    Exhausted,
    TimedOut,
    Cancelled,
}
```

Every event has: `node_id`, `depth`, `timestamp_us`, `schema_version`.

Design points:

- **Throttled, not raw.** Solver may explore 10M nodes/sec. The sink decides
  what's emitted: full trace at depth ≤ N, every K nodes thereafter, plus
  all backtracks above some threshold. The solver tags every event; the sink
  filters.
- **Position-delta `PartialSolution`s, not full boards.** Sparse "since last
  snapshot" deltas avoid bandwidth blow-up.
- **`node_id` and `depth` everywhere.** Lets the UI rebuild a search tree,
  scrub timeline, replay.
- **`schema_version: 1` from day one.** Future-proofs persisted research
  data.

### Proto — minimal RPC surface

```proto
service SolverService {
  rpc Solve(SolveRequest) returns (stream SolverEvent);
  rpc Cancel(CancelRequest) returns (CancelResponse);
  rpc ListSolvers(ListRequest) returns (ListResponse);
  rpc Health(google.protobuf.Empty) returns (HealthResponse);
}
```

- `Cancel` is a real RPC, not just stream-close. Currently cancellation is
  broken.
- `ListSolvers` lets the frontend discover the portfolio at runtime. No
  hardcoded enum on both sides drifting apart.
- `Solve` returns a stream of `SolverEvent` (the union above).

### Repo layout

```
eternity2/
├─ Cargo.toml                    # workspace root
├─ crates/
│  ├─ core/                      # Puzzle, Piece, Board, PathPolicy, Hints
│  │                              # no I/O, no async, wasm-clean
│  ├─ generator/                 # the ONE canonical generator
│  │                              # seeded, color-coverage correct
│  │                              # builds native + wasm32
│  ├─ events/                    # SolverEvent + EventSink trait
│  │                              # NullSink, BufferSink, JsonSink
│  ├─ solver-trait/              # Solver trait + PortfolioRunner
│  ├─ solver-naive/              # v1 port: strict path + spiral default
│  ├─ solver-csp/                # v2 port: MAC + MRV/LCV + BorderFirst
│  ├─ solver-dlx/                # v3 port: DLX + edge propagation
│  │                              # 3 keep-worthy heuristic profiles
│  ├─ solver-portfolio/          # parallel runner
│  ├─ propagators/               # parity, island, color frequency
│  ├─ wire/                      # proto-generated types + conversions
│  └─ benchmark/                 # seeded, JSON output, baseline diff
├─ server/                       # tonic + tonic-web binary
│  └─ src/main.rs                # no Envoy
├─ wasm/                         # wasm-bindgen wrapper
│  └─ src/lib.rs                 # exposes generator + solver-naive to JS
│                                  # educational mode only
├─ frontend/
│  └─ src/
│     ├─ lib/                    # Board.svg, Piece.svg, useSolveStream,
│     │                          # generator wasm binding
│     ├─ educational/            # tutorial, DIY, path play (WASM)
│     ├─ research/               # portfolio runner, heuristic inspector,
│     │                          # path lab, sweep mode
│     └─ shared/                 # PathManager component (used by both)
├─ proto/
│  └─ solver/v2/solver.proto     # versioned alongside the schema
├─ data/                         # unchanged location
└─ deploy/
   ├─ docker-compose.yaml        # 2 services: server, frontend
   ├─ Dockerfile.server
   ├─ Dockerfile.frontend
   └─ traefik-example.yaml       # the worked example DEPLOYMENT.md lacks
```

Constraints:

- `core` has zero deps beyond std (and optionally serde). It must compile to
  WASM cleanly. The moment `core` pulls in tokio or rayon, the WASM build
  dies.
- Each solver is its own crate. New solver = new crate, register in portfolio.
- `propagators` is shared across solvers — parity, island, color histograms.
- `wire` is generated from proto; the proto is the source of truth.

### WASM scope (educational only)

The `wasm` crate exposes:

- `generator` — seeded puzzle generation in-browser
- `solver-naive` — strict-path DFS with event stream

That's it. No DLX, no CSP. Educational mode runs <6×6 puzzles in-browser with
zero server roundtrip. Research mode hits the server.

**Why ship WASM at all when the server also has naive?** The educational loop
is "kid clicks 'play my path,' answer arrives instantly, no network." That's
latency + offline-ability, not raw speed. Multiply by a classroom on flaky
wifi (Terra Numerica's actual use case) and the local execution matters.

If WASM ergonomics get painful, retreat is easy: drop the `wasm` crate, point
educational mode at the server. You lose offline capability and nothing else.

### Educational vs Research — same app, two route trees

Shared:

- `Board.svg` + `Piece.svg` primitives
- `useSolveStream` hook (consumes `SolverEvent`)
- `PathManager` component (different mode prop)
- Generator (WASM)

Educational (`/edu`):

- Tutorial: interactive intro to pieces, edges, matching
- DIY puzzle (manual solving, keep current UX)
- Path Play: draw a path → WASM naive solver → animated playback. Zero
  server.
- "Watch a tiny puzzle solve" — 3×3 to 5×5 in WASM end to end
- Glossary with hover-defined inline links

Research (`/research`):

- Portfolio runner: pick puzzle + solvers + heuristics, run in parallel,
  compare event streams side-by-side
- Heuristic inspector: drill into one solver's decisions, domain heatmaps
- Path Lab: PathManager in `OrderingPrior` or `PrefixConstraint` mode
- Sweep mode: corpus generation (size × color × seed), portfolio runs,
  statistical view
- Export: download event traces as JSON / Parquet for offline notebook
  analysis

### State management

- **Zustand** for client state (board, in-flight solve, settings, with
  `persist` middleware for user preferences)
- **TanStack Query** for server interactions (puzzle list, solver list, sweep
  results, streaming + cancellation + retry)

Drop Recoil entirely.

### UI library

Tailwind v4 + shadcn/ui, full commit. Remove MUI and the half-installed
shadcn. The current three-way mix is the worst of all worlds.

### Benchmarking

The new `benchmark` crate fixes audit gaps:

- Seed control on every run (reproducibility)
- JSON output (not CSV) preserving typed event structure
- Multiple runs per (puzzle, solver, seed) with mean + variance
- Baseline diff: `benchmark/baseline.json` committed, CI fails on >X%
  regression
- Per-heuristic breakdown for portfolio runs
- Warm-up runs

The canonical suite stays in `data/benchmark/` — those 56 puzzles are real.

### Infra & deploy

- 2 Dockerfiles (server, frontend), 2 compose services, no Envoy
- Optional Makefile as convenience wrapper
- Optional Nix flake with committed `flake.lock` for dev shells
- CI: one workflow — `cargo test`, `cargo clippy`, `wasm-pack test`,
  frontend tests, build + push both images. Replaces four current parallel
  workflows.

Terra Numerica deploy: `docker compose -f deploy/docker-compose.yaml up -d`.
The Traefik example becomes a real file in `deploy/traefik-example.yaml`
instead of a missing reference in a README.

---

## Migration sequence

No big-bang. Each step is independently shippable; pausing between any two
leaves a coherent state.

1. **Proto first.** Design and freeze v2 proto. Generate Rust + TS stubs.
   This is the contract everything else builds against.
2. **`core` + `generator` in Rust.** Port the data model and the seeded
   generator. Test against current CSV format.
3. **`solver-naive` (v1 port).** Smallest solver, validates the trait shape
   and event sink end-to-end.
4. **WASM educational mode.** Wrap generator + naive, build educational
   frontend route. First user-visible v2 thing; proves WASM story works.
5. **`solver-dlx` (v3 port).** The canonical research solver. Wire to the
   new server.
6. **Portfolio runner + research frontend.** Built on the proven event
   stream.
7. **`solver-csp` (v2 port).** The slow one — comparator, doesn't block
   anything.
8. **Propagators** (parity, island). New work, ships after the structural
   migration.

---

## Strategy composition (vol-16)

### Why this section exists

After vol-15 the unified engine grew from 7 named profiles to 30+
combinations across five dimensions (variable order, value order,
propagator stack, scan order, Blackwood schedule). `EngineConfig`
became a 14-field struct with 25+ `EngineSolver::*` constructors,
each a thin wrapper around a `pub const` profile slab. Adding a
new dimension (vol-15 added scan_order + path_skeleton +
blackwood_schedule) now requires changes in ~6 files: the struct
definition, each named profile, each constructor, the proto
comment, `instantiate()`, `list_solvers()`, plus any harness that
wants the new dimension. The user flagged this in vol-15:
*"re-engineer the way we manage all those possibilities."*

The architectural decision below is **scoped to vol-16**. It does
not change the proto, the wire format, or the `Solver` trait
surface. It changes only the internal composition of
`EngineConfig` and how new strategies are added.

### Decision: trait + dyn dispatch (Option A)

Each axis is a trait. Concrete strategies are zero-sized or small
structs that implement the relevant trait. `EngineConfig` becomes
a bag of trait objects.

```rust
trait VariableSelector: Send + Sync {
    fn next(&self, state: &SearchState) -> Option<Position>;
}

trait ValueOrderer: Send + Sync {
    fn order(
        &self,
        state: &SearchState,
        pos: Position,
        candidates: &mut Vec<u32>,
    );
}

trait Propagator: Send + Sync {
    fn name(&self) -> &'static str;
    fn min_depth(&self) -> u32 { 0 }
    fn propagate(
        &self,
        ctx: &mut PropagatorContext<'_>,
    ) -> PropagatorResult;
}

pub struct EngineConfig {
    pub variable: Box<dyn VariableSelector>,
    pub value: Box<dyn ValueOrderer>,
    pub propagators: Vec<Box<dyn Propagator>>,
    pub scan_order: ScanOrder,
    pub blackwood: Option<Arc<BlackwoodSchedule>>,
    pub path_skeleton: Option<PathSkeleton>,
    pub parallelism: Parallelism,
    pub break_symmetry: bool,
}

impl EngineConfig {
    pub fn builder() -> EngineConfigBuilder { ... }
}

// Profiles become builder calls, not const slabs:
pub mod profiles {
    pub fn joe_depth150_bp_par(bp: Arc<EdgeBpMarginalsData>) -> EngineConfig {
        EngineConfig::builder()
            .variable(BorderFirstMrv)
            .value(EdgeBpMarginals::new(bp))
            .propagator(Ac3)
            .propagator(GaColor)
            .propagator(MultisetEquality)
            .propagator(ClassBalance)
            .depth_gate(150)
            .parallel()
            .build()
    }
    pub fn blackwood_raw(sched: Arc<BlackwoodSchedule>) -> EngineConfig {
        EngineConfig::builder()
            .variable(BorderFirstMrv)
            .value(BlackwoodHeuristic)
            .blackwood(sched.clone())
            .scan_order(ScanOrder::RowMajorBottomUp)
            .build()
    }
    // ... ~7 profiles, replacing today's 25 constructors.
}
```

### Why this and not the alternatives

Evaluated four candidates (full sketches in
`project_e2_vol16_cleanup_anchor.md`):

| option | runtime cost | adds-a-dimension cost | rejected because |
|---|---|---|---|
| A — trait + dyn | ~5% vtable | new trait + new field; existing strategies untouched | (picked) |
| B — type-state generics | 0% | every profile is a new monomorphisation | compile-time explosion + brutal error messages |
| C — plugin registry (data-driven) | < 1% | new struct + `inventory::submit!` | premature without a stable strategy set; loses compile-time safety |
| D — builder DSL with marker types | 0% | new builder method + new field on plain `EngineConfig` | doesn't solve "adding an axis touches 6 files" — only adds compile-time validation on top of today's model |

The ~5% vtable cost on Option A is the **only** unappealing
property, and it's bounded by:

1. The current profile already shows 14.6% in bounds-checking
   and 8.6% in `Range::spec_next` — vtable cost is a small slice
   of a pie that's mostly recoverable elsewhere (Cat-4 perf
   cleanup).
2. `#[inline]` on the trait methods + small enum-dispatch shims
   (where it matters) recover most of it.
3. The hot inner loop touches three trait methods at most:
   variable selection (1× per descent), value ordering (1× per
   placement), propagator chain (≤ N propagators per placement,
   N ≤ 6 today). The number of vtable calls per node is bounded
   and small.

### Constraints introduced by this decision

- **`EngineConfig` is no longer `Copy`** (Box<dyn> is not Copy).
  All callers that copy a `const` profile must be rewritten to
  `EngineConfig::builder()...build()` at call time. This is the
  main migration cost in Cat-2.
- **`Solver: Send + Sync`** — the strategy traits must themselves
  be `Send + Sync` (the workers in `rayon::scope` share them).
  Today's `Solver` is `Send` only; need to verify nothing leans
  on `!Sync`.
- **Profiles become factory functions, not constants.** The
  proto/server registry table now indexes into a function map
  (`HashMap<&'static str, fn(...) -> EngineConfig>`), not a
  static constant. Schedule injection (Blackwood) becomes a
  natural part of the factory signature, resolving the
  vol-15 "schedule has no proto home" carve-out cleanly.

### Migration path

1. Vol-16 Cat-2 ships the trait surface + EngineConfigBuilder +
   profiles module. Existing `EngineConfig::const FOO` slabs are
   replaced one-by-one; `EngineSolver::foo()` constructors collapse
   to one-liners that call into `profiles::foo()`.
2. The dispatch layer in `recurse` + `place_and_propagate_opts`
   switches from `match self.config.variable_order { ... }` to
   `self.config.variable.next(state)`. Same for value order and
   propagators.
3. After the migration lands, measure nps before/after on
   canonical E2 single-thread. If the vtable hit is < 5%, accept
   it. If > 10%, revisit Option B (type-state) for the inner-loop
   dispatch only — but keep the trait surface for the outer
   composition.

### Open question — deferred to vol-17

Should profiles be **JSON-loadable** (Option C, plugin registry)?
The bench-audit harnesses would benefit from being able to spec
an experiment configuration as JSON rather than as Rust code. But
the strategy set is not yet stable (vol-17 will add at least the
calibrated Blackwood schedule + likely a break-tolerant
propagator stack). Premature to commit to JSON config now; revisit
once vol-17 lands.

---

## Resolved design decisions

These were the six open questions; answers below are committed unless
revisited explicitly.

### 1. Proto schema

**Event union.** Protobuf `oneof` inside a common envelope. Forward-compat:
mandatory `schema_version` field; clients log a warning when they see a
version higher than they were compiled for and drop unknown variants.

**Portfolio selection.** `SolveRequest` carries `repeated SolverSelection`,
not a single solver enum. Each selection: `{ solver_id,
heuristic_profile, seed, per_solver_options }`. Every emitted event carries
`solver_run_id` so the frontend demultiplexes the merged stream.

**PathPolicy** is a oneof inside `PathConfig`:

```proto
message PathConfig {
  repeated uint32 path = 1;
  repeated uint32 hint_positions = 2;
  repeated Piece hint_pieces = 3;
  oneof policy {
    Strict strict = 4;
    OrderingPrior ordering_prior = 5;
    PrefixConstraint prefix_constraint = 6;
    Ignored ignored = 7;
  }
}
message PrefixConstraint { uint32 k = 1; }
// Strict, OrderingPrior, Ignored are empty placeholders for future fields.
```

**Event envelope.** Common fields at the top, oneof inside:

```proto
message SolverEvent {
  uint32 schema_version = 1;
  uint64 solver_run_id = 2;
  uint64 node_id = 3;             // solver-local monotonic counter
  uint32 depth = 4;
  uint64 timestamp_us = 5;        // relative to solve start, not wall-clock
  oneof body { ... }
}
```

`timestamp_us` is relative to solve start so traces are comparable across
runs. `node_id` is solver-local (multiple solvers in the portfolio have
overlapping node_ids — demux via `solver_run_id`).

**Board on the wire.** `repeated CellAssignment { position, piece_id,
rotation }`. `PartialSolution` carries only changed cells (delta). `Solved`
carries all cells.

**ListSolvers response.** Each entry: `{ solver_id, display_name,
description, supported_path_policies[], heuristic_profiles[] }`. Frontend
renders the support matrix from this — no hardcoded knowledge.

### 2. EventSink trait + throttling

The trait is intentionally minimal — solvers always emit; sinks decide:

```rust
pub trait EventSink {
    fn emit(&mut self, event: SolverEvent);
    fn should_continue(&self) -> bool;  // cooperative cancellation
}

pub struct NullSink;
impl EventSink for NullSink {
    #[inline(always)] fn emit(&mut self, _: SolverEvent) {}
    #[inline(always)] fn should_continue(&self) -> bool { true }
}
```

`NullSink::emit` inlines to nothing; the solver writes `sink.emit(...)`
unconditionally and the compiler erases the call when the sink is
`NullSink`. This is why `&mut dyn EventSink` (not `Option<...>` or feature
flags) was the right choice.

**Throttling is a wrapper sink**, not solver-side logic:

```rust
pub struct ThrottledSink<S> {
    inner: S,
    config: ThrottleConfig,
    state: ThrottleState,
}
```

Throttle per event category, not globally. Terminal events
(`Solved`/`Exhausted`/`TimedOut`/`Cancelled`/`Started`) always pass.

**Default rates by sink type:**

| Category | Wire (UI) | Benchmark | JSON dump |
|---|---|---|---|
| Terminal events | always | always | always |
| `Backtrack` (depth > threshold) | always | always | always |
| `VariableSelected`, `ValueTried` | first 1000 nodes, then 1/200 | suppressed | every event |
| `ConstraintPropagated`, `DomainWipeout` | first 1000 nodes, then 1/200 | suppressed | every event |
| `PartialSolution` | every 100ms or 50 cell-changes | suppressed | every 500ms |
| `Stats` | every 250ms | every 500ms | every 1s |
| `Backtrack` (shallow) | every 50ms aggregate | suppressed | every event |

The "first 1000 nodes full" rule preserves early-decision fidelity (the
interesting part) while letting deep churn be sampled.

**Sampling, not dropping.** When events are sampled out, the sink emits a
periodic `Stats` event with sampled-out counts. UI shows "8,432 backtracks
(42 displayed)."

**Config-driven.** `SolveRequest.throttle_config` overrides defaults.
Educational mode requests full traces (small puzzles, low volume).

**Adaptive throttling** based on outbound channel pressure: v2.1 future
work. Trait shape supports adding `should_emit_category(c) -> bool` later
without breaking changes.

**Rendering math.** Frontend can ingest ~600 events/sec without jank
(60fps, cheap React updates via Zustand + TanStack Query). Defaults above
stay well under that sustained (~50/sec) and burst high in the first
second (~1000) which is when the user is paying most attention.

### 3. PathManager UX

Single page, three sections, two routes (`/edu/path` and `/research/path`)
mounting the same component with different `defaultMode` and `glossary`
props.

**Layout:**

- **Top:** Path canvas (SVG grid). Click extends path, drag-select for
  ranges, right-click cell opens hint editor (piece picker filtered by
  remaining pieces, rotation picker, remove button). Hint cells render
  with colored border.
- **Middle:** Mode picker — radio with four options + one-line explainers:
  - *Strict order* — "Solver follows your path exactly. Best for learning."
  - *Ordering hint* — "Modern solvers use your path as a tie-breaker."
  - *Forced start* — "First N cells fixed; solver decides the rest."
  - *Ignore path* — "Use the solver's own ordering. Path recorded but
    unused."
- **Middle (conditional):** When *Forced start* is selected, K input +
  slider (default = half path length).
- **Bottom:** Solver picker + Play. Solvers incompatible with current mode
  are grayed out with tooltip ("doesn't support Strict order — try v1 or
  switch mode to Ordering hint"). Incompatible combos are unselectable.

**Persistence.** Paths and hints save to localStorage under a versioned
key. JSON export/import for sharing across machines.

**Animation.** Two visualizations:
- *Strict / Forced start* — animate path traversal cell by cell.
- *Ordering hint / Ignored* — animate solver decisions from the event
  stream, with the user's path drawn as a faint underlay (so they see how
  the heuristic agreed or diverged).

**Comparison feature (research mode, new).** "Compare" button runs the
same puzzle with two different (mode, solver) combos in parallel,
synchronized timeline scrubber, side-by-side board renders. Addresses the
audit's "currently impossible" path-comparison gap.

### 4. Throttling defaults

See §2 — defaults table is authoritative. Principle:

- **Wire sink** optimizes for smooth UI at 60fps.
- **Benchmark sink** optimizes for zero overhead.
- **JSON sink** optimizes for fidelity (offline research traces, replay).

Educational mode requests full traces; puzzles are small.

### 5. Cancel semantics

**Cancellation states:**

- **Searching, no solution yet** → returns `Cancelled { best_partial:
  Option<Board>, stats: FinalStats }`. Best partial = deepest valid
  placement during the run, tracked by the solver as a cheap side effect
  (one update per new depth reached).
- **Searching, solutions already found** ("find all" mode) → returns
  `Cancelled { solutions_so_far: Vec<Board>, stats }`. For "first
  solution" mode, the solver would have already returned `Solved`.
- **Finalizing** (past search, building stats) → cancel is no-op; solver
  returns actual result.

**Mechanism.** `EventSink::should_continue()` is the cancellation channel.
Solvers check it:

- At every backtrack (cheap natural breakpoint)
- Before entering a propagator loop (avoid wasted work)
- Never in the inner edge-check loop (too hot)

Check frequency: ~once per few hundred nodes. Worst-case cancel latency:
single-digit ms.

**Portfolio mode.** Cancelling the portfolio flips `should_continue` on
every sink. Workers notice on next check, return cleanly. Portfolio
runner joins all, aggregates results. No `thread::abort`, no panics.

**gRPC stream drop = cancel.** tonic surfaces the stream lifecycle; when
the client disconnects, the server-side handler drops, sinks flip,
workers wind down. The explicit `Cancel` RPC is for graceful
"client-still-connected wants to stop."

**Idempotency.** Cancel after Solved/Exhausted/TimedOut returns
`CancelResponse { already_terminal: true }` — no-op.

### 6. Benchmark baseline

**Three tiers:**

**Tier 1 — CI regression gate (~10 puzzles, <30s total).**
- Sizes 2, 3, 4 × colors 2, 3, 4 + size 5/colors 5 + size 6/colors 3.
- Median of 3 runs per puzzle.
- Baseline: `crates/benchmark/baselines/ci.json`, committed.
- Fail PR if any puzzle: unsolved, or >20% slower than baseline mean.
- 20% threshold (not 5%) accounts for CI hardware variance. False
  positives are worse than slow regressions.

**Tier 2 — Nightly regression (all 56 puzzles, ~15min on fast box).**
- Dedicated CI job, statistical reporting (mean, p95, p99 across 5 runs).
- Per-solver-and-heuristic breakdown — catches "you optimized DLX but
  slowed CSP."
- Flags >10% regressions for human review; doesn't fail the build.
- Baseline: `crates/benchmark/baselines/full.json`.

**Tier 3 — Research frontier (on-demand).**
- Size ≥7, color ≥6 puzzles. Not gated, not nightly.
- Invocation: `cargo run -p benchmark -- research --size 8 --colors 6-9`.
- Timeouts reported as data, not failures.
- Output: JSON to `data/partial_results/` (existing directory, keep it).

**Baseline regeneration.** `--regenerate-baseline` flag exists but only
runs from a tagged commit on `main`. PRs cannot regenerate baselines.
"I think this is faster" must be justified by reviewing the baseline
JSON diff.

**Per-heuristic attribution is mandatory.** Per-solver-and-heuristic
times are the actual baseline numbers; aggregate "fastest solve" is also
reported but not the gate. This is what catches regressions in one
strategy that the portfolio aggregate would hide.

---

## Open questions (next round)

Now that the contract above is settled, these become the next things to
nail down:

1. **The exact proto file.** Write `proto/solver/v2/solver.proto` as the
   single source of truth. Generate Rust + TS stubs, verify both compile.
2. **`SolverId` and `HeuristicProfile` namespacing.** String IDs vs enums,
   stability guarantees across versions, how new strategies opt in.
3. **`solver-trait` API beyond `solve()`.** Does the trait need
   `validate_request()`, `estimate_difficulty()`, or are those out of scope
   for v2.0?
4. **Telemetry beyond events.** Prometheus/OpenTelemetry? Or just
   structured logs to stderr and let Terra Numerica plug their own
   collector?
5. **WASM bundle size budget.** ~~Open.~~ **Resolved 2026-05-11**: with
   only `generator` + `solver-naive` exposed, the optimized bundle is
   ~91 KB (128 KB raw → wasm-opt -O3). Budget set at **500 KB optimized**:
   leaves headroom for adding parity/island propagators or a tiny CSP
   variant later. If a future addition pushes past 500 KB, prefer
   server-side execution for that feature over enlarging the educational
   bundle.

---

## What stays, what goes, what's new

**Stays** (port to v2 unchanged or near-unchanged):

- SVG board/piece rendering primitives
- 56-puzzle benchmark corpus in `data/benchmark/`
- Compose-based deployment topology
- BASE_PATH / reverse-proxy env-var pattern
- The four page concepts (Home, DIY, Solver, Stats, PathManager)
- The hints concept (now actually wired through)

**Goes**:

- v0 (not even used today)
- Spiral path baked into the board (becomes a Strict path the user can pick)
- Envoy proxy
- CMake, vcpkg, optionally Nix
- 4 docker-compose files (collapse to 1 + 1 prod variant)
- MUI, Recoil
- AbortController + boolean booleans in solver UI state
- 12 heuristic profile names with duplicates and dead branches
- Two divergent puzzle generators
- v2's commented-out rare-color bonus
- v3's `CORNER_HEAVY` and `REVERSE_LCV` (silent duplicates)
- The dummy `exit 0` healthcheck

**New**:

- Typed `SolverEvent` stream with throttling
- `PathPolicy` enum and solver support matrix
- WASM educational mode
- Parity propagator (Gemini gap)
- Island propagator (Gemini gap)
- Seeded reproducible benchmarks with baseline-diff CI
- Heuristic inspector UI (domain heatmaps from event stream)
- Portfolio runner UI (side-by-side event stream comparison)
- Sweep mode UI (corpus generation + statistical view)
- Real cancellation RPC
- ListSolvers RPC for runtime portfolio discovery
- Worked Traefik example in `deploy/`
- Real gRPC healthcheck
- Vitest + Playwright tests
- localStorage persistence for paths and preferences
- Glossary / inline term definitions in educational mode

---

## Status

Design draft. Reflects the audit findings as of 2026-05-11 and the
discussion around portfolio architecture, event stream design, PathManager
triple-mode semantics, and WASM educational scope. No code written yet.

## Research log (Experiments A–G, 2026-05-11)

Cross-references `v2/RESEARCH_NOTES.md` for the full hypothesis/measure/
verdict trail. Headline state after deep-edge work:

- **Engine baseline** (`border_first_lcv`): 1.3s aggregate on size-6/7
  corpus (32 puzzles).
- **+ GAColor (incremental)** (`border_first_gacolor`): −13% wall, same
  pruning quality, paper-validated symmetric-alldiff necessary-condition
  variant. Production default for low-cost propagation.
- **+ AC-3 cascading** (`gacolor_ac3`): **−39% wall, −84% nodes**.
  Production default for mid-difficulty cells.
- **+ RootSplit parallel** (`gacolor_ac3_par`): cracks every size-8
  puzzle in our corpus including the previously-DNF `size_8_colors_7`.
  Headline solver for hard problems.

Three negative results worth recording in the architecture itself:

- **CHESS variable ordering** is currently incompatible with our
  propagation strength. Needs Régin-style matching filter on the Edge
  Color Graph before it pays off. Two controlled experiments confirm.
- **Rotational symmetry breaking via corner pinning** is a no-op for
  FirstSolution mode because lowest-piece-id corner is already tried
  first by implicit ordering. Kept dormant for AllSolutions mode.
- **Necessary-condition propagators** (parity, parity-island, naive
  gacolor) net-cost on easy puzzles even when correct, because the
  per-node overhead is paid even when the check rarely fires. Strict
  improvements require incrementality (gacolor v2 achieves this).

Cross-domain ideas surveyed and ranked for future experiments:
spatial energetic reasoning (job-shop scheduling), full Régin matching
GAColor (CP theory + paper), CDCL nogood learning (SAT), SAC (CP
theory), local-search-after-AC-3 (protein folding / MILP).

