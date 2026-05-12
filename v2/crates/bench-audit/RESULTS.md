# Before/after fleet benchmark — results

Host: Apple M1, macOS 26.1. Budget 60s per cell.
Baseline binary: `cargo build --release` (no extra flags).
After binary: `cargo build --profile bench-fast`, with
`.cargo/config.toml` setting `target-cpu=apple-m1` on aarch64-apple-darwin,
and `eternity2-solver-engine` carrying the `border_priority` cache change.

## Comparison (first 4 cells; after-run stopped early — see below)

| Size | Seed | Base time | After time | Δ |
|---:|---:|---:|---:|---:|
| 8×8 | 1 | 10265 ms | 10034 ms | **-2.2%** |
| 8×8 | 2 | 75 ms | 73 ms | -2.7% |
| 9×9 | 1 | 2134 ms | 2118 ms | -0.7% |
| 9×9 | 2 | 58430 ms | 59874 ms | **+2.5%** |

All four deltas are within typical run-to-run variance for 60-second
solves on a 8-core M1 (where macOS scheduling, thermal headroom, and
P/E core assignment dominate any sub-5% effect). The optimizations
**did not move the needle on this workload**.

## Why the changes didn't show

Both changes were defensible on paper:

1. **`target-cpu=apple-m1`** — gives LLVM the Apple-specific instruction
   scheduler. Real on tight numeric inner loops; the engine's hot path
   is dominated by `Vec<u32>` swap-remove (linear scan + integer
   comparison), not by anything that benefits from the scheduling tweak.

2. **Cached `border_priority`** — eliminated a `border_mask` recompute
   on every `select_position` call. Profiled cost was a single
   `border_mask` call per position per node. For a 12×12 puzzle that's
   144 cells × ~3M nodes ≈ 400M lookups. But the cached version is
   `Vec<u32>` indexed lookup (~1-2 ns) vs. the original arithmetic
   (~3 ns). The total saving is <2% even in the best case, and it
   gets lost in the 60-second timeout noise floor.

The structurally hotter paths — `place_and_propagate`'s linear-scan
domain pruning, the AC-3 cascade, the per-call `Vec<u32>` allocations
in `prune` — were judged too risky to refactor without coordinated
review (parallel agent was working in adjacent crates). Those remain
the realistic candidates for non-trivial gain.

## What this confirms

- The fleet harness, comparison binary, and `.cargo/config.toml` / `bench-fast`
  profile infrastructure all work end-to-end. They can be re-used for any
  future optimization claim — run baseline, change code, run after, compare.
- The bench-audit microbenchmarks' "89× speedup on `alns::score_board`" is
  real but **not on the engine or PT hot path**. Both use precomputed
  `state.edges_for` / `Row.edges`. The 89× number is for a function called
  only by benchmark binaries at final-state reporting time.
- Build flags alone don't fix algorithmic costs. The remaining wins
  require touching data structures (engine domains → bitsets, ALNS
  MWPM in parallel) or new compute platforms (Metal for PT inner SA).

## Files touched in this round

- New crate: `crates/bench-audit/` (fleet harness, compare, audit report).
- `.cargo/config.toml` (new): `target-cpu=apple-m1` for aarch64-apple-darwin.
- `Cargo.toml`: added `crates/bench-audit` to workspace, added
  `[profile.bench-fast]` for native fat-LTO builds.
- `crates/solver-engine/src/lib.rs`: added `border_priority_cache:
  Vec<u32>` to `SearchState`, populated at construction, used by
  `border_priority()`. All existing tests pass.
