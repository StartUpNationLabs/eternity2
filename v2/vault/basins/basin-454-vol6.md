---
tags: [basin, warm-record]
status: historic
score: 454
ceiling: ≥454
---

# Basin 454-vol6 (historic warm record)

**Score**: 454/480 — historic warm-PT record (still our all-time best)
**Bound** ([[relaxed-bound]]): 460 (gap +6 per vol-21 measurement of `winning5_sa_s1` family)
**Representative file**: `output/HISTORIC_first_454_1778567792.json`

## Discovery

Vol-6: `pt_e2 --pin-perimeter` starting from a 453-seed (vol-5 GA-cascade product) + corpus border `0xCAFEFEEF` family + GA-LARGE interior seed.

Byte-identical across 4 seeds (42, 9018, 18019, 27020). **Deterministic ceiling** for this basin under standard PT.

## Properties

- Mismatch hotspot: center-BOTTOM region (top-down scan-order, see [[mismatch-geometry]]).
- 26 mismatches in a 45-cell defect zone (vol-7).
- **[[inner-k-optimality]] proven**: defect zone is MaxSAT-locally-optimal for k = 3, 4, 5 (60s EvalMaxSAT minimal encoder). Full 45-cell zone: proven optimal in 83s.
- Operator-locked at any K ≤ 5 (vol-7 EvalMaxSAT extension implies it; vol-20 confirmed for 457).
- Vol-21 measurement: relaxed bound 460, gap +6 (saturation similar to our 457).

## What couldn't break it

- Vol-7: 11 attack vectors (z22-charge, Verhaard, chessboard parity, generator bias, cross-border GA, Houdayer within corpus, blank-interior PT). All zero-improvement.
- Vol-7 MaxSAT proof: 45-cell zone is the optimum.
- GA-LARGE cross-basin: failed (between-basin crossover is noise).

## Why it's still our warm record

- 12 volumes later, the 457 cold record beats 454 only by going to a **different basin** ([[basin-457-pt]]).
- No warm-start variant from any basin has exceeded 454 yet.
- The 442 plateau in [[basin-440-469]] (under hours of PT) is below 454.

## Sister basins

- [[basin-457-pt]] — vol-18 cold record from different scan order
- [[basin-440-469]] — vol-22 high-ceiling fresh basin
- [[basin-447-top-row]] — vol-17 cold record

## Linked concepts

- [[border-diversity]] — what produced the seed
- [[inner-k-optimality]] — what proves 454 locally optimal here
- [[parallel-tempering]] — `--pin-perimeter` flag that froze the border

## Linked memory

- `project_e2_state` (vol-6 row)
