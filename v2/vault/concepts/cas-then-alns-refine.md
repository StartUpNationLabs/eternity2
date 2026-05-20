---
name: cas-then-alns-refine
description: Take CAS-greedy's 433/480 output (output/vol-74/casfullfixedsolution.json),
status: built
metadata:
  type: concept
---
# CAS-then-ALNS refine: 437-439 — vol-78b (2026-05-15)

**Status**: `built` (negative) — vol-78b.

## Test

Take CAS-greedy's 433/480 output (output/vol-74/cas_full_fixed_solution.json),
run standard ALNS (winning5, 2min, 4 seeds) on it.

## Results

| seed | final score | gain over CAS |
|---|---|---|
| 1 | 437 | +4 |
| 7 | 439 | +6 |
| 42 | 437 | +4 |
| 100 | 439 | +6 |

ALNS gains only +4 to +6 over CAS in 2min. Far below 459 standard pipeline.

## Why CAS-output is hard for ALNS to refine

CAS commits 256 pieces in a geometrically-constrained way:
- Outer 3 shells perfectly matched (252 matches)
- Inner 5 shells imperfect (~180 matches across 8 inner shells)

The piece-set is determined by CAS's MIP optima per shell. ALNS's
destroy-and-repair must move pieces ACROSS shells to find better
configurations, but each shell's pieces are individually optimal,
so cross-shell moves usually worsen score.

## Conclusion

CAS-output is a LOCAL OPTIMUM that ALNS can refine only slightly.
The constraint set baked into CAS prevents reaching 459-class.

This is the SAME pattern as McGavin-N-row-pinning experiments: any
upstream commit constrains downstream search.

The standard ALNS pipeline reaches 459 by avoiding commits — it
jointly evolves the entire board.

## Linked

- vault/concepts/cas-frame-final.md (CAS-only 430-436)
- vault/concepts/cas-hybrid-refutation.md (CAS-3 + ALNS 418)
- vault/concepts/cas-backtrack-results.md (vol-78 same-shell retry)
