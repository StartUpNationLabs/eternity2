# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Scope

All v2 work lives inside `v2/`. The sibling directories of `v2/` (`solvers/`, `frontend/`, `api/`, `docker-compose/`, `envoy/`, `nix/`, etc.) are the legacy C++/JS/Nix stack — **read-only reference material**. Do not modify them.

`v2/V2_DESIGN.md` is the contract everything implements. It is a living document: when implementation reveals a better answer or a hidden constraint, edit `V2_DESIGN.md` in the same change. Do not let code and spec drift.

## Research vault — READ FIRST when starting a new volume

`v2/vault/` is the concept-first knowledge base for E2 research. Established 2026-05-13 to fix the recurring pattern of plan items deferred 5–8 volumes. It is an Obsidian-compatible vault: pages link via `[[wikilink]]`, the canonical entry point is `vault/INDEX.md` (Map-of-Content).

The vault is the single source of truth for **what we know and what we've tried** on Eternity II. Code is the source of truth for *what we currently do*; the vault is the source of truth for *the research history, current bounds, and the open questions*.

### Layout

```
vault/
├── INDEX.md                Map-of-Content (read first if disoriented)
├── README.md               vault discipline (one page)
├── concepts/               one page per algorithm class, propagator, structural finding
├── basins/                 one page per notable board or basin
├── sessions/
│   ├── vol-NN.md           per-volume compact journal (one page per vol)
│   ├── night-NN.md         per-night-session journal
│   └── archive/raw/        original long-form RESEARCH_NOTES_*.md / NIGHT*.md / V15_*.md
├── plans/
│   ├── BACKLOG.md          canonical T-list across volumes
│   └── CURRENT-VOL.md      the in-progress volume's binding items (1–3 max)
└── reference/
    ├── memory-crosswalk.md ~/.claude/.../memory/*.md → vault page mapping
    └── reference-*.md      mirrors of authoritative reference memories
```

### Page schema — concepts

Every `concepts/<slug>.md` SHOULD contain:

1. **Title** (`# Concept name`).
2. **Status line**: `built` | `partial` | `unbuilt` | `refuted` | `wont-do`.
3. **Origin**: which volume introduced or measured it.
4. **Files**: rust source paths and/or scripts.
5. **Definition** — one short section. What the thing IS, not what we tried.
6. **What we measured** — empirical results table where possible. Cite the volume.
7. **What was refuted / unsound conditions** — if applicable.
8. **What's still open** — backlog hooks.
9. **Linked concepts** — wikilinks to related pages.
10. **Linked memory** — names of relevant `~/.claude/.../memory/*.md` entries.

Concepts are **stable**. They are amended (not rewritten) as new measurements come in. A concept whose status flips from `built` to `refuted` keeps its history; the status line and a refutation section are added — **no quiet deletes**.

### Page schema — basins

Every `basins/<slug>.md` SHOULD contain:

- **Score** and (if measured) **bound** ([[relaxed-bound]]).
- **Discovery**: vol + algorithm + seed if reproducible.
- **Properties**: geometry, locked-under-K, MaxSAT-proven optimality.
- **What couldn't break it**: enumerated dead ends.
- **What might break it**: open hypotheses.
- **Sister basins** and **Linked concepts**.

### Page schema — sessions

Every `sessions/vol-NN.md` (compact summary) SHOULD contain:

- **Theme** — one-line headline.
- **Raw** — link to the original `archive/raw/RESEARCH_NOTES_NN.md`.
- **What was attempted** — bullet list of distinct tracks.
- **What was measured / kept** — bullet list with numbers + concept links.
- **What was refuted** — bullet list with reasoning.
- **Concepts touched** — wikilinks to every concept page added or amended this vol.
- **Open at close** — what carries into the next vol.
- **Linked memory** — relevant memory file names.

Sessions are **journals, not encyclopedias**. They describe what happened *this volume*; durable knowledge belongs in `concepts/`. A session page should be readable in under 90 seconds.

### Status taxonomy

| Status | Meaning |
|---|---|
| `unbuilt` | proposed; no code or measurement yet |
| `partial` | code exists but not fully evaluated, OR measurement is partial |
| `built` | shipped + measured, with current numbers in the page |
| `refuted` | empirical or theoretical refutation, evidence linked |
| `wont-do` | explicit decision not to pursue, with reason |

