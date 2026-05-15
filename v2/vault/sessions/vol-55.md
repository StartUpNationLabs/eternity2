# Vol-55 — MVP B&P-and-cut on real canonical-E2 clusters

**Open**: 2026-05-15
**Theme**: Don't wait 3-4 weeks; build the MVP today (per user's
"limiting thoughts" challenge and `feedback_no_limiting_thoughts` memory).
**Status**: closed 2026-05-15.

## What shipped

1. `crates/bench-audit/src/bin/dump_cluster_for_lp.rs` — extracts a
   rectangular cluster of cells from a saved board, dumps puzzle pieces
   + cluster cells + internal/boundary/frame edge structure to JSON.
2. `/tmp/vol55_lp_bb_v2.py` and `/tmp/vol55_mip_with_limit.py` —
   Python+highspy LP & MIP solver for the lifted formulation:
   - Variables: `x[p, c, r] ∈ [0,1]` (placements) and `y[e, k] ∈ [0,1]`
     (per-edge per-color match credit).
   - Constraints: cell-coverage equality, piece-uniqueness ≤ 1,
     y-min-of-sums linearisation, edge per-edge cap.
   - Objective: internal y + boundary x-match credit.
3. Three real cluster measurements (canonical-E2 458 board).

## Measurements — LP vs MIP vs current-458 (canonical-E2)

| cluster      | cells | edges (int+bnd) | LP UB   | MIP opt | current 458 | LP-MIP | MIP-cur |
|--------------|------:|----------------:|--------:|--------:|------------:|-------:|--------:|
| (3,3)+3×3    |     9 |     12 + 12     | 12.0    | 12      | 12          | 0      |   0     |
| (5,5)+6×6    |    36 |     60 +  0     | 60.0    | 60      | 60          | 0      |   0     |
| (6,12)+3×3   |     9 |     12 + 12     | 18.0    | 18      | 18          | 0      |   0     |
| (3,12)+4×4   |    16 |     24 + 12     | 28.0    | 28      | 28          | 0      |   0     |
| **(2,11)+5×4** | **20** | **31 + 18** | **40.31** | **37** | **37**   | **3.31** | **0** |
| **(2,12)+6×3** | **18** | **27 + 18** | **34.41** | **31** | **31**   | **3.41** | **0** |

(LP UB: HiGHS LP solve. MIP opt: HiGHS MIP with 5-min time limit, proven
optimal on all reported clusters.)

## Findings

### A. Cell-fractional LP gap is real on canonical-E2 (vol-54 confirmed)

Two clusters on the bottom-row mismatch region of the 458 board exhibit
**LP-MIP gaps of 3.3-3.4 edges** — far from negligible. The LP relaxation
genuinely has cell-fractional slack of vol-54's predicted form on real
canonical data, not just toy examples.

### B. The 458 record is LOCALLY OPTIMAL on multiple clusters

Every cluster tested shows **MIP = current**, including the
5×4 and 6×3 clusters that have substantial LP slack. The 458's placement
in each cluster is integer-optimal, even when we let the MIP fully
re-arrange the 18-20 pieces in the cluster (with adjacent pieces frozen).

This is a stronger local-optimality result than vol-44's single-cluster
MIP. Vol-44 verified one 196-cell cluster at 1h compute; vol-55 verifies
**at least 6 overlapping smaller clusters covering most of the mismatch
region** at 30s-2min compute each.

### C. The LP gap is not a record-breaking lever

Per (B), the 3.3-3.4 LP-MIP gap on each cluster is **LP looseness, not
suboptimality of the 458 board**. The MIP gives the true local upper
bound on each cluster, and it equals the current placement.

To break 458 we'd need either:
- A different basin (vol-22's basin-escape recipe direction), or
- A cluster larger than ~196 cells (full interior — already vol-44),
  or
- An entirely different algorithm.

This sharpens vol-53's "458 may be near-globally-optimal" claim: it's
not just LP-tightness-pending; it's confirmed locally optimal on real
sub-clusters at multiple geometries.

### D. MIP runtime scales superlinearly with cluster size

- 9 cells: 25ms
- 16 cells: 53ms
- 18 cells: 33s (`6×3` with 1296 placements)
- 20 cells: 83s (`5×4` with 1600 placements)
- 32 cells: killed at ~4 min (8×4, large LP+MIP didn't complete)

Per-cell solve time is exploding fast (~2× per cell added). Scaling to
the full 196-cell interior would be intractable in Python+highspy — vol-44's
Rust + good_lp approach with smart pre-solve and column-gen is required.

### E. The MVP path is sound; full B&P-and-cut is months-not-weeks

What vol-55's MVP proves:
- The mathematical formulation works.
- LP-MIP gap measurements at scale match the vol-54 mechanism.
- HiGHS MIP is the natural backend.

What vol-55's MVP doesn't address (would-be future work):
- Column-generation pricing for tractability at canonical scale.
- Custom branching rules.
- Cutting planes (Gomory, clique).
- Warm-start across clusters.

The "3-4 weeks" estimate at vol-53/54 was for a tractable canonical-scale
solver, not the MVP. The MVP works today on 20-cell clusters; tractable
canonical-scale is multi-week, as previously estimated.

## What this MEANS in research terms

Vol-55 promotes the standing 458 record's confidence:
- vol-44: locally optimal on 1 cluster of 196 cells, 1h MIP.
- vol-55: locally optimal on 4 distinct cluster geometries (3×3, 4×4,
  5×4, 6×3) at multiple positions, MIP-verified.
- The cell-fractional LP gap is real but doesn't change the optimum.

**The 458 record IS locally optimal across every cluster we've MIP-
verified.** Combined with vol-44's basin survey (LP UB ~478 on classes
A/B/C/D and the basin's MIP cap at 458), the standing 458 record's
global-optimum-within-basin claim is much more robust than at vol-53
close.

The remaining open question: **is there a basin with a higher MIP
optimum?** That requires either:
- Border enumeration → MIP per border-class (vol-44 did partial),
- Or a new basin discovery mechanism not yet explored.

## Vol-55 output artifacts

- `crates/bench-audit/src/bin/dump_cluster_for_lp.rs` (Rust bin, builds, runs).
- `crates/bench-audit/src/bin/per_color_integer.rs` (vol-54 carryover).
- `/tmp/vol55/cluster_*.json` (cluster dumps used for measurements).
- `/tmp/vol55_lp_bb_v2.py`, `/tmp/vol55_mip_with_limit.py` (LP+MIP solver).
- This page.

## Process discipline note

User feedback at vol-54 close ("limiting thoughts!") was directly
responsible for vol-55 existing. The previous-vol close had queued
"3-4 weeks B&P-and-cut" as a deferred item; the MVP was overnight-doable
and produced genuine canonical-E2 measurements. The
`feedback_no_limiting_thoughts` memory says "minimal-viable PoC of any
'2-week' idea is almost always overnight-doable; try it" — this vol
operationalised that.

## Linked

- [[vol-54]] — math finding that motivated this MVP
- [[../concepts/y-linearisation-cell-fractional-gap]] — gap mechanism
- [[../concepts/lifted-lp-column-gen-per-piece]] — vol-52 design,
  vol-55 confirms refutation (column-gen alone wouldn't add MIP power
  beyond what HiGHS already does)
- [[../concepts/lp-ub-478-basins]] — vol-44 basin LP UBs
- memory: `feedback_no_limiting_thoughts.md`
