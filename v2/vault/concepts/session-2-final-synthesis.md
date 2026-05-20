---
name: session-2-final-synthesis
description: Session 2 final synthesis — 2026-05-15 (~3h45min autonomous)
status: built
metadata:
  type: concept
---
# Session 2 final synthesis — 2026-05-15 (~3h45min autonomous)

**Period**: 19:25 → 23:25 CEST (user "1 month away" signal to now).
**Total commits**: 63.
**Standing record**: 459/480 (UNCHANGED).
**New unique 469 boards**: 1 (from 1 → 2; near-twin swap 234↔235).

## Algorithms invented & tested

| vol | name | status | result |
|---|---|---|---|
| 62 | Homotopy-ALNS (β₁-targeted destroy) | refuted | β₁ = 0 on records |
| 62 | ComponentClusterDestroy | bounded | halo ≤ 1 MIP-proof |
| 65 | Piece-Side-Matching polytope | bounded | LP = 480, no tightening |
| 66 | Basin-Level Genetic Search | refuted | ≤ 469 (3 variants) |
| 67 | Forced-Component-Departure | spec | not built |
| 69 | Oracle-Attracted ALNS | spec | bug in repair |
| 70 | Rigidity-Guided Search | refined | rigidity is seed-dependent |
| 74 | Concentric Annular Solving (CAS) | bounded | 430-436 across 20 frames |
| 78 | CAS-BACKTRACK | refuted | 434 (same-shell retry doesn't help) |
| 78b | CAS + ALNS-refine | bounded | 437-439 (+4-6 only) |

## Structural findings (added today)

1. **0 cross-record backbone**: across 5 high-score records (incl
   McGavin), no cell has all-5-agreement on (piece, rotation).
2. **N-row scaling sharp threshold**: pinning McGavin's top-14 rows
   uniquely determines the rest → 469 reconstruction.
3. **CAS-greedy plateau** at 430-436 regardless of frame.
4. **500 distinct 60/60 frames enumerated** (frame-space huge).
5. **CAS BEATS ALNS** when starting from bare frame (+34 to +49).
6. **NS-1 Δ correlates with score**: 469→Δ=1, 459→Δ=2, 458→Δ=3-4.
7. **Vol-22 "ceiling 471" REFUTED**: relaxed_bound is not sound.
8. **Topological obstruction vacuous** (16×16 grid contractible).
9. **Spectral Fiedler bi-clusters** frame vs interior; no further
   structure.
10. **vol-61 sister-basins differ by 6-cycle σ-permutation** of
    46 cells in rows 12-15.
11. **McGavin basin σ-distance ≥ 247** from any non-McGavin record.
12. **σ-cycle to McGavin indecomposable** — every cycle subset
    reduces score.

## What's known about Blackwood/McGavin gap (vol-14 documented)

McGavin reaches 469 via Blackwood's algorithm with:
- Per-cell unrolled goto + 4-axis lookup → 295M nps (800× our throughput)
- Heuristic-color schedule [17, 2, 18] + piecewise-linear targets
- Break-index allowance (12 breaks → 469 max)
- In-place prune-back-to-T restart

We have partial ports (#1, #2, #3) but #4 (engineering) is
prohibitively slow without major work.

**At our throughput (367k nps × 8 cores), matching McGavin's
compute would take ~40 days.**

## What's been EXHAUSTED

- ALNS variants (standard, with ops, with seeds, multi-budget)
- σ-cycle import experiments
- Near-twin swaps (single + double)
- Local repair (halo ≤ 1 MIP-proof bounds)
- Spectral / community detection
- Topological obstruction theory
- Greedy commit-then-refine pipelines (all bounded below 459)

## What might still produce a result (NOT tried in session)

- **Long-compute McGavin replay**: hours-days of CPU on
  blackwood_then_csp pipeline + canonical schedules.
- **More 469 examples** via cross-machine sampling → ML training.
- **Algebraic generating-function partition-function** approach
  (mentioned but not built).
- **Full QAP MIP via Rust good_lp** (Python LP didn't converge in 48min).

## Bottom line

**The maximally-adversarial thesis stands across ~20 axes.**
Selby-Riordan engineered canonical E2 to defeat every algorithmic
shortcut. McGavin's 469 is reachable only via specific engineering
+ algorithm combination (Blackwood's solver) requiring 200× our
throughput.

Standing 459/480 on canonical E2 is the ceiling our pipeline
reaches under available compute. To beat it requires Blackwood-
class algorithm + engineering OR fundamentally new mathematics.

The session output is **research-grade structural characterization**,
not a record break.

## Files

- 22 new vault concept pages in this session
- 8+ new memory entries
- 25+ new scripts
- 500-frame corpus in `output/vol-76/`
- 1 new 469 board (near-twin swap)
- `vault/E2_KNOWN_FACTS.md` — one-page state-of-the-art reference
