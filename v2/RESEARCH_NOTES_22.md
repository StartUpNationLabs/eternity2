# RESEARCH_NOTES_22.md — vol-22 working notes

**Date opened:** 2026-05-13 13:24
**Predecessor:** [[RESEARCH_NOTES_21.md]] + [[RESEARCH_NOTES_22_PLAN.md]]
**Mode:** Autonomous.

## Entry state

- Score ceiling: 457/480
- Our 457 basin's relaxed-bound: 461 (gap +4)
- Bound-ascent + ALNS empirically fails (proved vol-21)
- Vol-22 T1: bound-preserving ALNS

## Vol-22 strategic framing

The single biggest discovery of vol-21 was that **higher-bound basins
exist** but ALNS doesn't see bound and falls back to the 457 lock.

The fix is structural: ALNS acceptance must check `bound(candidate)` 
against a `bound_floor`. The candidate-rejection rate will be much
higher (since most ALNS moves don't preserve bound), so we need to
generate MORE candidates per accept.

Alternative framing: instead of modifying ALNS, modify the OBJECTIVE.
Make the optimization target `score + λ × bound` with λ > 0. Then
moves that decrease bound are accepted only when their score gain
outweighs the bound loss.

Both approaches will be tested.

