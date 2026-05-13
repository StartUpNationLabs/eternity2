---
tags: [concept, do-not-revisit, refuted]
status: refuted
origin-vol: 11
---

# Refuted approaches (do not revisit without fresh evidence)

**Status**: `refuted` (vol-11 verdict, periodically reconfirmed)
**Origin**: 2026-05-11 night session, 3 independent cross-domain agents
**Files**: memory `project_e2_dead_ends`

## Three approaches ruled non-viable

### 1. Survey Propagation (Mézard-Parisi-Zecchina)

- Theoretical block: cavity-method assumes locally-tree-like; E2 is 2D grid with short cycles in every 2×2.
- Empirical analog: Edwards-Anderson spin glass on 2D/3D, SP famously fails.
- Zero published successes on Latin squares, sudoku, jigsaw, any structured combinatorial puzzle.
- With 5 hints E2 is below rigidity threshold → SP degenerates to BP → uniform surveys.
- **Vol-11 measurement confirmed**: lower m flattens marginals, not sharpens. Reversed from random k-SAT.

See [[survey-propagation]].

### 2. IsingFormer / Transformer-augmented PT (arXiv:2509.23043)

Three structural obstacles for E2:
- Tokenization explosion (256 pieces × 4 rotations vs binary spins).
- E2 wants a measure-zero ground state, not a Boltzmann distribution.
- Training data must come from PT itself → model learns to reproduce plateau states rather than escape them.

**Honest expert read**: every learned-proposal MCMC paper of the last 5 years (normalizing flows, GFlowNets, GFACS) shows the same pattern — nice on synthetic problems, no penetration into engineered combinatorial-search community.

The 2-4 weeks + $50-150 GPU build doesn't address the **structural universal-mismatch lever** — that's a destroy/region problem, not a smarter Metropolis proposal.

### 3. GPU/FPGA/Quantum SAT acceleration

- AWS F1 FPGA: no canned SAT bitstream, 2-6 weeks dev.
- D-Wave: would need >100k qubits via minor-embedding; benchmarked at this scale no advantage over classical (Nature Sci. Rep. 2025).
- ParaFROST GPU SAT: 2-5× on industrial CDCL, sometimes slower; pure SAT not MaxSAT.
- p-bit / Ising-machine hardware: no commercial cloud endpoint.
- "CryptoMiniSat-GPU" doesn't exist as a product.

**EvalMaxSAT not finding `o` lines is an encoding/symmetry problem, not a FLOPs problem.** Throwing compute at the same algorithm scales wall-clock by a constant.

## The ONE serious "more compute" path

**Mallob/MallobSat on AWS** (SAT Comp Cloud Track 5× gold medalist, ~$50 for 8h on c7i fleet). Bottleneck is encoding strength + portfolio diversification, NOT clock speed. Reserved for a separate budgeted day.

## How to apply

**Do not propose these for E2** unless someone has fresh evidence:
- A new SP variant for grid-structured factor graphs.
- A learned-proposal paper that demonstrably escapes plateaus (not just samples them).
- A quantum/ising hardware demo at 100k+ qubits with classical benchmark advantage.

## Linked concepts

- [[bp-marginals]], [[survey-propagation]] — empirical confirmation
- [[boundary-mps]] — adjacent cross-domain refutation

## Linked memory

- `project_e2_dead_ends`
