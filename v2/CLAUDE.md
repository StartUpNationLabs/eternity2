# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Scope

All v2 work lives inside `v2/`. The sibling directories of `v2/` (`solvers/`, `frontend/`, `api/`, `docker-compose/`, `envoy/`, `nix/`, etc.) are the legacy C++/JS/Nix stack — **read-only reference material**. Do not modify them.

`v2/V2_DESIGN.md` is the contract everything implements. It is a living document: when implementation reveals a better answer or a hidden constraint, edit `V2_DESIGN.md` in the same change. Do not let code and spec drift.

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
