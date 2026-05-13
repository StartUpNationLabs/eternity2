---
tags: [concept, engineering]
status: built
origin-vol: 12
---

# Bitset domain rep

**Status**: `built` (vol-12, 7 steps shipped), iterated vol-16
**Origin**: vol-12
**Files**: `crates/solver-engine/src/lib.rs`

## Definition

Replace `Vec<Vec<u32>>` per-cell domains with `Vec<u64>` bitsets (one bit per (piece, rotation) candidate). AC-3 revision becomes a few SIMD-friendly word-ops instead of vector traversal.

## Empirical (vol-12)

- Single-thread ~2,150 nps stable on canonical E2 with `joe_depth150 + NS-1`.
- Multi-core (8-thread RootSplit) ~14k nps.
- Speedup over `Vec<Vec<u32>>` rep: **+48–101%** depending on propagator mix.
- The `t=150 + NS-1` profile: nps 959 → 1932 (+101%).

## Vol-16 follow-on wins

- Precomputed `same_piece_rots` LUT → +2.9× on `joe_depth150_par`.
- `score_board` O(n²) → O(n) via `Puzzle::piece` O(1) cache.
- Arena-based undo (vs `Vec<Undo>` per entry) → reduced allocator pressure.
- **BLACKWOOD_RAW: ~80k → ~367k nps single-thread** (4.6×). See [[engine-profile-registry]].

## Invariants enforced

- `domain_bits` mirrors `domain` exactly after every revision.
- Bit count equals domain length; debug-assert in `cfg(debug_assertions)` builds.
- Iterating set bits is O(popcount) per word.

## What's still open

- **NS-1 incremental update** (vol-12 was rebuild-each-step O(56)): incremental O(1) possible, not shipped.
- **SIMD piece-match table** (would close part of the gap to [[mcgavin-engine]]'s fit_table).

## Linked concepts

- [[ac3]], [[gacolor]] — propagators that benefit
- [[engine-profile-registry]] — profiles that include this
- [[mcgavin-engine]] — the next-level engineering target

## Linked memory

- `project_todo_engine_bitset` — DONE marker
- `project_e2_vol16_closeout`
