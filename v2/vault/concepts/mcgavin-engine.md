---
tags: [concept, community-engineering, throughput]
status: external-reference
origin-vol: 14
---

# McGavin engine (per-cell unrolled goto + fit_table)

**Status**: external community engine; we have not reimplemented
**Origin**: docs/community-mining/05_Joe_pruning_method_thread.md (vol-14 analysis)

## Definition

Peter McGavin's C backtracker (gcc -O6) with Joshua Blackwood's algorithm on top. Achieves **295M nodes/sec single-core**. Bucas's libblackwood C rewrite hits 2.3× over Blackwood's own Mono C# (originally 50M nps); L1 miss rate 0.09% (vs 0.33% C#).

## Why it's fast

- **Per-cell unrolled goto code**: each of the 256 cells gets its own emitted match-loop. No virtual dispatch, no propagator-trait overhead.
- **4-axis fit_table**: `(north_edge × 24 + 23) × 24 × 24 + west_edge → sorted (piece, rotation) list` precomputed offline. O(1) candidate lookup.
- **Memory locality**: hot tables in L1; piece domain represented as compact bit-fields.
- **Instruction-level parallelism**: the unrolling exposes parallelism to the CPU front-end.

It is **not algorithmic sophistication** — same DFS as everyone else. The win is pure cache + ILP engineering.

## Our throughput gap

| Stack | nps (single-core) | source |
|---|---:|---|
| McGavin C, -O6, fit_table | ~295,000,000 | community |
| Bucas libblackwood C, Python-generated unrolling | ~50M | community |
| Blackwood Mono C# | ~20M | community |
| Our `BLACKWOOD_RAW` post-vol-16 cleanup | ~367,000 | vol-16 measurement |
| Our `joe_depth150_bp_par` baseline | ~7,000 | vol-16 measurement |

We are **~800× slower** than McGavin (after vol-16 4.6× speedup); ~20,000× before cleanup. At our throughput, reaching Blackwood's 50B-iteration cap takes ~40 days wall-clock.

## What it would take to close

- **Per-cell unrolled match-loop**: codegen step in build.rs emitting 256 specialized DFS frames. Weeks of work.
- **4-axis fit_table propagator**: replace AC-3 + gacolor with O(1) lookup at the cost of unsoundness under break allowance. Already partially the case in [[blackwood-algorithm]] (BLACKWOOD_RAW).
- **SIMD piece matching**: 4 rotations × bit-packed edges fits in AVX2 lanes; could vectorize the candidate filter.

Per [[mcgavin-blackwood-gap-analysis]], this is **gap #4 (engineering)** of four orthogonal gaps to 469. Lowest priority until [[blackwood-algorithm]] + [[prune-restart]] (gaps #1–#3) land and demonstrate the algorithmic ceiling.

## Linked concepts

- [[blackwood-algorithm]] — the algorithm McGavin runs on this engine
- [[prune-restart]] — Joe's policy that McGavin runs *outside* the inner loop
- [[bitset-domain-rep]] — our analogue of the bit-packed domain rep, vol-12

## Linked memory

- `project_e2_mcgavin_blackwood_gap_analysis`
- `project_e2_vol16_closeout` — our 4.6× engine speedup
