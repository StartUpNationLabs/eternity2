# Vol-44 — Border classes + cluster-repair MIPs

**Theme**: Build LP-relaxation UB, identify border-classes, then test
local-optimality via MIP cluster repair.

**Status**: live. Real research-grade results in hand.

## Toolset

- `crates/bench-audit/src/border_ub.rs` — LP formulation lib.
- `crates/bench-audit/src/cluster_repair.rs` — MIP cluster repair lib
  (with x and y warmstart from current board).
- Bins:
  - `lp_smoke` — toolchain smoke test.
  - `border_lp_ub_small` — small-puzzle LP validation.
  - `border_lp_ub` — LP UB on any board.
  - `border_mip` — full MIP on a board's border (impractical at this scale).
  - `board_anatomy` — split score into B-B, B-I, I-I components.
  - `mismatch_map` — find mismatch clusters in a board.
  - `cluster_repair_458` — sequential cluster-repair on 458 board with
    optional halo extension.
  - `repair_region` — MIP on any user-specified region of cells.

## LP UB sweep (10 records, all canonical-E2 5-clue)

| Record | Score | LP UB | bb/60 | Class |
|---|---:|---:|---:|:---:|
| vol-32 458 vanilla_fast | 458 | **478.0** | 60 | A |
| vol-35 458 deep458 s5 | 458 | 478.0 | 60 | A |
| vol-32 456 blackwood_raw s2 | 456 | 478.0 | 60 | A |
| vol-39 455 diverse s1 | 455 | 478.0 | 60 | A |
| vol-39 455 diverse s5 | 455 | 478.0 | 60 | A |
| vol-36 454 make-canonical | 454 | 478.0 | 60 | A |
| vol-32 457 blackwood_mrv s7 | 457 | **477.0** | 60 | B |
| vol-32 457 blackwood_mrv s10 | 457 | 477.0 | 60 | B |
| vol-32 456 blackwood_raw s4 | 456 | 477.0 | 60 | B |
| vol-32 457 blackwood_mrv 30min s4 | 457 | **476.0** | 58 | C |

**Three border-classes** identified. Each ~20 below its LP ceiling.

## Class-A 458 board anatomy

(See [[458-class-A-mismatch-structure]] for full details.)

- B-B: 60/60 (perfect ring)
- B-I: 52/56 (4 unmatched)
- I-I: 346/364 (18 unmatched in 10 disjoint clusters)
- All I-I mismatches in rows 10-14 (bottom band). Top 9 rows perfect.

## Cluster-repair results

### Halo extension (single cluster per MIP)

| halo radius | max region size | total time | total delta |
|---:|---:|---:|---:|
| 0 (cluster only) | 5 | 0.1 s | **0** |
| 1 | 8 | 0.3 s | **0** |
| 2 | 16 | 2 s | **0** |
| 3 (≈30) | (too slow without warmstart) | aborted | (n/a) |

### Union of all 10 clusters (28 cells)

Single MIP on the union: 1.74 s, **delta = 0, OPTIMAL**.

### Bottom 7 interior rows (98 cells)

MIP running with x+y warmstart. BestSol=195 (current), BestBound=3017
(LP), 1700s budget remaining.

## Mathematical conclusions (so far)

> **Theorem (vol-44, empirical for vol-32 458 board)**:
> The vol-32 458 board's piece arrangement is the integer optimum
> under any rearrangement of *just* the 28 cells touching any I-I
> mismatch, with the other 228 placements held fixed. Proved by
> exact MIP (HiGHS B&B to optimality, 1.74 s).

This is strictly stronger than vol-22's K=5 operator-lock. We have
EXACTLY proven that 28 specific cells can't be rearranged to gain
even one matched edge.

## Open questions

- Is the **bottom 7 rows** (98 cells) also locally optimal? Running.
- Is the **bottom 9 rows** (126 cells) also locally optimal?
- What about cross-class movement (would class A's 458 do better with
  class B's bottom-band?) — requires building a "graft" experiment.
- LP dual analysis: which cells/pieces are bottlenecks? Untouched.

## Engineering finding (warmstart matters)

For >50-cell MIPs, HiGHS without warmstart spends minutes in
feasibility-jump without finding ANY integer feasible. With x+y
warmstart, HiGHS accepts the current board immediately and only
needs to test improvements. Always warmstart cluster-repair.

## Linked

- [[458-class-A-mismatch-structure]] — anatomy concept page
- [[border-enum-lp-ub]] — LP math
- [[vol-43-reframing]] — pre-vol-44 plan analysis
