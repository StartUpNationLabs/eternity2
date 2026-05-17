---
name: vol122-pcls-poc-result
description: "Vol-122 J4 PCLS PoC. Per-color edge-LP with piece-supply caps gives identical UB=480 for McGavin border AND our 5 clean-slate borders. Supply-LP doesn't distinguish good vs bad borders."
metadata:
  type: project
---

# Vol-122 J4 — PCLS PoC (per-color edge-LP)

## Method

Edge-LP over the adjacencies of a partial board:
- `z_{a,k}` = LP-indicator that adjacency `a` carries color `k`.
- Per-adjacency: ∑_k z_{a,k} ≤ 1.
- **Per-color supply cap**: ∑_a z_{a,k} ≤ ⌊supply_k / 2⌋.

Supply_k = total edges of color k across:
- All free interior pieces, all 4 edges.
- All placed border pieces' INTERIOR-FACING edges (1 side per non-corner border cell; 0 for corners).

Solved with HiGHS via PuLP in 0.1s per border.

## Result

| Border type | Per-color SUM UB | LP-OPT | Border-border | Total UB |
|---|---|---|---|---|
| McGavin 469-host | 420 | 420.0 | 60 | **480** |
| vol-122 perm0_b0 | 420 | 420.0 | 60 | **480** |
| vol-122 perm1_b1 | 420 | 420.0 | 60 | **480** |
| vol-122 perm2_b2 | 420 | 420.0 | 60 | **480** |
| vol-122 perm3_b3 | 420 | 420.0 | 60 | **480** |
| vol-122 perm4_b4 | 420 | 420.0 | 60 | **480** |

**All 6 borders LP-UB = 480.** McGavin reaches 469 (gap 11); our clean-slate borders are LP-permitted to reach 480 too.

## Interpretation

The supply-LP is **TOO LOOSE** at the per-color level to distinguish "good" basins from "bad" ones. Per-color supply isn't the binding constraint — geometric / positional constraints are.

This means:
- PCLS as designed (LP-shadow-prices on per-color supply) **cannot guide basin discovery**, because shadow prices on the supply constraints are uniform across border types.
- A tighter LP that captures **per-cell-pair** color compatibility (vol-44 style) WOULD distinguish, but at much greater LP cost.

## What this rules out for J4 PCLS

The supply-LP version of PCLS is REFUTED as a discriminator. Future PCLS work must use the per-cell-pair LP (vol-44 ≤ 478, vol-122 B3 = 480 for perm0).

## What this proves about basin equivalence

A POSITIVE finding: all our clean-slate borders + McGavin's border are **LP-EQUIVALENT** at the supply level. This means combinatorially, all 5+ clean-slate borders should also admit 469+ boards — IF the geometric LP says so, AND the integer realization is achievable.

That motivates **B3** (per-border interior LP-UB with positional constraints) at scale. The supply-LP says "feasible"; B3 says "feasible at integer too?".

## Status

`refuted-as-discriminator` (supply-LP cannot rank borders). New direction: scale up B3 (already in flight for perm0; needs perm1-4 + per-cell-pair).

## Linked

- [[../sessions/vol-122]]
- [[../plans/INVENTIONS_BACKLOG]] — J4 status update
- [[inv3-border-dp-seed]] — A1 motivation
- [[inv-b4-hall-color-pair-refuted]] — sister supply-LP refutation
