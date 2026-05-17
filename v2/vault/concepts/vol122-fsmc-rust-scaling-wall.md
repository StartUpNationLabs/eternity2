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
2. **Partial frontier hash** (TESTED): hash only LAST K frontier cells.
   On 10×10/c10 with K=10 or K=20, **NO CHANGE** in hit rate (0.64%)
   because piece-bitset still dominates the key.
3. **Frontier-only key (no piece-set)** (TESTED): on 10×10/c10 with
   K=5, hit rate JUMPED to **33.5%**. But the search now terminates
   at depth 74 vs 82 unmemoized — the cache is LOSSY (cuts off
   legitimate subtrees that share frontier-color signatures but have
   different remaining-piece sets).
   * **Not safe for proven-complete solving.**
   * Could be useful for **BASIN DISCOVERY** (find any partial with
     high score, doesn't matter if we miss other paths).
4. **Symmetric-equivalent state**: canonicalize the frontier mod
   rotations/reflections of the partial board. May increase hits.

## New direction (from these tests)

FSMC pure exhaustion-skip is **insufficient** for canonical-scale.

But the **frontier-only key** has a usable form:
- Replace "skip subtree as exhausted" with "skip subtree because best
  score from this frontier shape was X — only continue if we can beat
  X from the remaining pieces".
- This is **best-score-from-frontier memoization** for the MaxScore CSP.
- Wrong in subtle way: we cache score given a frontier shape, but
  different piece-sets can achieve different bests. Cache is LOWER
  BOUND only (best seen so far across visits with same frontier).
- For SEARCH RANKING: pessimistic cache lets us prune branches that
  can't improve over the cached lower bound.

This could be a new invention: **frontier-keyed score memoization for
MaxScore CSP** (rather than exhaustion-skip). Worth a follow-up.

## Status

- 5×5–8×8: **CONFIRMED WIN** (FSMC enables solving previously
  unsolvable instances).
- 10×10+: **SCALING WALL** — pure FSMC doesn't help.
- **Canonical 16×16/22c**: hit rate = **0.00%** after 11M states in 60s.
  Search reaches d203 vs d207 baseline = SLOWER and SHALLOWER. PIH
  ALSO has 0% hit rate at canonical scale. Even color-supply collisions
  are vanishingly rare because the supply space is too high-dimensional.
- Net assessment: **negative at canonical scale**. The IDEA is sound
  but cannot solve E2 directly. The 5×5–8×8 wins are publishable in
  their own right (a recipe for low-color jigsaw CSPs).

## Why no convergence at canonical

For canonical 16×16/22c, the color-supply vector has 22 dimensions,
each ranging 0..50+. State space ≈ 50^22 ≈ 10^37. With 11M states
visited, P(collision) ≈ 11M / 10^37 ≈ 0.

So PIH's compression of piece-bitset (256-dim) into color-supply (22-dim)
ISN'T ENOUGH at canonical. The remaining 22 dims are still too many.

Possible escape: **per-color-MOD-K hash** where supply is bucketed into
coarser bins (e.g., supply // 4). Trades correctness for collision rate.

## Linked

- [[vol122-fsmc-convergence-measured]] (Python PoC)
- [[../sessions/vol-122]]
- [[../plans/INVENTIONS_BACKLOG]] J6 entry
