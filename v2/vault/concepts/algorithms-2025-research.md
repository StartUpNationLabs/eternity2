---
name: algorithms-2025-research
description: "Vol-125 T38 deep research (2026-05-18): survey of LAP solvers, LNS variants, and E2-related algorithms in 2024-2025 literature. Identifies 8 algorithms NOT in our stack that are candidates for implementation, ranked by EV."
metadata:
  type: project
---

# Deep research: algorithms we could try beyond JV

Conducted 2026-05-18 in response to Reinout's JV suggestion. JV is implemented
(T37); microbench shows 1.1-1.5× speedup over Kuhn-Munkres on raw LAP, but
end-to-end ALNS is roughly equal (cost-matrix construction dominates).

This survey identifies algorithms beyond JV that ARE NOT in our stack.

## Algorithm landscape

### LAP-solver family

| Algorithm | Status in our stack | Speedup over KM | Notes |
|---|---|---|---|
| Kuhn-Munkres | ✓ via `pathfinding` | 1.0× baseline | current default |
| **Jonker-Volgenant (JV)** | ✓ T37 (`lsap` crate) | 1.1-1.5× microbench | drop-in done |
| **LAPMOD** | ✗ | ~10× at n>5000, sparse | for huge SPARSE matrices |
| **Auction algorithm** | ✗ | Parallel-friendly | natural for GPU |
| **GPU Hungarian** | ✗ | 100-1000× | needs CUDA, infeasible on macOS |
| **Sinkhorn (OT-regularized)** | ✗ | Polynomial → near-linear | APPROXIMATE only |
| **Deep Greedy Switching (DGS)** | ✗ | 1000× on GPU | sacrifices optimality |

### LNS / metaheuristic family

| Algorithm | Status | EV for E2 |
|---|---|---|
| ALNS basic | ✓ production | high — our 461 producer |
| **Neural LNS (NLNS)** | ✗ | medium — needs training data |
| **SPL-LNS (sampling-enhanced LNS)** | ✗ | medium — designed for ILP, not CSP |
| **Hyper-heuristic ALNS** | ✓ winning5 preset | similar to what we have |
| **AHGSLNS (adaptive hybrid genetic LNS)** | ✗ | low — different domain (VRP) |

### Cutting-edge SAT / CSP

| Algorithm | Status | EV |
|---|---|---|
| Kissat | ✓ via W-SAT pipeline | tested vol-123 |
| **AlphaMapleSAT (MCTS cube-and-conquer)** | ✗ | high — directly relevant |
| **Heule 2008 diamond encoding** | ✓ partial via W14 | could be extended |
| **Lazy Clause Generation (Chuffed)** | ✗ | high — designed for our problem class |
| **MaxSAT cluster repair** | ✓ vol-99 z3 | done |

### NEW: e2solver (December 2025, Weizmann Institute)

**Most directly relevant find.** Published 2025-12-31 by Shahar Seifer at
Weizmann. Combines:
- D-Wave quantum annealing
- Classical methods (Hungarian, SA, etc.)
- "AI method" (unspecified)

GitHub: https://github.com/Pr4Et/EdgeMatchingPuzzleSolver
Zenodo: https://zenodo.org/records/18109266

**Action**: clone the repo, inspect their methods, port the novel ones to
our Rust stack. Status: unbuilt.

## Top 5 invention paths (post-JV)

### T39: AlphaMapleSAT cube-and-conquer wrapper (HIGH EV)

- MCTS-based cube selection over our existing W-SAT CNF
- Adds learned guidance to the SAT-based approach
- Already noted as T70 in WALL_BREAKING_INVENTIONS.md
- Build: ~1 week. We have the CNF; need MCTS + kissat wrapper.

### T40: Lazy Clause Generation via Chuffed (HIGH EV)

- Chuffed combines SAT learning with CSP propagation
- Designed exactly for our problem class
- Available via MiniZinc backend
- Build: ~3 days. Write MiniZinc model, plug Chuffed.

### T41: Sinkhorn-regularized OT repair (MEDIUM EV)

- Replaces exact LAP with entropy-regularized Sinkhorn iterations
- Approximate but much faster on dense matrices (near-linear vs O(n³))
- Could enable LARGER free-sets (k > 128) in ALNS within budget
- Build: ~2 days. Pure Python prototype; Rust port if it helps.

### T42: Port e2solver (Seifer 2025) novel methods (MEDIUM EV)

- D-Wave hybrid: probably uses cluster decomposition similar to our vol-44 MIP
- "AI method": likely a learned heuristic for piece selection
- Worth inspecting their source code
- Build: ~1 week to port their best classical method.

### T43: Auction algorithm + GPU port (LOW EV ON MAC, HIGH IF CLUSTER)

- Naturally parallel; great for clusters
- We have no GPU; CPU implementation gives modest speedup over KM
- Save for if user moves to GPU machine

## What I've ruled out

- **Neural LNS (NLNS)**: requires training data we don't have; cold-start prediction may be worse than ALNS basic.
- **Polynomial chaos**: unrelated (stochastic ODE control, not combinatorial).
- **Quantum annealing direct**: D-Wave requires cloud subscription; ALSO Seifer 2025 used it already.
- **Sliced Wasserstein**: too approximate for our problem (we need exact assignment).

## The ONE thing nobody has tried

After this survey: **no published work uses iterative Hungarian-based bridge
between near-basins** the way we did in vol-125 T31-T32 (which found 9 new
460 basins). This is our novel contribution.

**Possible publication angle**: "Near-basin Hungarian bridging for edge-
matching puzzles" — would document our σ-cycle + iter-Hungarian method as
a new metaheuristic operator class.

## Sources

- LAP-solvers benchmark: https://github.com/berhane/LAP-solvers
- Heule 2008 SAT encoding: https://github.com/JamesGallicchio/eternity2
- Auction GPU survey: https://stanford.edu/~rezab/classes/cme323/S16/projects_reports/jin.pdf
- Sinkhorn-OT: https://dfdazac.github.io/sinkhorn.html
- AlphaMapleSAT: https://arxiv.org/abs/2401.13770
- SPL-LNS: https://arxiv.org/pdf/2508.16171
- e2solver 2025: https://zenodo.org/records/18109266
- Chuffed: https://github.com/chuffed/chuffed
- MILP/Max-Clique for E2: https://arxiv.org/abs/1709.00252
- Wikipedia E2: https://en.wikipedia.org/wiki/Eternity_II_puzzle
