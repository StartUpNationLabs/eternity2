---
tags: [reference, community, performance]
source: groups.io eternity2 msg #3098 (2007-10-28, "Mike", re: Brute force does not work)
added: vol-219 (2026-06-12, user-directed)
---

# Mike's 2007 fast-backtracker recipe (msg #3098)

The foundational community post on fast E2 backtracking — 60-80M
tiles/s/core on a 2007 AMD X2 3800+ (~33 instructions/cell), at a
time when 35M/s was considered fast. **Lineage**: Mike #3098 (2007)
→ Peter McGavin's `genbody*` C generators (his current ~295M pp/s
single-core engines; shared with Joe in the 2026 pruning thread) →
the same architecture family as Bucas's libblackwood. Every fast
community engine and our own fast walkers converge on this design.

## The eight techniques, mapped to our stack

| # | Mike 2007 | Our implementation | Status |
|---|---|---|---|
| 1 | `LookupNW[n][w]` per-cell candidate lists; `LookupNEW` 3-side variant for E-border cells; `LookupNSW` for the cell above a hint | `vanilla_fast` buckets `pos*NW_KEYS+(n,w)` with per-pos border-side filtering (subsumes NW + NEW + all border variants); blackwood-fast same idea | HAVE (stronger: per-pos) |
| 2 | Fixed scan order; placing writes only S/E info forward | row-major `entry_s/entry_e` forward writes | HAVE |
| 3 | Procedurally generate monolithic loop-free code per cell (caveat: I-cache; ~66% on big working sets) | blackwood-fast `depth_dispatch_256!` proc-macro (vol-106, +25% → 79M PGO, opt-in `E2_BF_UNROLLED=1`); full libblackwood-style per-depth constant folding UNBUILT (BACKLOG `blackwood-fast-per-depth-unrolling`) | PARTIAL |
| 4 | Minimal state; reconstruct board for printing | packed u32 `chosen[]` entries, report-time reconstruction | HAVE |
| 5 | Pack 4 sides into one int → 1 load | `pack_entry(pid, rot, s, e)`; `tilesides[t_r]` ≡ our rot tables | HAVE |
| 6 | Keep temps in registers, commit late | LLVM + the vol-218 allocator lesson (3-pass retained buffers, 2.2×) | HAVE |
| 7 | Read the asm; pipeline flushes + L1 misses dominate | vol-106 T7 asm inspection (9 instr/cycle ceiling), PGO, vol-218 L2-thrash measurement (cost-index rejected) | HAVE |
| 8 | Dependency-free bookkeeping is free if scheduled right | masked deadline checks (`& 0x3FFFF`), NullSink inlining contract | HAVE |
| 1b | **`LookupNSW` for the cell ABOVE a mandatory hint** | mirror_gen clue-compat pre-filter (vol-218 catch #2). **vanilla_fast does NOT have it** — the d34/d135 clue wall cost 2/8 threads in the vol-217 stage-2 gen (each churned 85M pp/s at depth 34 for 20 min) | **ACTIONABLE** |

## What was new for us (vol-219 reading)

1. **The hint-neighbor pre-filter has 2007 provenance.** Our vol-218
   clue-compat pre-filter (mirror_gen) independently rediscovered
   Mike's `LookupNSW`. Port it to `vanilla_fast` (N- and W-neighbor
   cells of every forced cell restricted to candidates exposing the
   matching color, zero completeness loss): direct stage-2
   generation throughput win (~25% of threads currently die at the
   d34 wall), which is exactly the supply bottleneck after the
   vol-219 exhaustibility finding.
2. **"Empty buckets point at a shared zero-count entry to avoid
   null tests"** — micro-pattern we don't use (we use start==end);
   equivalent.
3. **His honest I-cache caveat on codegen** (~66% on big working
   sets) matches our vol-106 EV analysis of full unrolling — the
   remaining 2-4× single-thread gap to libblackwood is real but
   bounded by memory effects, and speed is a multiplier, not a
   wall-breaker (480-perspective: multipliers are the UNBOUGHT
   class).

## Linked

[[reference-community-e2-ceiling]], [[reference-blackwood-decoded]],
`docs/community-mining/05_Joe_pruning_method_thread.md` (the 2026
thread where McGavin re-surfaced #3098), BACKLOG
`blackwood-fast-per-depth-unrolling`, vol-218 clue-wall catch
([[vol-218]]).