Aged `unbuilt` (≥ 3 volumes) is a vault smell. The audit-at-open rule resolves it.

### Naming conventions

- **Slug-kebab-case**: `bound-ascent.md`, not `BoundAscent.md` or `bound_ascent.md`.
- **Basin slugs** include score: `basin-457-pt.md`, `basin-440-469.md`.
- **Session slugs** zero-padded: `vol-01.md`, `vol-22.md`.
- **Wikilinks** use the slug without extension: `[[basin-457-pt]]`, `[[bound-ascent]]`.
- **Cross-folder links** use the relative path: `[[sessions/vol-14]]`, `[[../sessions/archive/raw/RESEARCH_NOTES_14|RESEARCH_NOTES_14.md]]` (display text after `|`).

### Audit-at-open discipline

**First actions of every new volume** (the *prevent-8-vols-of-drift* protocol):

1. Read `vault/plans/BACKLOG.md`. Skim every entry. The whole list.
2. For each item with status `unbuilt` and `since: ≤ vol-(current−3)`: **make a decision**. Pick it, demote to `wont-do` with reason, or argue (in writing in BACKLOG) why it deserves another vol.
3. Read the previous vol's `CURRENT-VOL.md`. Note what was promised vs delivered.
4. Read the previous vol's `sessions/vol-NN.md` — specifically the "Open at close" section.
5. Write a **new** `CURRENT-VOL.md`. At most **3 binding items** (often 1). Add an "Audit-at-open compliance" section explicitly listing the aged items resolved this vol.

**Why 3 max**: every previous vol that committed to 6+ items shipped 1–2. The vol-22 close meta-finding ("8 volumes of deferring prune-restart") drove the limit.

### Discoveries during a volume

Mid-volume findings are **logged, not chased**:

1. Anything genuinely new (a new operator, a new measurement, a new bound) → add an entry to `BACKLOG.md` with status `unbuilt` and `since: <current vol>`.
2. Do **not** pivot the current vol's binding items. Their job is to ship.
3. Exception: if the discovery *obsoletes* a binding item (e.g., a refutation makes the planned build pointless), update the binding item to `wont-do (reason: X discovery this vol)`.

This rule exists because "discovery hijacks the planned work" was responsible for ~80% of the deferred-item pattern. The energy to write a BACKLOG entry is much less than the cost of mid-vol pivoting.

### Vol-close protocol

At vol close:

1. Update the status of each binding item in `BACKLOG.md` (`built` / `partial` / `refuted` / `wont-do`).
2. **Amend every concept page touched** (new measurements, new linked sessions, status updates). Do not duplicate measurements across pages — concept page is canonical.
3. Write `sessions/vol-NN.md` per the schema above. One page, compact.
4. If notable basins were discovered, add `basins/basin-<score>-<slug>.md`.
5. Draft `CURRENT-VOL.md` for the next vol using the audit-at-open protocol.
6. Update `memory/MEMORY.md` if a finding warrants a persistent agent memory.

### Memory ↔ vault interplay

The agent's persistent memory (`~/.claude/.../memory/*.md`) and the vault overlap. Rules:

- **Memory is for agent re-loading**: high-density, prose, frontmatter-tagged. Loaded into every conversation.
- **Vault is for human + agent navigation**: structured, wikilinked, browsable in Obsidian.
- A finding usually exists in **both**. The memory entry is dense; the vault entry is structured.
- `vault/reference/memory-crosswalk.md` maps every memory file to its vault page(s). Update it when a new memory entry is added.
- When a memory entry's content has been **fully absorbed** into a vault concept page, the memory entry can be (a) trimmed to a one-line pointer with a `[[wikilink]]`, or (b) left as the canonical short-form reference. Either is fine; the canonical form *for the human researcher* is the vault page.

### No quiet deletes

If a concept is refuted, vault hygiene forbids removing the page. Instead:

- Update the status line to `refuted`.
- Add a `## Refutation` section with the evidence (volume, measurement, reasoning).
- Keep all prior content. Future researchers (including ourselves) must be able to see *why* it was refuted, not just that it was.

This rule preserves the audit trail and prevents re-attempting the same dead end (the [[dead-ends]] concept page exists for exactly this reason).

### When in doubt

