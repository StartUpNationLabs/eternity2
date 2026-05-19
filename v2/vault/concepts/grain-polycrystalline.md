

# GRAIN — Polycrystalline E2 Search

**Status**: `partial` (vol-135, 2026-05-19)
**Origin**: Brainstorm reservoir round-3 (Elser-style "grow from
seeds")
**Files**:
- `scripts/v135_grain_poc.py`
- `scripts/v135_grain_to_alns.py`

## Algorithm

1. Drop $K$ seeds at random interior positions, each with a random
   interior piece + random rotation.
2. Round-robin growth: each crystal attaches the best piece-rotation
   from shared inventory at one of its boundary cells. "Best" =
   maximize matched edges with current crystal.
3. Continue until inventory exhausted or all cells covered.
4. Score = total matched interior edges.

## V135 measurements

**Single-pass GRAIN on V131 generated suite + canonical** (3 seeds):

| Puzzle | GRAIN median % | ALNS basic 60s % |
|--------|----------------|------------------|
| 7×7/c5 | 72.6% | 97.6% |
| 10×10/c8 | 75.6% | 91.1% |
| 14×14/c12 | 77.5% | 81.6% |
| **canonical 16×16/22** | **77.1%** | 96.0% (best record) |

GRAIN scales UPWARD with size (72→78%) while ALNS-basic scales DOWN
(97→81%). At 14×14, ALNS only beats GRAIN by 4pp.

**GRAIN → ALNS pipeline on canonical 16×16/22 (10 GRAIN trials + 60s
ALNS)**:

| Pipeline | Score |
|----------|-------|
| GRAIN alone (best of 10 trials) | 370/480 (77.1%) |
| GRAIN → ALNS 60s | 368/480 (76.7%) |
| ALNS baseline 60s from empty | 359/480 (74.8%) |

**GRAIN→ALNS beats baseline ALNS by +9 edges at equal 60s budget.**

## Interpretation

GRAIN provides a STRONG starting point but ALNS slightly degrades
it (370 → 368). The +9 advantage over empty-start baseline is real
but small.

ALNS-degrades-GRAIN suggests crystallised regions have intra-crystal
cohesion but bad grain-boundary edges. ALNS destroys the grain
boundary, but the destroyed pieces don't fit better elsewhere.

## What's still open

- Recrystallisation outer loop (only-destroy-boundary).
- More GRAIN trials (100+).
- Longer ALNS budget (30 min).
- K sweep (4, 8, 16, 32 crystals).

## Linked

- [[concepts/filament-lk-2d]]
- [[concepts/scaling-curve-2026-05-19]]
- [[plans/EXTERNAL_BRAINSTORM_2026-05-18]]
