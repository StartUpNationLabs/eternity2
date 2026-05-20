---
name: mip-tightness-depends-on-defect-density
description: cluster_repair LP relaxation is informative ONLY when centered on defect cells. Random 80-cell interior block (vol-98) gives 1308% gap; defect-centric 64-cell (vol-86) gives 6% gap. Implications for MIP design.
metadata:
  type: project
status: built
---

# MIP LP-relaxation tightness depends on defect density (vol-98)

**Status**: `built` — measured 2026-05-16 ~03:31.

## Comparison

Two 80ish-cell MIPs on McGavin's 469:

| vol | region | cells | bin vars | current | dual | gap |
|----:|---|---:|---:|---:|---:|---:|
| 86 | top-4 rows (defect-dense) | 64 | 18.8k | 116 | 123 | **6.03%** |
| 84 | top-5 rows (mixed) | 80 | 28.7k | 144 | 2657 | 1745% |
| 98 | interior block rows 4-11 cols 4-13 (defect-free) | 80 | 28.8k | 174 | 2450 | **1308%** |

**Vol-86 has tight LP** (6% gap). Vols 84 and 98 have ridiculously
loose LPs (1308-1745% gap).

The defining difference: **defect-cell density**.
- Vol-86 top-4 contains ALL 16 McGavin defect cells in 64 cells = 25% defect.
- Vol-84 top-5 contains 16 defects in 80 cells = 20% defect, more loose halo.
- Vol-98 interior block 4-11 × 4-13 contains 0 defect cells (rows 4-11 are below McGavin's top-4 hard region).

When the MIP region contains NO mismatched edges, the LP
relaxation has tons of slack — it can fractionally satisfy every
constraint trivially. When the region contains mismatches, the LP
must trade off contributions and the relaxation tightens.

## Significance

- **Defect-centric MIPs are the right tool** for proving local
  optimality of records — the LP relaxation gives useful bounds.
- **Random-region MIPs are uninformative** on canonical E2 even
  for high-score records, because the LP relaxation is too loose.

## Strategic implication

Future MIP-bound work on canonical E2 should:
1. Always center on defect cells.
2. Expand halo carefully — too large a halo dilutes the LP
   tightness.
3. Don't waste compute on defect-free regions; they give no info.

## Why this surprises me a little

A priori I would have expected the LP relaxation to be similarly
loose for ANY 80-cell region. The fact that defect-centric MIPs
have 200× tighter relaxation is a non-trivial observation.

Possible explanation: cluster_repair's LP includes constraints
that pieces must come from the cluster's current contents. When
the cluster contains "leftover" defect-region pieces (poor color
profiles), the LP has more meaningful constraints. When the
cluster contains well-matching pieces, the LP can find many
fractional permutations that all satisfy constraints.

## Linked

- [[mcgavin-top4-mip-bounded]] (vol-86, the tight one)
- [[mcgavin-top5-mip-inconclusive]] (vol-84, loose)
