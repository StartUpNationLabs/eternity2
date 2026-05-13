---
tags: [concept, tensor-network, refuted]
status: refuted
origin-vol: 13
---

# Boundary MPS (tensor-network contraction)

**Status**: `refuted` (vol-13)
**Origin**: vol-13, Liang 2025 (arXiv:2503.17698) inspiration
**Files**: `scripts/v13_tensor_recon.py`, `scripts/v13_boundary_mps.py`, `scripts/v13_mps_marginals.py`

## Hypothesis

Treat the E2 factor graph as a tensor network. Contract row-by-row using MPS approximation with bond dimension χ. Get the partition function Z and marginals. Use as a globally-informed pruner or value-order.

## Setup (vol-13)

- Interior tile tensor: 784 nonzeros / 279,841 entries (0.28% dense, all distinct signatures).
- χ-truncated MPS sweep, χ ∈ {1, 4, 8, 16, 32, 64}.
- Boundary conditions encode the 4 corners + 5th canonical hint.

## Refutation: χ-sweep is paramagnetic

| χ | log Z (nats) |
|---:|---:|
| 1  | 213.69 (= BP) |
| 4  | 214.… |
| 8  | … |
| 16 | … |
| 32 | … |
| 64 | 216.72 |

Monotone increase, but **χ=1 (BP limit) is already paramagnetic**; higher χ doesn't fix it. Per-leg marginal entropy 4.087 bits at χ=4 (uniform over 17 of 22 colors). 52 frozen edges (perimeter BORDER + hint-adjacent), 300/512 edges near-uniform.

## The 10^101 overcounting gap

- MPS Z* ≈ 7×10⁹³ boundary-consistent colorings (sum over edge configurations consistent with the local matching constraints).
- True E2: ~10⁻⁸ expected solutions (≈1 actual solution, per McGavin's Brendan-complex-theory).
- **Overcounting ratio ≈ 10¹⁰¹**.

## Interpretation

Local matching constraints (edge-equality only) admit 10¹⁰¹× more colorings than respect piece-uniqueness. **The binding rigidity is global piece-uniqueness, not local matching.** Any local-message-passing method (BP, SP, MPS at any χ) is bounded by this gap.

→ Quantifies what [[bp-marginals]] showed qualitatively: cross-domain "approximate local marginals" methods are structurally insufficient for E2.

## Rare-color geography corollary (vol-13)

The χ-sweep produced as side effect the **rare-color geography** finding:
- 120 rare-color (colors 1-5) edges all live on the 60-piece border ring's INTERNAL matchings.
- 196 interior pieces have 0 rare edges.
- 56 edge pieces have 2 rare E/W each.
- 4 corners have 2 rare each.

This is a sharp Selby-Riordan generator design choice. See [[rare-color-rule]].

## Linked concepts

- [[bp-marginals]] — χ=1 limit
- [[survey-propagation]] — same theoretical block (cavity)
- [[rare-color-rule]] — the geography discovered en route

## Linked memory

- `project_e2_mps_relaxation_null`
- `project_e2_rare_color_geography`
