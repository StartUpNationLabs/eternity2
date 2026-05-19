# ATLAS — Pattern-Database Heuristic

**Status**: `refuted` (Vol-128, 2026-05-19)
**Origin**: Brainstorm reservoir round-4
[[plans/EXTERNAL_BRAINSTORM_2026-05-18]]
**Files**:
- `scripts/v128_atlas_critique.py`

## Definition

Korf-style precomputed admissible heuristic. For each local $k$-cell
patch configuration ($k = 4-6$), store the minimum number of edge
corrections needed to make the patch consistent with *any* completion.

Online: $h(B) = \sum_{\text{patches } p} h(B[p])$ — an admissible
lower bound on total mismatches. Powers IDA*/A* with genuine pruning;
supercharges ALNS destroy-target selection.

## Why it works on Rubik's cube / 15-puzzle

On those puzzles, the objective is NON-ADDITIVE: total move count to
the goal is not a sum of per-tile distances. Pattern DBs encode the
*joint* cost of a multi-tile sub-configuration, yielding a stronger
lower bound than per-tile distances would.

## E2 measurement (V128)

The check: is E2's matched-edges objective additive per edge?

**Yes.** Each interior edge contributes independently to the matched
count. The per-edge upper bound is therefore:

$$
\text{UB}_{\text{per-edge}}(B) = \sum_{(i,j) \in E_{\text{int}}} \mathbb{1}[(i,j) \text{ feasible}]
$$

**On canonical E2**:
- 22 distinct interior colors.
- Every side ${N, E, S, W}$ has 22 distinct colors achievable via
  piece rotation across the 256-piece set.
- $\Rightarrow$ every potential interior edge is feasible.
- $\Rightarrow$ per-edge UB = 480 (the maximum possible).

The per-2×2-patch UB:
- Each 2×2 patch has 4 internal edges, each feasible. Max per-patch
  matches = 4.
- 225 patches × 4 = 900, but each internal edge belongs to 2 patches
  → overcount-corrected = 480.

Both UBs equal 480. **They convey no information beyond the trivial
"all 480 edges are potentially matchable".**

## Why ATLAS doesn't add value

The pattern DB is most useful when:
1. The objective is non-additive across the patch decomposition.
2. The patch has internal joint structure not captured by per-element
   lookup.

For E2:
- The objective IS additive per-edge.
- The "joint structure" is the piece-once constraint, which couples
  cells GLOBALLY (not just within a patch).

The right admissible heuristic for E2 is one that respects the
piece-once constraint. We already have these:

- `crates/bench-audit/src/border_lp_ub.rs`: LP relaxation upper bound.
  Tight integrality gap is the real issue; the LP isn't aware of piece
  rotation correlation.
- `crates/bench-audit/src/border_mip.rs`: integer MIP upper bound.
- Vol-55 cluster MIP: per-cluster MIP-tight upper bound.

These tools are **strictly stronger than any patch-DB** because they
encode the global piece-once constraint.

## Conclusion

ATLAS as a per-patch DB is **refuted on canonical E2**. The objective
is additive; existing LP/MIP tools provide stronger heuristics.

## What's still open

A different kind of "pattern database" might still apply:
- **Trajectory DB**: store the minimum number of operator steps (ALNS
  swaps, kicks) to reach a board with score ≥ T. This would be
  non-trivial because operator cost is non-additive.
- **Local-completion DB**: given a partial board, store the maximum
  score achievable by some completion. This is the LP-UB problem,
  already addressed by `border_lp_ub.rs`.

These are different concepts than Korf's static-state pattern DB.

## Vol-128 close

Per [[feedback_e2_one_invention_per_volume]]: vol-128 is ATLAS-only.
Status set to `refuted`. Vol-129 opens for the next invention.

## Linked

- [[plans/EXTERNAL_BRAINSTORM_2026-05-18]]
- [[concord-difference-map]]
- [[concretion-rigid-molecules]] (refuted)
- [[sessions/vol-128]]
- vol-13 `border_lp_ub.rs` and `border_mip.rs` (already-built
  stronger heuristics)
