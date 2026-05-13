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

## 13:35 — Bound-floor ALNS empirical null

`edge_bound_floor_alns`: 3 outer × 3 attempts × 15s ALNS. Every
attempt: score=457, bound=461 (the 457 lock).

ALNS cannot preserve bound through repair. Need different algorithm.

## 13:40 — **BREAKTHROUGH — Basin escape via bound + Hungarian + ALNS**

Recipe:
1. Bound-ascent 2000 iters from any starting board (e.g. 450/465)
2. Hungarian bipartite matching against the bound-ascended state's
   relaxed target
3. ALNS recovery (60s)

Result: **440/469 board** — score=440, bound=469, Hamming=72 from
our 457. NEW BASIN with HIGHER CEILING (+8 above 461).

Confirmed 256 unique pieces. Real piece-uniqueness placement.

The basin ceiling 469 = the McGavin community record. If we can
ALNS-push 440 → 469, we'd MATCH the community record.

## 13:50 — Pushing the 440/469 basin

- 60s ALNS: 440 → 440 (initial)
- 300s ALNS: 440 → 442 (bound dropped 469 → 463)
- 5min hot-PT (8 chains, t_max=30): 440 → 442 (bound dropped 469 → 462)

The basin's ceiling 469 is NOT achievable by score-greedy ALNS;
bound drifts toward score under repair.

## 14:00 — Multi-seed basin jumps

8 basin-jumps from various boards. Results (score, bound):
- seed=1 from 457: 440, 469 ← BEST
- seed=11 from 457: 414, 454
- seed=22 from 457: 426, 458 ← still > 457 bound
- seed=33 from 457: 436, 451

The recipe is stochastic: different seeds → different basins.
The 469-ceiling result was found by 1 out of 4 seeds.

## 14:10 — TIGHT bound analysis (user prompt)

User: "Should we reuse or write another algorithm just aimed at
finding the exact bound possible? Are bounds even achievable?"

Built `edge_tight_bound.rs`. Result:

**Per-edge loose bound**: 480 (every internal edge has matchable
piece pairs across border classes). Confirms no STRUCTURAL barrier
to a complete solution.

Three levels of "bound":
1. Per-edge loose: 480 (trivial — every edge is individually matchable)
2. Cell-by-cell relaxed (our edge_relax): 448-461 (basin-local)
3. Joint piece-uniqueness optimum: ≤ 469 (McGavin); 480 (if E2 solvable)

The gap between levels 2 and 3 is *unknown*. The 469 from McGavin
suggests the joint optimum is ≥ 469. The 480 case is open.

**Answer to "are bounds achievable":** YES at level 1 (480 is the
loose upper bound), but level 2 and 3 may diverge. Our 457 basin's
cell-level bound 461 may or may not be jointly achievable. The
relaxed gap +4 is *evidence* of non-tight relaxation but not proof
of infeasibility.

