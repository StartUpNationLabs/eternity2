# Vol-35 — color-ratio considerations for landscape mapping

**Date**: 2026-05-14 (vol-35 mid-vol).
**Status**: user-prompted (Q at 12:18) — does color ratio explain
the 6×6/5c rugged-no-structure result?

## Color/piece ratios

Canonical Eternity II: 256 pieces / 22 colors = **11.6 pieces/color**.

Previous probes:

| Size/colors | Pieces | Colors | Ratio | FDC r |
|---|---:|---:|---:|---:|
| 4×4/4c | 16 | 4 | 4.0 | -0.052 |
| 6×6/5c | 36 | 5 | 7.2 | -0.031 |
| 12×12/8c | 144 | 8 | 18.0 | -0.104 |
| 16×16/22c (canonical) | 256 | 22 | 11.6 | -0.068 |

The 6×6/5c (rugged) ratio is 7.2 — much CROWDED-er than canonical
(11.6). The 12×12/8c is OVER-loose (18). Neither matches canonical's
structural regime.

## Proportionally-scaled puzzles

To approximate canonical's 11.6 pieces/color ratio:

| Size | Pieces | Best colors | Ratio | Edges/color |
|---|---:|---:|---:|---:|
| 8×8/5c | 64 | 5 | 12.8 | 22.4 |
| 10×10/8c | 100 | 8 | 12.5 | 22.5 |

Both close to canonical's 11.6 pieces/color AND 21.8 edges/color.

## Experiment in flight

Vol-35 mid-vol: 100-restart ALNS landscape probes at 8×8/5c and
10×10/8c. Each running single-thread (won't compete much with the
ongoing thread-id sweep).

Hypothesis: if the 6×6/5c rugged result was a color-ratio artifact,
8×8/5c and 10×10/8c should show MORE FDC structure (closer to
canonical-class).

## Caveat: the right starting condition

The 6×6/5c probes used ALNS-FROM-RANDOM. But vol-34 T3's trimodal
Hamming at canonical 16×16 was on ALNS-FROM-CP-PARTIAL — a different
LO population.

At 8×8/5c the engine solves trivially (ms), so "deep partials" aren't
meaningful. The landscape question may have different answers at
small scales vs at canonical because the *meaningful starting
condition differs by scale*:
- 4×4/4c: brute-force enumeration is tractable; LOs are global+near-globals
- 6×6/5c: ALNS-from-random gives a sample; few partials are meaningful
- 8×8/5c: similar; partials are trivially completable
- 12×12/12c: harder; CP-partial regime emerges
- 16×16/22c (canonical): CP-partial regime is the right one

The proportional-color probes will give cleaner data but the
TRIMODAL landscape structure observed at 16×16 from ALNS-from-partial
may only be observable at canonical scale.

## Update — 8×8/5c result

**8×8/5c (100 restarts × 10s ALNS, single thread)**:
- Score range 86-98, mean 93.2, max 98 (87% of optimum)
- Mean Hamming = 63.5 / 64 (essentially max)
- All 100 LOs distinct (no clustering)
- **FDC r = 0.000** (literally zero correlation)

The "canonical-ratio" 8×8/5c has WORSE FDC than the off-ratio
6×6/5c (-0.031) or 12×12/8c (-0.104). The user's color-ratio
hypothesis is **REFUTED** as the explanation for the rugged
small-puzzle landscape.

Updated scaling table:

| Size | Pieces/Color | FDC r | Best/Max |
|---|---:|---:|---:|
| 4×4/4c | 4.0 | -0.052 | 100% |
| 6×6/5c | 7.2 | -0.031 | 90% |
| 8×8/5c | 12.8 | -0.000 | 87% |
| 12×12/8c | 18.0 | -0.104 | 84% |
| 16×16/22c (random) | 11.6 | -0.068 | 66% |

FDC isn't monotonic in color-ratio. The 12×12 happens to have
strongest structure (r=-0.104). Possibly the SIZE matters more
than ratio for whether ALNS-from-random finds basin structure.

## Implication

Random-init ALNS may simply be the wrong tool for finding
basin structure at any small scale. The trimodal Hamming we
observed in vol-34's T3 lottery (record-class LOs) is
*starting-condition-dependent*: ALNS-from-deep-CP-partial finds
basins; ALNS-from-random doesn't.

This is the bigger insight than color-ratio. To map structure
at canonical scale, we need to start from MANY different CP
partials (vol-35 T1 thread-id sweep) and let ALNS settle them
into per-basin attractors. NOT from random configurations.
