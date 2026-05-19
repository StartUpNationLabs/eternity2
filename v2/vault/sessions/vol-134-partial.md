# Vol-134 Partial Close (interrupted by user pivot 2026-05-19)

V134 FILAMENT-vs-SA head-to-head was running 36 ALNS jobs serially. User
pivoted away ~halfway. Partial median scores so far:

| Puzzle | SA median | FILAMENT median | Δ (FIL-SA) |
|--------|-----------|-----------------|------------|
| 6×6_c4 | 60 (100%) | 60 (100%) | 0 |
| 7×7_c5 | 82 (97.6%) | 79 (94.0%) | -3.6pp |
| 8×8_c6 | 106 (94.6%) | 105 (93.8%) | -0.8pp |
| 10×10_c8 | 166 (92.2%) | 159 (88.3%) | -3.9pp |
| 12×12_c10 | 226 (85.6%) | 230 (87.1%) | **+1.5pp** |
| 14×14_c12 | (not run) | (not run) | — |

**Tentative finding**: FILAMENT-repair LOSES at small sizes (6-10) but
slightly WINS at 12×12. Not enough data to claim significance, but
notable. The 14×14 result would clarify whether FILAMENT's advantage
GROWS with size.

Status: `partial`. User explicitly pivoted; do not re-run unless
specifically requested.

## Linked
- [[concepts/filament-lk-2d]]
- [[concepts/scaling-curve-2026-05-19]]
