# GRAIN — Polycrystalline E2 Search

**Status**: `built` (Vol-135 + 136, 2026-05-19)
**Origin**: Brainstorm reservoir round-3
**Files**:
- `scripts/v135_grain_poc.py`
- `scripts/v135_grain_to_alns.py`
- `scripts/v136_grain_60s.py`

## Algorithm

1. Drop $K$ seeds at random interior positions, each with a random
   interior piece + rotation.
2. Round-robin growth: each crystal picks best (piece, rotation) from
   shared inventory at one of its boundary cells, maximizing matched
   edges with the current crystal.
3. Continue until all cells covered or inventory exhausted.
4. Fallback: any leftover unmatched-class slot gets any valid piece.

## Measurements

### Single-pass GRAIN scaling (V135)

| Puzzle | GRAIN % | ALNS basic 60s % |
|--------|---------|------------------|
| 7×7/c5 | 72.6% | 97.6% |
| 10×10/c8 | 75.6% | 91.1% |
| 14×14/c12 | 77.5% | 81.6% |
| **canonical 16×16/22** | **77.1%** | 96.0% (best record) |

GRAIN scales UPWARD (72→78%), ALNS scales DOWN (97→81%). Crossing
near 14×14.

### GRAIN-vs-ALNS at canonical 60s budget (V136)

| Strategy | Score |
|----------|-------|
| GRAIN 60s (101 trials) | **373/480 (77.7%)** |
| GRAIN→ALNS 60s | 368/480 (76.7%) |
| ALNS baseline 60s (empty) | 359/480 (74.8%) |

**GRAIN alone beats ALNS baseline by 14 edges in same wallclock.**

### Plateau behavior

GRAIN at K=8 plateaus at 77.7% within the first ~5 trials. After 3.7s
of compute, additional trials don't help. The search space of (seed-
position, random-rotation, greedy-attachment) is small and quickly
saturated.

## Interpretation

GRAIN provides a strong constructive baseline that ALNS-from-empty
can't match in 60s. But GRAIN's plateau is real: greedy growth from
random seeds converges to a similar score across many runs.

The ALNS-degrades-GRAIN finding (370 → 368) suggests grain-boundary
defects are the residual: ALNS destroys the boundary, but the
destroyed pieces are no longer in the inventory pool of the original
crystals.

## What's still open

- Recrystallisation outer loop: only-destroy-grain-boundary, regrow
  with full inventory of those cells.
- $K$ sweep (4, 8, 16, 32 crystals).
- Hybrid GRAIN+SA inside ALNS: SA-fill empty cells, then GRAIN-
  reorder pieces in crystal patches.
- Multi-restart: 1000 GRAIN trials with stochastic attachment
  (random vs best-match).

## Linked

- [[concepts/filament-lk-2d]] (refuted as repair)
- [[concepts/scaling-curve-2026-05-19]]
- [[plans/EXTERNAL_BRAINSTORM_2026-05-18]]
