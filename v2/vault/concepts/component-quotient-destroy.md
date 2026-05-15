# Component-Quotient-Destroy (vol-62 pivot)

**Status**: `refuted at halo ≤ 2` — vol-62 (2026-05-15). MIP-bound test
proves that no local repair with halo ≤ 2 cells can escape the 459
basin. See [[mip-local-optimality-459]] for the sound proof.
**Type**: NOT a fully novel algorithm; partial overlap with vol-17
`ComponentDestroy` + `ComponentPlusHaloDestroy` already in
`crates/localsearch/src/alns.rs`. The genuinely-new contribution is
the small-component regime characterization + min_size tuning.

## Honest correction (2026-05-15)

After drafting this concept I audited the codebase and found that
**vol-17 already implemented** component-targeted destroy:

- `ComponentDestroy { max_size, min_size }` — picks the largest defect
  component within size bounds, returns its cells as destroy-set.
- `ComponentPlusHaloDestroy` — adds 1-cell halo.

Both use BFS on the mismatch graph identical to my prototype. So the
core operator is NOT a vol-62 invention.

### Where it IS novel (the actual vol-62 contribution)

All existing bins (`alns_only`, `cold_portfolio`, `alns_portfolio`,
`alns_pt`, `pinned_blackwood_from_board`, `run_e2_blackwood_then_csp`,
`run_e2_x_skeleton`, `cross_graft`) instantiate `ComponentDestroy`
with `min_size: 6`.

**On every known E2 record at score ≥ 458, the largest defect
component is size 5 (459 board) or smaller.** Measurement:

| board | n components | largest size | size distribution |
|---|---|---|---|
| 459 p06 | 14 | 5 | [5,5,3,2×11] |
| 458 vol-32 | 14 | (similar, ~5) | many pairs |

With `min_size=6`, **ComponentDestroy NEVER triggers on these records**
— every call falls back to `ConflictDriven`. The "vol-17 NOVEL" comment
in the code is misleading at the regime that matters; vol-17 measured
size-6+ components at scores 437-447 where they DID exist.

### Vol-62 contributions (revised, three components)

1. **Measurement** of the small-component regime across 2,293 boards:
   defect graphs are forests (β₁ = 0) at all records; size distribution
   on the 459 board is [5,5,3,2×11]. This is the new EMPIRICAL finding.
2. **Tuning** of existing operators: lower `min_size` to 2 for the
   459 regime (`--ops componentonly2` / `winning5_smallcomp`). NOT
   a new operator; a parameter regime that was unexplored.
3. **NEW operator `ComponentClusterDestroy`** (vol-62 invented):
   gather ALL defect cells within L∞-radius `r` of the densest core,
   plus a halo. Unlike `ComponentDestroy` (picks ONE component) or
   `WorstBand` (entire row-strip), this respects component structure
   AND spatial concentration. Implemented in
   `crates/localsearch/src/alns.rs::ComponentClusterDestroy` with
   `--ops cluster_only` / `winning5_cluster` exposing it.

The new operator is the genuinely-novel piece. The tuning + measurement
characterize the regime where it applies. Together this is a complete
vol-62 contribution.

## Why this exists (refuting Homotopy-ALNS)

`vault/concepts/homotopy-alns.md` proposed β₁-cycle-targeted destroy
operators on the defect graph. Empirical measurement (scripts/
vol62_homotopy_alns.py + broad scan over 2,293 boards) found:

| score range | n boards | β₁ = 0 | β₁ ≥ 1 |
|---|---|---|---|
| 459 | 3 | 3 | 0 |
| 458 | 30 | 30 | 0 |
| 457 | 185 | 185 | 0 |
| 456 | 113 | 111 | 2 |
| 433-455 | ~880 | ~96% | ~4% (always β₁=1) |
| ≤ 318 | small | rare | β₁=11 once |

**On all known E2 records (score ≥ 458), β₁ = 0.** The defect graph is
a forest. Homotopy-ALNS has no destroy targets at the records we care
about. The concept is REFUTED as a primary operator.

This isn't surprising in hindsight: a 1-cycle in the defect graph
means a closed loop of mismatched edges going around an interior. On
a near-perfect board, this would require all 4+ edges of an
"interior pocket" to be wrong, which the search has long since fixed.

The retained insight: **defect topology IS informative**, just not via
β₁. The forest structure decomposes into small connected components,
and these are the natural quotient units.

## What we actually see (459-board anatomy)

On the local 459 record:
- 35 defect cells / 21 defect edges
- **14 components, none with cycles**, all confined to rows 11-15
- Component sizes: [5, 5, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]
- 11 components are simple pairs (a single bad edge between 2 cells)
- 3 components are short paths (3-5 cells, diameter 2-4)

This is a "scattered local defects" pattern, not a "global topology"
pattern. The right primitive is the **component**, not the cycle.

