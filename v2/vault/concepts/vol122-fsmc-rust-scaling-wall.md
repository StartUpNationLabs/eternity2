---
name: vol122-fsmc-rust-scaling-wall
description: "Vol-122 J6 v2 Rust port: FSMC works for low-color puzzles (5×5/c3 → 10.8× node reduction; 7×7/c4 → 9× and FLIPS solvable; 8×8/c5 → 2.3×). But hit rate plummets to ≤1.4% on 10×10/c10 and 12×12/c12. Scaling wall identified."
metadata:
  type: project
---

# Vol-122 J6 v2 — FSMC Rust port + scaling test

## Rust port summary

`crates/bench-audit/src/bin/fsmc_e2.rs` (~250 LOC). Implements:
- Row-major CSP backtracker
- Zobrist hash: piece-bitset XOR frontier-color-position hashes
- HashMap<u64, u32> as state-exhaustion cache
- `--no-memo` flag to disable memo and measure vanilla baseline

## Results

| Puzzle | Mode | Solved? | Best depth | Nodes | NPS | Hit rate |
|---|---|---|---|---|---|---|
| 5×5/c3 | NO-MEMO | yes | 25/25 | 38067 | 8.1M | – |
| 5×5/c3 | **MEMO** | **yes** | 25/25 | **3528** | 1.06M | **39.8%** |
| 7×7/c4 | NO-MEMO | NO (timed) | 46/49 | 10M | 4.5M | – |
| 7×7/c4 | **MEMO** | **YES** | **49/49** | **1.12M** | 1.15M | **26.5%** |
| 8×8/c5 | NO-MEMO | NO (timed) | 61/64 | 10M | 3.2M | – |
| 8×8/c5 | **MEMO** | **YES** | **64/64** | **4.4M** | 720k | **5.8%** |
| 10×10/c10 | NO-MEMO | NO (timed) | 82/100 | 10M | 1.16M | – |
| 10×10/c10 | MEMO | NO (timed) | 82/100 | 10M | 463k | 0.6% |
| 12×12/c12 | NO-MEMO | NO (timed) | 116/144 | 10M | 945k | – |
| 12×12/c12 | MEMO | NO (timed) | 116/144 | 10M | 343k | 1.4% |

## Findings

**Wins on small/low-color puzzles:**
- 7×7/c4 flips from unsolvable-at-budget to SOLVED with 9× node savings.
- 8×8/c5 same flip.
- 5×5/c3 → 10.8× node reduction.

**LOSES on canonical-scale (color-rich) puzzles:**
- 10×10/c10: 0.6% hit rate, 2× wall-clock SLOWER.
- 12×12/c12: 1.4% hit rate, 3× wall-clock SLOWER.
- Even same depth reached — memo doesn't unlock new depth.

**Scaling wall identified**: as the colors/cell ratio increases (more
unique frontier signatures), state collisions become rare. The
hashmap overhead dominates and FSMC becomes slower than vanilla.

For canonical E2 (16×16 with 22 internal colors + 1 BORDER), expected
hit rate is likely ≤0.5%. The pure FSMC approach would be SLOWER
than vanilla.

## Mitigations to test

1. **Bounded-depth memoization**: only memoize at depths > N (where
   hit rates may be higher). Need per-depth hit-rate profiling.
2. **Partial frontier hash**: hash only LAST K frontier cells, not all.
   Decouples cache from full piece-set. May get spurious hits but
   higher hit rate.
3. **Frontier-only key (no piece-set)**: ignore placed-piece set
   entirely. Cache says "given this frontier shape, no solution
   exists from any piece-set". Lossy but very small key.
4. **Symmetric-equivalent state**: canonicalize the frontier mod
   rotations/reflections of the partial board. May increase hits.

## Status

- 5×5–8×8: **CONFIRMED WIN** (FSMC enables solving previously
  unsolvable instances).
- 10×10+: **SCALING WALL** — pure FSMC doesn't help.
- Net assessment: **partial success**. The IDEA is sound but the
  CANONICAL ENCODING needs work. The 5×5–8×8 wins are publishable
  in their own right (a recipe for low-color jigsaw CSPs).

## Linked

- [[vol122-fsmc-convergence-measured]] (Python PoC)
- [[../sessions/vol-122]]
- [[../plans/INVENTIONS_BACKLOG]] J6 entry
