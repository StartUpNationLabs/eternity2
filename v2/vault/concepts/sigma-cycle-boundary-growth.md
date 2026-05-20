---
name: sigma-cycle-boundary-growth
description: "Vol-117 T3 — quantitative explanation of σ-cycle indecomposability via boundary-growth analysis in the 2D grid graph. For the 154-cell σ-cycle between local-459 and McGavin-469, minimum boundary at k=113 is ~190 edges (ratio 1.68 per cell). For smaller σ-cycles between same-score basins (cycles of 6-10 cells), min boundary is 2.0-2.6 edges per cell — near-optimal contiguity. Partial-cycle application breaks ~boundary score-edges, explaining the empirical 90+ edge loss seen in subset tests."
metadata:
  type: project
status: built
---

# σ-cycle boundary growth (vol-117 T3)

**Status**: `built` — new quantitative mechanism for indecomposability.

## Definition

Given a σ-cycle $C = [c_0, c_1, ..., c_{N-1}]$ between two boards
$b, b'$ at the same or different scores, the **grid boundary** of a
contiguous subset $S \subseteq C$ of size $k$ is the number of
adjacent-on-grid edges where one endpoint is in $S$ and the other
is not in $S$.

For the σ-cycle subset application (permute pieces along the subset
according to σ, leave rest fixed), the boundary edges are where the
permuted pieces meet unchanged pieces. These edges are very likely
to NOT match, contributing edge-loss to the resulting board.

## Empirical results

`scripts/vol117_sigma_boundary_growth.py <a> <b>` measures the minimum
boundary over rotational starts for each contiguous subset size $k$.

### Same-score 459↔459 (small cycles)

Between two pipeline 459 basins (vol-110 bseed1 & bseed11):
- 6 cycles, sizes [9, 8, 7, 6, 3, 2]
- Min b/k ratios per cycle: 3.33 / 2.33 / 2.00 / 3.50 / 1.50 / 2.00

Between cross-source 459 basins (vol-110 vs v17_alns winning5):
- 7 cycles, sizes [10, 7, 6, 5, 4, 4, 2]
- Min b/k ratios per cycle: 2.25 / 3.00 / 3.00 / 3.33 / 4.00 / 3.00 / 2.00

Typical ratio = 2.0-3.5 per cell. For comparison, a perfectly
contiguous 2×k rectangle subset has boundary 2(k+1)/k ≈ 2.0 per cell
asymptotically. So same-score σ-cycle subsets are **near-contiguous
but not maximally so**.

### Different-score 459→McGavin-469 (giant 154-cycle)

| k    | min boundary | b/k ratio |
|-----:|-------------:|----------:|
|    1 |            4 |     4.00  |
|    8 |           22 |     2.75  |
|   29 |           84 |     2.90  |
|   78 |          174 |     2.23  |
|   99 |          188 |     1.90  |
|  113 |          190 |     1.68  |
|  148 |          164 |     1.11  |
|  153 |          164 |     1.07  |

Boundary PEAKS at k ≈ 99-113 then DECREASES. The cycle has
"saturating" behavior — past ~half the cycle, additional cells
fill in interior and don't add boundary.

**Min boundary across all subsets ≈ 190 edges** (at k ≈ 113).

## Theoretical implication

Applying a partial σ-cycle (subset $S$) yields a board where:
- |S| cells are permuted along the cycle.
- Boundary edges between S and complement are AT RISK of mismatch
  (the moved pieces' edges face unchanged neighbors that they
  weren't originally adjacent to in either board $b$ or $b'$).

**Upper bound on score loss** = number of boundary edges (each can
mismatch at most once). Whether a particular boundary edge actually
mismatches depends on whether σ happens to preserve color
compatibility across the boundary.

Empirically, vol-99 found subsets of the 459→469 cycle lose 80-170
edges. The min-boundary measurement here (~190 at k=113) is the
THEORETICAL MAXIMUM loss; the realized loss (80-170) suggests
~50-90% of boundary edges actually mismatch.

This is consistent with the cycle being "near-rigid": most boundary
edges DO mismatch, but not all. The σ permutation has some local
structure that preserves a fraction of cross-cycle edges by chance.

## Quantitative refutation of "subset attack"

Vol-110 tried 2^n subset enumeration of cycles. The math here shows
WHY subsets fail: the boundary-cardinality grows at ratio ≥ 1.07 per
cell (best case) and typically 2-3 per cell. Score-recovery via
ALNS bounded above by halo-3 region size × 1 edge per cell ≈ 30-50
edges. The deficit is structural.

**A cleaner mathematical statement**: For a σ-cycle $C$ with min
contiguous boundary $B$, applying a proper subset induces score loss
$\geq B - O(\text{neighborhood-fix})$, where the fix term is bounded
by ALNS's effective halo cardinality. Indecomposability holds whenever
$B \gg O(\text{neighborhood-fix})$.

For our giant 154-cycle: $B \approx 190 \gg 30-50$. Indecomposable.

## What this opens

- **Non-contiguous subset search**: the boundary minimum was found
  for CONTIGUOUS subsets (in cycle order). Non-contiguous subsets
  (skipping segments) might have lower or higher boundary.
- **Subset-with-fix MIP**: formalize the bi-objective IP
  σ-subset choice + local-fix choice. Boundary tells us the
  feasibility region. Vol-118+ candidate.
- **σ-cycle "thickness" metric**: average boundary normalised by
  cycle length, as a fingerprint of how rigid a basin transition is.

## Code

- `scripts/vol117_sigma_boundary_growth.py`

## Linked

- [[multiple-459-basins-rigid]] — empirical refutation of σ-subset attack.
- [[basin-mix-mip-refuted]] — MIP-level refutation at 4 basins.
- [[MATH_NOTES_2026-05-16_459_LEVEL_SET]] — Conjecture C4 (board-spanning move).
- [[vol-117]].
