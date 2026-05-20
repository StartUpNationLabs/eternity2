---
name: intaglio-pruned-dfs
description: Post-placement 2×2 forbidden-patch check during DFS. At every placement,
status: refuted
metadata:
  type: concept
---
# INTAGLIO-pruned DFS

**Status**: `refuted` (Vol-147, 2026-05-19). Empirically verified on 24 boards × 5400 patches: 0 cases of `forbidden + full-edge-match`. Post-placement DFS pruner is vacuous on edge-strict DFS.

## Original idea (vacuous)

Post-placement 2×2 forbidden-patch check during DFS. At every placement,
check whether the partial 2×2 patch (the one just completed) is in the
forbidden-2×2 set.

## Why vacuous

The forbidden-2×2 theorem (V138-V142) tests: "given 4 piece IDs, does
ANY rotation assignment yield 4-internally-matching edges?"

In edge-strict DFS (like `vanilla_fast`):
- Every placement requires N color = previous-row S color, W color = previous-col E color.
- By the time a 2×2 patch is complete, all 4 internal edges match by construction.
- So **every completed 2×2 in a vanilla DFS partial is feasible**, by definition.
- The forbidden-2×2 check would NEVER fire post-placement.

The theorem's discriminatory power comes from *piece subsets*, not
edge-match — and the DFS already enforces edge-match strictly.

## Redesign: forward-check propagator (INTAGLIO-FC)

Place pos $p = (y, x)$. Consider the **as-yet-unplaced** 2×2 patches
that will eventually include $p$. Specifically, the patch with $p$ as
TL, where TR=(y, x+1), BL=(y+1, x), BR=(y+1, x+1) are all unplaced.

For each candidate piece $\pi$ for TR (i.e., currently in the bucket
for pos $(y, x+1)$ given N-W constraints), and for each candidate
$\pi'$ for BL, check: **does there exist a feasible 2×2 for (p, π, π',
*)** — i.e., is there ANY 4th piece (for BR) and ANY rotations such
that all 4 internal edges match?

If NO, $\pi$ for TR is a dead-end given $\pi'$ for BL (and vice versa).

**This is non-vacuous** because it propagates *information about the
piece subset already committed to* down to unplaced cells.

## Cost analysis

At depth d in canonical 16×16/22:
- Placed-pos $p$ has up to 1-4 future-2×2 patches involving it.
- For each future patch with 1 placed cell: candidates for the other 3
  cells = bucket sizes × $(N-d)$ remaining pieces. Too many to enumerate.
- For each future patch with 2 placed cells: candidates for the other 2
  cells = (bucket × remaining pieces). Still expensive.
- For each future patch with 3 placed cells: candidates for the 4th = 1
  bucket. **This is the cheap case.**

The 3-placed-1-unplaced case is **trivially the next row's first
unplaced cell** in row-major DFS. We get this check FOR FREE inside the
bucket-lookup machinery: bucket for next-cell already filters by
N-color and W-color of the two placed neighbors. So **the existing
bucket structure ALREADY does forward-check on the immediately-next
cell**. Nothing new to add.

## The actually-valuable propagator: 2-placed-2-unplaced

Consider the partial 2×2 with TL and BL placed, TR and BR unplaced.
TR's bucket requires N = TL.s and W = BL.e. BR's bucket requires N =
TR.s and W = BL.s.

The 2×2 is feasible iff **there exist $π_{TR}$ in bucket(N=TL.s,
W=fresh) and $π_{BR}$ in bucket(N=π_{TR}.s, W=BL.s) such that
$π_{TR} \ne π_{BL}, π_{TR} \ne π_{TL}, π_{BR} \ne π_{TR}, π_{BR} \ne
π_{BL}, π_{BR} \ne π_{TL}$.**

In column-major DFS, this state arises naturally between columns. In
row-major DFS, this state DOESN'T arise: BL is placed only AFTER TR
in row-major.

So **INTAGLIO-FC requires column-major or other scan order to be useful.**

## Verdict

Original vacuous; redesign requires changing DFS scan order. This is
a much larger surgery than V147's day-budget allows.

**Pivot.** The 2×2 theorem is right; the DFS integration is wrong.
Instead, use the forbidden-2×2 theorem as **piece-subset pruning** at
the *piece-supply level*: for each (color_pair × rotation_count)
budget, check feasibility against forbidden-piece-set bounds. This is
closer to an LP-side bound than a DFS pruner.

## What V147 actually does (revised binding)

Given the redesign, V147 pivots to measuring **how often the 4-tuple
of pieces currently placed at a 2×2 patch in real partial boards is in
the forbidden set**. This is the empirical sanity check that
post-placement check is indeed vacuous on edge-strict DFS — i.e., test
my reasoning above.

**Concrete experiment.**
1. Take 100 partial boards from `database-400-480/` at scores [440, 480].
2. For each complete 2×2 patch (15×15 = 225 patches per board), check
   `is_forbidden_2x2`.
3. Confirm: 0 forbidden patches in *complete* 2×2 patches of real
   edge-strict partials.

If confirmed (expected): document that V147 must be done via piece-supply
LP. If FALSIFIED (unexpected): real ALNS-final boards have edge mismatches,
so the patch-check WOULD fire. Then V147 day 2-3 proceeds as originally
planned but only against ALNS-init boards (not edge-strict DFS partials).

## Linked

- [[forbidden-patch-theorem-2026-05-19]]
- [[vol-147]]
- [[MULTI_VOL_PLAN_2026-05-19]]