- If unsure whether something is a `concept` or a `session` thing: **does this describe a durable algorithm/finding (concept) or a one-time observation tied to a particular volume (session)?**
- If unsure whether to write a new concept page: **will anything in a future volume link to this?** If yes, page. If no, session note suffices.
- If unsure whether a measurement is worth a memory entry: **would a fresh agent re-loading the project from scratch make a worse decision without this fact?** If yes, memory. If no, vault page alone.
- If in doubt about whether to *delete* something: **don't**. Mark, amend, or move — never silently remove.

## Build, test, run

The toolchain is a Cargo workspace at `v2/Cargo.toml` plus a pnpm frontend at `v2/frontend/`. All commands assume `$HOME/.cargo/env` is sourced.

```bash
# Rust workspace
cargo build --workspace
cargo test --workspace
cargo test -p eternity2-solver-engine                       # single crate
cargo test -p eternity2-solver-engine --release some_test   # single test (release for perf-sensitive)
cargo test -p eternity2-solver-engine -- --ignored --nocapture  # perf-comparison tests are #[ignore]d

# WASM bundle (educational mode)
./wasm/build.sh                                             # wasm-pack + system wasm-opt; outputs to wasm/pkg/
node wasm/test-node.mjs                                     # smoke test the bundle

# Server
cargo run -p eternity2-server                               # binds 0.0.0.0:50051 (E2_SERVER_BIND override)

# Frontend (from v2/frontend/)
pnpm install
pnpm gen:proto                                              # buf generate → src/gen/solver/v2/
pnpm test                                                   # vitest run
pnpm dev                                                    # vite dev server, proxies /grpc → :50051
pnpm build                                                  # production build

# Proto codegen verification harness (from v2/proto/_verify-ts/)
./node_modules/.bin/buf generate && ./node_modules/.bin/tsc --noEmit

# Deploy (from v2/)
docker compose -f deploy/docker-compose.yaml up -d --build

# Native "go fast" profile for perf comparisons (fat LTO, +5-15% on hot loops).
# Do NOT use for the WASM bundle. `.cargo/config.toml` sets target-cpu=apple-m1
# for aarch64-apple-darwin only — WASM unaffected.
cargo build --profile bench-fast -p eternity2-bench-audit --bin fleet
./target/bench-fast/fleet --budget-ms 60000 --label baseline --out base.json
# (edit code, rebuild)
./target/bench-fast/fleet --budget-ms 60000 --label after --out after.json
./target/release/compare base.json after.json
```

## Architecture (the big picture)

The codebase is a portfolio of solvers wired together through a typed event stream. The contract is the proto file; everything else is an implementation of one role.

**Data flow:** `proto/solver/v2/solver.proto` is the single source of truth. `wire` generates Rust types from it via `tonic-build` and exposes a `convert` module that translates between proto and native domain types (`eternity2-core::Puzzle/Board`, `eternity2-events::SolverEvent`, etc.). The server uses `wire::convert::*` at its RPC boundary; solvers never see proto. The frontend uses `@bufbuild/protoc-gen-es` to generate TS types from the same proto and `@connectrpc/connect-web` to call the server.

**Solver dimension:** there is one search engine. The legacy V2 ("CSP") and V3 ("DLX") C++ codebases converged into a single Rust backtracker (`solver-engine`) once written cleanly. The split was an artifact of code provenance, not algorithm structure. `solver-naive` is genuinely different (no domains, no propagation) and stays separate.

**Registry:** the canonical solver registry is `2 solver_ids × 7 heuristic profiles`. See `proto/solver/v2/solver.proto` for the comment block at top, and the server's `instantiate()` for the live mapping. New strategies opt in by **adding to ListSolvers and `instantiate()`** — not by changing the proto. `solver_id` and `heuristic_profile` are stable opaque strings.

**Config axes:** `EngineConfig` in `solver-engine` has three orthogonal axes: `variable_order`, `value_order`, `propagators`. Five engine profiles today are just preset combinations of these. Step 8 propagators (`class_balance`, `parity`, `island`) plug in here as bool toggles; new propagators add a flag and live as new functions in the `propagators` crate.

**Event sink contract:** solvers always call `sink.emit(event)` unconditionally. `NullSink::emit` is `#[inline(always)] fn(_) {}` so the call site monomorphizes to nothing — that's why the trait is `&mut dyn EventSink` and not `Option<...>` or a feature flag. Throttling is a *wrapper sink* (`ThrottledSink<S>`), never solver-side logic. Terminal events (`Started`, `Solved`, `Exhausted`, `TimedOut`, `Cancelled`) always pass throttling. Cancellation is cooperative via `sink.should_continue()` checked at backtracks and propagator entries — never in the hot inner loop. gRPC stream drop ⇒ sink's `should_continue` flips false ⇒ workers wind down cleanly; no `thread::abort`, no panics.

