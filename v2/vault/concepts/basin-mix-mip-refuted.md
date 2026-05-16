---
name: basin-mix-mip-refuted
description: "Vol-112 T1 — MIP-PROVEN refutation. Given 4 distinct 459 basins, formulated an MIP picking one of the 4 basin assignments per cell, subject to piece-uniqueness, maximising matched edges. HiGHS-CBC solved to OPTIMAL = 459 in 16s. No mix of these 4 basins exceeds 459. Rigorous mathematical confirmation of vol-110/111 heuristic findings."
metadata:
  type: project
---

# Basin-mix MIP refuted (vol-112 T1)

**Status**: `refuted` — MIP-PROVEN optimum 2026-05-16 ~14:35.
**Origin**: vol-112 T1, math-research mode follow-up to vol-110 T2.b's
heuristic σ-cycle subset enumeration.

## The formulation

Given $N = 4$ distinct 459 basins each placing 256 pieces. For each
cell $c \in \{0, ..., 255\}$ and basin $b \in \{0, ..., 3\}$, the
assignment $(piece_b(c), rot_b(c))$ is known. Build:

$$\max \sum_{e \text{ adjacent}} y_e$$

subject to:
- $\sum_b x_{c,b} = 1 \quad \forall c$ (one basin per cell).
- $y_e \le x_{c_1, b_1}, y_e \le x_{c_2, b_2}, \quad \forall e = (c_1, c_2, b_1, b_2)$ where the edge between basin $b_1$ at $c_1$ and basin $b_2$ at $c_2$ matches.
- $\sum_{(c,b) : piece_b(c) = p} x_{c,b} \le 1 \quad \forall p$ (each piece appears at most once).

Variables: 1024 x-vars (256 cells × 4 basins), ~4500 y-vars
(matched-edge indicators), ~9700 constraints.

## Result

| solver  | objective | wall  |
|---------|----------:|------:|
| CBC MIP | **459**   |  17s  |

**Optimal solution = 459.** The MIP proved that no convex
combination of cell-level basin assignments (subject to
piece-uniqueness) exceeds 459. The optimal solution uses a MIX of
the 3 pipeline basins (basin 0 = vol-60 contributes 0 cells; basins
1/2/3 contribute 64/98/94 cells respectively, summing to 256).

The mix ITSELF is a 459 board — distinct from any single basin but
sharing their score. This is a **new way to construct 459 boards**
but not a way to exceed 459.

## Significance

- **Strengthens vol-110 T2.b's heuristic finding** (σ-cycle subset
  enumeration showed all 256 subsets ≤ 459) into a **MIP-proven
  optimum** over a broader space (any cell-wise mix).
- **Generalises vol-99 / vol-65 indecomposability**: not only do
  σ-cycle subsets fail to break 459, but ANY cell-wise mix of
  observed basin placements also fails.
- **Refutes Path B** ([[../MATH_NOTES_2026-05-16_459_LEVEL_SET]])
  for this 4-basin dataset.

## What this proves vs doesn't

**PROVES** for the 4-basin set $\{b_{60}, b_{orig}, b_{1}, b_{6}\}$:
$$\max_{x \in \{0,1\}^{1024}, \text{piece-unique}} s(x) = 459$$

**DOES NOT PROVE** general 459 ceiling: the proof is only over
mixes of these 4 specific basins. A different 459 basin (e.g., a
strict-canonical 5/5-hint 457 record) could conceivably combine
with these 4 to break 459 — but the cell-level choices are
restricted to the OBSERVED placements; novel placements aren't in
the MIP's search space.

## What might still work

- **Enlarge the basin corpus**: as more 459 basins are discovered,
  the cell-choice space grows, and the MIP optimum could move.
- **Allow non-basin placements at variable cells**: instead of
  restricting to observed (piece, rot), allow any (piece, rot) at
  the 24 fully-variable cells. This is essentially the vol-22 ALNS
  destroy-and-repair on those cells; ALNS already saturates at 459.
- **Lift to multi-row σ-orbits**: instead of mixing whole-cell
  basin assignments, mix at the σ-orbit level. The σ-cycle
  decomposition between two basins is a sequence of independent
  cycles; the orbit subgroup may have elements not corresponding
  to any single basin choice per cell.

## Script

`scripts/vol112_basin_mix_mip.py` — PuLP + CBC. Runs in ~17s on
apple-m1 for 4 basins. Scales linearly in N (number of basins).

## Linked

- [[multiple-459-basins-rigid]] — basin corpus.
- [[459-skeleton-and-variability]] — what cells vary across basins.
- [[../MATH_NOTES_2026-05-16_459_LEVEL_SET]] — Path B framing.
- [[../sessions/vol-112]].
