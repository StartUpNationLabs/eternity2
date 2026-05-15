# Current vol — vol-45 (opening) — 2026-05-15

**Predecessor**: vol-44 closed with rich research output (8 findings,
14 tools) but no record break. See [[../sessions/vol-44]].

## Vol-44 summary (carried forward)

- LP UB tool ships. 3 border-classes identified (A 478, B 477, C 476).
- vol-32 458 basin is locally optimal under MIP at 28-cell rearrangement
  PROVEN exact. Locked under ALNS-diverse (24 seeds, vol-40), ALNS-mega_mix
  (8 seeds × 1h, vol-44), MIP cluster-repair (halo ≤ 2, vol-44), and
  196-cell whole-interior MIP (1h, no improvement, vol-44 final).
- 458 border is LP-UB locally maximal under k≤3 random perturbations
  (13/13 trials decrease UB).
- Combinatorial color UB = 480 (no parity waste); LP UB 478 captures
  spatial obstruction.
- McGavin 469 canonical-projected gives LP UB 477 < 478. McGavin's
  border is NOT a route past 458 on canonical 5-clue.

**Conclusion**: 458 is firm in this basin. Record break needs a
*different* basin (LP UB ≥ 479) or fundamentally different search.

## Vol-45 candidates (1 binding item per audit-at-open rule)

1. **CP search with LP UB objective**: build a CSP propagator that at
   each border placement step prunes by a partial-LP UB lower bound.
   Goal: directly generate borders with LP UB ≥ 479. Cost: ~2-3 days
   if LP at every CSP node is too slow; can use cheap proxies (color
   count, edge-supply Hall conditions). **Selected for vol-45.**

2. **Per-color LP UB diagnostic**: extend `border_ub.rs` to report
   sum(y) per color k. Identify which colors are LP-spatially-bottle-
   necked on class A. Cheap. Backup if (1) too big.

3. **Multi-trajectory CP exploration**: run CP with 16+ distinct
   value-order seeds, save partials, compute LP UB on each. Find
   basins with UB > 478. Cost: ~hours. Mid-effort alternative.

## Audit-at-open compliance

Aged unbuilt from BACKLOG:
- RL self-play (T1 vol-30) — `unbuilt`, since vol-30 (3 vols ago). 
  Multi-week build; not picking up vol-45. Status: deferred again
  with reason "vol-44 measurements suggest the 458 basin is too
  locally locked for value-order improvements to help; need basin-
  changing moves not value-order moves."

## Linked

- [[../sessions/vol-44]] — predecessor session
- [[../concepts/lp-ub-478-basins]]
- [[../concepts/458-class-A-mismatch-structure]]
- [[../concepts/color-multiset-bound]]
