# VOL-33 — code quality refactor (vol-25 items)

**Opened**: 2026-05-14 (vol-32 close).
**Status**: drafted at vol-32 close.
**Theme**: **single focus** — ship the code quality refactors measured
at vol-25 but never executed (deferred 8 volumes).

User asked for: "do vol-25 we had skipped" — this is the code quality
items. Splitting vol-33 into pure refactor work makes it easy to
ship without scope creep.

The companion **vol-34** is the throughput exploitation + record
chase work.

## Why this volume exists

Vol-25 measured the code debt landscape but never shipped the
refactors. Per BACKLOG, deferred since vol-25 (8 vols ago) the items
must be picked or marked wont-do per audit-at-open discipline.
We pick them.

## Why a dedicated refactor volume now

- The 76 bins are getting harder to add to (each new bin re-implements
  ~250 lines of CLI/loader/sink/score boilerplate).
- Vol-32's vanilla_fast + vanilla_fastest pair already duplicated the
  bucas URL / scoring code that the export-crate would consolidate.
- solver-engine/src/lib.rs at 5011 lines is the slowest-to-recompile
  unit; splitting it speeds every dev cycle.
- Net effect: vol-34+ work ships faster on a clean base.

## Audit-at-open

The code-quality items in BACKLOG, deferred since vol-25:

1. `extract-eternity2-time-crate` (1h, since vol-25)
2. `extract-eternity2-export-crate` (4-6h, since vol-25) — **highest leverage**
3. `split-solver-engine-lib-into-5-modules` (4h, since vol-25)
4. `extract-eternity2-puzzle-io-crate` (3-4h, since vol-25, blocked on #2)
5. `consolidate-bin-harness` (8-10h, since vol-25, blocked on #2)

All 5 items are **8 vols deferred**. Per audit-at-open: must be picked.

## Binding items (5 sequential refactors)

Ship in order, each independently committable:

### T1 — `extract-eternity2-time-crate` (1h)

Move identical `Clock` impls (solver-engine, solver-naive) to a
single `eternity2-time` crate. Trivial dedup, ships first to validate
workflow. Both crates already implement the same wasm32 vs native
shim.

### T2 — `extract-eternity2-export-crate` (4-6h)

Consolidate **5 duplicated utilities** into one crate:
- board scoring (`bench-audit::score_board` + `benchmark::report::score_matched_edges`)
- bucas URL encoding (currently buried unexported in `benchmark::report`)
- `DumpedBoard` JSON serialization
- ASCII board rendering
- report writing

Replace each duplication call site with `use eternity2_export::*`.
Test: `cargo test --workspace` passes; existing bins still work.

**This is the highest-leverage item**. Unblocks T4 + T5.

### T3 — `split-solver-engine-lib-into-5-modules` (4h)

Internal module split of `solver-engine/src/lib.rs` (5011 lines):
- `paths.rs` (~330 lines, pure geometry, zero backlinks) — ship first
- `config.rs` (~200 lines, enums + struct)
- `schedule_builders.rs` (~410 lines, pure factories)
- `profiles.rs` (~350 lines, EngineSolver + 40 factories)
- `lib.rs` keeps SearchState + recurse + propagate_ac3 (~3200 lines, untouched)

Multi-crate split rejected per vol-25 notes as overkill until a
downstream consumer wants schedules/paths independently. Internal
module split is the right scope. Each step independently shippable.

### T4 — `extract-eternity2-puzzle-io-crate` (3-4h, blocked on T2)

Hint loading (`benchmark::loader::load_puzzle_with_hints`) and CSV
parsing belong with the puzzle types, not in the benchmark crate.
Currently invisible to solvers from naming.

### T5 — `consolidate-bin-harness` (8-10h, blocked on T2)

76 bins across `bench-audit` and `benchmark` share ~250 lines of
boilerplate each (CLI parsing, puzzle load, ProgressSink, solver
instantiation, report writing). Extract into `bin-common`. **~7K
lines of copy-paste eliminated**.

## Vol-close protocol

1. Update BACKLOG: all 5 items → `built`. Concept page `code-debt`
   amended.
2. Verify: `cargo test --workspace` passes; `vanilla_fast --pin-hints`
   still hits 95M+ pp/s (no regression).
3. Write `sessions/vol-33.md`.
4. Update INDEX (no score row needed — code quality vol doesn't move scores).

## What this vol explicitly does NOT do

- ❌ No new algorithms.
- ❌ No record-chasing (that's vol-34).
- ❌ No throughput experiments.
- ❌ No new propagators.

**Pure refactor only.**

## Honest cost estimate

- T1: 1h
- T2: 4-6h
- T3: 4h
- T4: 3-4h (after T2)
- T5: 8-10h (after T2)

**Total**: 2-3 days. Mechanical work; can interleave with vol-34 if
the user wants score-chase in parallel.

## Linked concepts

- [[code-debt]] — vol-25 measurement + restructure plan.
- [[vol-25]] — original measurement.
