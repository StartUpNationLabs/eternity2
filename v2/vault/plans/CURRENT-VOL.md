# Current vol — vol-106 OPEN 2026-05-16 ~07:55 CEST

**Author**: autonomous agent (user away ≥ 1 month).
**Theme**: hyper-optimized Rust port of libblackwood (Bucas's
295M-nps unrolled-C engine). User direct redirect on 2026-05-16
~07:50 CEST: "move on from MIP. The migration of blackwood here in
an hyper-optimized manner is a cool topic" + "why can't we make
something as good ourselves in RUST?".

## Why this is the right vol

The user is right. There's no language ceiling stopping Rust from
matching C on a tight DFS. Our 367k nps vs C's 295M nps gap (800×)
is purely architectural:

1. `solver-engine` is GENERIC — VTable dispatch on `dyn EventSink`,
   `dyn ValueOrder`, `dyn ScanOrder`. Hot path has indirections even
   when propagators are toggled off.
2. No per-cell unrolling. Bucas emits one mega-function with 256
   labelled depth blocks (`'depthN: loop { ... }` in Rust terms); we
   recurse.
3. Heap-allocated `SearchState`. Bucas's `board[WH]`,
   `pieces_used[WH]`, `cumulative_*[WH]` are stack arrays sized at
   compile time.
4. Constraint-indexed candidate lists rebuilt per node. Bucas
   precomputes `master_lists_of_union_rotated_pieces[ref]` ONCE,
   indexed by neighbour-color-pair; we recompute bitsets.

LLVM with `target-cpu=native` will produce code competitive with gcc
on the equivalent C shape. The work is: emit that shape.

## Binding items (≤ 3 per CLAUDE.md)

### T1 — `eternity2-blackwood-codegen` crate, PoC level

A new workspace crate that, given a puzzle CSV at build/run time,
generates a Rust source file containing one `solve(...)` function
with WH unrolled depth blocks. Initial scope: 4×4 toy puzzle (16
cells, 16 pieces), no heuristic schedule, no break index — just
raw unrolled DFS. Goal: PROVE the shape compiles, runs correctly,
and is measurably faster than the equivalent recursive call.

Acceptance:
- Compiles cleanly under workspace lints.
- Solves a generated 4×4 toy in identical or fewer nodes vs current
  `vanilla_fast` on the same puzzle.
- Single-thread nps ≥ 2× current `BLACKWOOD_RAW` on 4×4.

### T2 — scale T1 to 16×16 canonical with full Blackwood schedule

Once T1 PoC is verified, generate the canonical 16×16 mega-function
with:
- Heuristic-pattern schedule (vol-15's `BlackwoodSchedule`).
- Break-index allowance at the standard depths.
- Per-cell precomputed `lists_by_constraint`.
- Stack-allocated state.

Acceptance:
- Single-thread nps ≥ 10× current `BLACKWOOD_RAW` (3.67M nps target).
- Stretch goal: 10-30M nps (within 10× of Bucas's C).
- Variance reporting: ≥ 8 seeds × {30s, 5min}.

### T3 — Concept page write-up of the codegen architecture

Whether T1/T2 deliver the headline numbers or not, write the
codegen architecture as a concept page so the next vol can pick it
up. If the headline numbers fall short, document WHY (e.g. LLVM not
honouring inlining of WH=256 blocks, register pressure on
apple-m1, etc.) — that's a publishable null per [[rigor-rules]].

## What this is NOT

- Not a CVC track. CVC is reserved as the user's invention but the
  user redirected away from 8×8 toy work.
- Not a MIP track. Vol-105 setup is preserved in vault/concepts/
  for whoever picks it up later.
- Not a score-axis claim. The point is THROUGHPUT, not records.
- Not a port of libblackwood's Python multiprocessing or interactive
  thread orchestration — only the per-cell unrolled DFS core, what
  Bucas calls `gen_solve_function`.

## Audit-at-open compliance

23 `unbuilt` items in BACKLOG. Reviewed; most aged ≥ 3 vols are
either score-axis (orthogonal to this vol) or already deferred
with reason. The two engine-perf items adjacent to this work
(`incremental-ac3-count-maintenance`, `restore-or-simd`) are kept
`partial`/`unbuilt`; they are smaller wins than the codegen path
and would conflict with the codegen architecture (which doesn't
run AC-3 at all). Add a note to BACKLOG marking those as
"deferred behind T2".

## Linked

- [[../INDEX]]
- [[../DIRECTIVE_VOLS_106-115_BLANK_PUZZLE_SPEEDUP]]
- [[../IDEAS_FROM_BLANK_2026-05-16]] item #1 (port libblackwood).
- [[../concepts/blackwood-algorithm]] — current Rust Blackwood.
- [[../concepts/mcgavin-blackwood-gap-analysis]] — quantifies the
  800× throughput gap this vol attacks.
- [[../sessions/vol-105|vol-105 close]] — last vol.
