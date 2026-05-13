# Session — vol-03

**Theme**: Edge-variable CSP formulation (Inversion-2); graph-theoretic reframings.
**Raw**: [[../sessions/archive/raw/RESEARCH_NOTES_3|RESEARCH_NOTES_3.md]]

## What was attempted

- New crate `crates/edge-solver/`: 480 interior edges as variables, domain {1..22}.
- Hall-1 alldiff propagator (necessary condition on edge-color matchings).
- Bipartite matching feasibility check.
- Four graph-theoretic reframings: 1-factor / bipartite compat / color adjacency / disagreement graph.
- Cross-pollination: edge-CP → seed cell-PT.

## What was measured / kept

- **Edge-coloring relaxation is LOOSE.** 480/480 achievable in 24s with no backtracks — edge-equality alone is solvable.
- **Piece-uniqueness is the binding rigidity.** Hall-1 alldiff filter recovers 335; matching-full recovers 303.
- Edge-CP seeded PT: **444-446** (3-5 edges behind cell-CP-seeded PT at 449).
- "Hamming moat" identified: depth-≥5 perturbations needed to escape plateaus.

## What was refuted

- **CHESS heuristic** with necessary-condition-only alldiff: not viable.
- **Houdayer-PT between same-border replicas**: zero improvement — same conclusion as vol-2 for same reason.
- **Color-strand-topology decomposition**: speculative; no concrete construction; deferred.

## Concepts touched

- [[edge-grid-dual]] (introduced; refined vol-21)
- [[ac3]] / [[gacolor]] (the cell-side comparison baseline)

## Implication for later vols

The vol-3 dual formulation didn't beat the primary, but the framing matured into [[relaxed-bound]] (vol-21): "what if piece-uniqueness were relaxed?" This is the same question vol-3 was asking; it took 18 volumes to find the right operationalization.

## Linked memory

- (vol-3 predates the memory system)
