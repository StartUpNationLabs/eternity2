---
tags: [concept, maxsat, optimality]
status: built
origin-vol: 6
---

# Inner-k optimality (EvalMaxSAT proof for sub-regions)

**Status**: `built` (vol-6, EvalMaxSAT-minimal encoder)
**Origin**: vol-6
**Files**: `crates/benchmark/src/bin/sat_e2.rs` (with `--free-cells` flag), MaxSAT WCNF encoder

## Definition

For a partial board B and a chosen sub-rectangle of `k×k` cells:
1. Pin every cell outside the sub-rectangle.
2. Free the sub-rectangle cells (any piece, any rotation).
3. Compile to **WCNF** (weighted CNF MaxSAT) preserving piece-uniqueness.
4. Run **EvalMaxSAT** (60s timeout typical).

If EvalMaxSAT proves optimal: the partial B is **locally optimal under the k×k sub-puzzle** — no rearrangement of those k² pieces beats the current score.

## Vol-6 / vol-7 results

| k | Status on canonical E2 |
|--:|---|
| 3 | proven optimal (vol-6, fast) |
| 4 | proven optimal |
| 5 | proven optimal |
| 6+ | **intractable in 60s** |

Vol-7 extension: **45-cell defect zone** of the 454 board proven MaxSAT-locally-optimal in **83 seconds** with the minimal encoder. 26 mismatches in that zone are the optimum.

## Vol-6 minimal-encoder win

15× WCNF size reduction over naive encoding by:
- Drop unit clauses for pinned cells.
- Drop alldiff clauses for pieces with full constraint already.
- Compile hint constraints into the goal weight.

This is what made the 45-cell EvalMaxSAT run feasible.

## Vol-7 z3 failure at scale

Vol-22 cluster repair tested z3 on 60-cell halo=0 cluster:
- z3 returned UNKNOWN in 180s.
- z3 returned UNKNOWN in 60s on halo=2 (62 cluster + 210 free, 76 MB WCNF).

→ EvalMaxSAT scales better than z3 on these instances; both are limited past ~50 cells. See [[exact-joint-bound]] for the unbuilt kissat-RC2 path.

## What this proves

Our 454 record is **locally optimal under ALL local moves up to 5-cycles** (vol-7 [[operator-lock]]) and **optimal in 45-cell sub-regions** (vol-7 MaxSAT). Improvements need:
- Larger cooperative moves (≥ 76-cell cycles per [[r5f-cooperativity]]).
- Different prefix (per [[prefix-determinism]]).
- Different algorithm class entirely.

## Linked concepts

- [[exact-joint-bound]] — extension to true global bound
- [[operator-lock]] — complementary K-move proof
- [[r5f-cooperativity]] — what bigger move sizes are needed

## Linked memory

- `project_e2_state` (vol-6, vol-7 rows)