**Portfolio runner:** `solver-portfolio::run_parallel` spawns workers via `rayon::scope`, fan events through `crossbeam-channel` to a single merged sink on the calling thread (so the sink doesn't need `Sync`). Workers demux at the consumer side via `event.solver_run_id`. If any worker reports `Solved` in `FirstSolution` mode, the others' `should_continue` flips false.

## Project-specific traps

- **Do not name a crate `core`.** It conflicts with the `core` libstd prelude when `#![no_std]` is on. The crate is `eternity2-core`.
- **`std::time::Instant` panics on wasm32-unknown-unknown.** Both `solver-naive` and `solver-engine` have a `clock.rs` module that uses `js_sys::Date::now()` on wasm32 and `Instant` elsewhere. New solver crates need the same shim; `core` stays no_std and never sees a clock.
- **wasm-pack 0.14 ships an outdated wasm-opt** that rejects current rustc output. The package metadata disables wasm-pack's bundled wasm-opt; `wasm/build.sh` runs the system `wasm-opt` (`brew install binaryen`) with explicit `--enable-mutable-globals --enable-nontrapping-float-to-int --enable-sign-ext --enable-reference-types --enable-multivalue --enable-bulk-memory` flags.
- **JS Number can't hold u64.** `serde-wasm-bindgen::Serializer::new().serialize_large_number_types_as_bigints(true)` is mandatory when serializing types with `u64` fields (e.g., the puzzle fingerprint, event timestamps, `solver_run_id`). The frontend handles them as `bigint`.
- **Vite + Vitest version coupling.** Vitest 2.1.x resolves vite 5 as a transitive peer; mixing vite 6 + vitest 2 in pnpm produces hard-to-read TS type errors about `PluginOption` mismatches. The frontend pins vite 5.4.x to match.
- **In `vite.config.ts`, import `defineConfig` from `vitest/config`** (not `vite`) to get the `test` field type. Otherwise tsc rejects the config.
- **WASM import in TS** uses an alias `@wasm/eternity2_wasm.js` declared in `src/wasm.d.ts` and resolved by Vite to `../wasm/pkg`. Don't use absolute paths in `import()`; TS rejects them.
- **`#[ignore]` for perf-comparison tests.** Tests that benchmark propagator pruning strength run with `cargo test -- --ignored --nocapture`. They use *sum-across-seeds* assertions, not per-seed monotonicity — a stronger propagator can occasionally explore more nodes on a single seed by forcing an alternative path. The honest measurement is averages.
- **Propagator integration vs. strength are different.** A propagator is "v1 integrated" when the hook works and the algorithm is correct. Tuning pruning strength is ongoing and does not change the engine API. The current `parity_check` is correct but weakly pruning (~0% on a 6×6 sample) because it enforces only end-state feasibility; strong incremental per-side per-color budgets are a v2.1 task.

## Conventions

- **Comments:** default to none. Only add one when the *why* is non-obvious. `V2_DESIGN.md` is where the rationale lives; the code carries the *what* through identifiers and types.
- **No new top-level docs.** No per-crate README, no progress journals, no separate design documents. Single source of truth is `V2_DESIGN.md`.
- **Match the registry comment in `solver.proto` and the entries in `server::service::instantiate` + `list_solvers`.** These three must stay in sync. Update all three in the same change when adding a profile.
- **`SolverEvent` is the only way events leave a solver.** The proto envelope, the events crate, and the wire/convert layer all agree on `(schema_version, solver_run_id, node_id, depth, timestamp_us)` on every event. `schema_version = 1` is baked in; bump it only when introducing a breaking change to event bodies.
- **`#![forbid(unsafe_code)]` at every crate root.** Workspace lints enable `clippy::pedantic` and `clippy::nursery`; some noisy lints are allowed at the workspace level. Don't add `unsafe`.
- **Performance improvements over legacy are welcome and expected.** If a legacy pattern is wasteful (recomputed edges, HashMap where a dense Vec works, etc.), fix it as you port. Note the *why* of a non-obvious optimization in a one-line comment.