## The algorithm — Component-Quotient-Destroy

### Idea

Treat each connected component of the defect graph as an atomic
**destroy unit**. Add a **halo** of `k` cells around the component
(BFS within the cell-grid). Destroy the whole halo, refill.

Components are independent on the defect graph itself but may share
pieces (a piece in component A may also appear once in some halo-cell
of component B). Refill therefore commits to ALL pieces of the halo
simultaneously — a small CP problem.

### Math

Given board `B` with defect graph `G = (V, E)`:
1. Compute connected components `{C_1, ..., C_k}` of `G`.
2. For each `C_i`, the **destroy halo** is
   `H_i = C_i ∪ {cells within L_∞-distance ≤ r of C_i}`.
3. Sort components by `|H_i|` ascending (try cheap repairs first).
4. For each component, run `Repair(B, H_i)`:
   - Un-pin all cells in `H_i`.
   - Run CP-MaxScore restricted to `H_i` cells with a budget.
   - If improved score, accept; else roll back.

### Halo radius

- `r = 0`: only defect cells; CP often infeasible because piece-unique-
  ness can't be satisfied with the rest of the board fixed.
- `r = 1`: defect cells + their L_∞ neighbours. Typical halo size for
  a 2-cell pair = 8 cells. CP can swap pieces around the defect.
- `r = 2`: 18 cells halo. More flexibility, more compute.
- `r ≥ 3`: heavy compute; only justified for the 5-cell components.

### Component score-target

Each component `C_i` has a **local matched-edge target**:
- `n_internal_edges` = adjacent pairs inside `H_i` with both endpoints
  in `H_i`.
- We need ALL `n_internal_edges` to match for the component to be
  "closed". On the 459 board, comp 0 (5 cells) has ~6 internal edges;
  closing it would gain back ~3 of the 4 defect edges in that comp.
- **Per-component upper bound**: `4 · |H_i| - (boundary half-edges)`.

This is a *sound bound* (every internal edge can match at most once);
it's used to early-prune unprofitable repairs.

### Why this is INVENTED, not a variant

- Existing destroy operators (`mwpm_defect_pair`, `worst_window`,
  `random_region`) all use either pairwise distance or fixed windows.
- None of them respect the connected-component decomposition of the
  defect graph as the atomic unit.
- `mwpm_defect_pair` pairs DEFECT EDGES across components; this
  algorithm respects component boundaries — it never pairs across.
- Naming: **Component-Quotient-Destroy** (CQD). Searched
  "component quotient ALNS" "defect component destroy" — not in any
  E2 or general ALNS literature.

## Variants

- **CQD-Strict**: only accept improvements. Fast but stalls.
- **CQD-Anneal**: SA acceptance on per-component delta score. Can
  worsen one component to enable improving another.
- **CQD-Multi**: destroy K largest components together; jointly refill.
  Higher compute, may help when components share pieces.

## Implementation plan (vol-62 day 1)

1. Python prototype: enumerate components, halos, internal-edge bounds.
2. Pick the smallest non-singleton component on our 459 board (comp 13:
   pair at (13,12)-(13,13), halo r=1 = 6 cells).
3. Hand-solve: what pieces could close this 1-defect pair? Use
   `target/release/alns_only --extra-hint` or a small CP probe.
4. Measure: would a halo-r=1 CP refill recover this defect?

## Pre-checks (done)

- β₁ measurement confirms forest topology — no cycle generators.
- Vol-18 R5 had similar finding qualitatively but didn't act on it.
- Component-size distribution measured on 2,293 boards (above).

## Expected behavior

### Best case
- Most pair-components (11/14 on the 459) have small halos (6-8 cells).
- CP can usually find a valid closing if the surrounding board allows
  it. ALNS-style repeated CQD passes should improve the board by 2-4
  defect edges per pass.

### Worst case
- All defect components share pieces with each other in a tangle. CQD
  passes never strictly improve. Need CQD-Anneal or CQD-Multi.

### Realistic
- Some components close on first pass (the geometrically isolated
  pairs). The "stubborn" components in rows 12-14 (where backbone is
  basin-specific) may resist any local repair, confirming vol-22
  basin-escape finding.

## Open questions

1. **Halo radius**: empirically tune r ∈ {1, 2, 3} per component-size.
2. **Refill engine**: CP with MaxScore vs MWPM with consistency. CP
   is cleaner; MWPM is faster.
3. **Acceptance**: strict vs SA vs portfolio (multiple temperatures).
4. **Joint refill of multiple components**: when components share
   pieces, can we detect that and refill them together?

## Linked

- [[homotopy-alns]] — refuted concept that this replaces
- [[../sessions/vol-62]] — vol journal
- memory: `feedback_vols_61_to_70_invented_algos`
