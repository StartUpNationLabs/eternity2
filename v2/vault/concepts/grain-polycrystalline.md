---
name: grain-polycrystalline
description: 1. Drop $K$ seeds at random interior positions with random interior
status: built
metadata:
  type: concept
---
# GRAIN — Polycrystalline E2 Search

**Status**: `built` (Vol-135 → 137, 2026-05-19)
**Origin**: Brainstorm reservoir round-3
**Files**:
- `scripts/v135_grain_poc.py`
- `scripts/v135_grain_to_alns.py`
- `scripts/v136_grain_60s.py`

## Algorithm

1. Drop $K$ seeds at random interior positions with random interior
   pieces + rotations.
2. Round-robin growth: each crystal attaches best (piece, rotation)
   from shared inventory at one of its boundary cells, maximizing
   matched edges.
3. Continue until all cells covered.
4. Fallback: any leftover slot gets any valid piece.

## Measurements

### Single-pass GRAIN scaling (V135)

| Puzzle | GRAIN % | ALNS basic 60s % |
|--------|---------|------------------|
| 7×7/c5 | 72.6% | 97.6% |
| 10×10/c8 | 75.6% | 91.1% |
| 14×14/c12 | 77.5% | 81.6% |
| canonical 16×16/22 | 77.1% | 96.0% (best record) |

GRAIN scales UPWARD with size; ALNS scales DOWN. Cross near 14×14.

### GRAIN-vs-ALNS 60s budget on canonical (V136)

| Strategy | Score |
|----------|-------|
| GRAIN 60s (101 trials, plateau at trial 6) | 373/480 (77.7%) |
| GRAIN→ALNS 60s | 368/480 (76.7%) ← buggy |
| ALNS baseline 60s | 359/480 (74.8%) |

GRAIN alone beat ALNS baseline by +14 at 60s.

### GRAIN→ALNS 30min on canonical (V137, after rotation bugfix)

| Strategy | Initial | Final | Δ |
|----------|---------|-------|---|
| **GRAIN→ALNS 30min** | 373 | **392/480 (81.7%)** | +19 |
| ALNS baseline 30min | 0 | 376/480 (78.3%) | +376 |

**GRAIN seeding gives +16 over empty-start ALNS at 30min budget.**

## Critical bugfix during V137

Original V137 (V135 unfixed) showed GRAIN seed loading at 141/480
instead of 370. Cause: Python `rotate_piece(p, r)` does CCW rotation
while Rust `Edges::rotated(r)` does CW. The same `r` index means
different rotations in each language. Fix: write
`r_rust = (4 - r_py) % 4` to placement JSON.

After fix: GRAIN's 373 in-memory ↔ 373 after JSON round-trip rescore.

## Where GRAIN sits in the landscape

- **vs ALNS-from-empty**: GRAIN seed helps (+9 at 60s, +16 at 30min).
- **vs state-of-the-art canonical pipeline (bf_bw + ALNS)**: GRAIN
  alone is far worse. Our 461 record needed the canonical-aware
  bf_bw partial as seed; GRAIN's random crystallization produces
  inferior seeds.
- **vs FILAMENT**: GRAIN constructs from scratch; FILAMENT polishes.
  Not directly comparable.

## What's still open

- $K$ sweep (4, 8, 16, 32 crystals).
- Recrystallisation outer loop (only-destroy-grain-boundary).
- GRAIN seeded by canonical hints (currently ignores them).
- Stochastic attachment (random rotation among top-K candidates).
- GRAIN at MUCH longer ALNS budget (2-4h) to see if asymptote
  surpasses the canonical pipeline.

## Linked

- [[concepts/filament-lk-2d]]
- [[concepts/scaling-curve-2026-05-19]]
- [[concepts/constraint-density-vs-alns-gap]]
- [[plans/EXTERNAL_BRAINSTORM_2026-05-18]]
