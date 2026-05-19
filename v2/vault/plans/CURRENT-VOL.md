# Current Volume — Vol-138

**Theme**: INTAGLIO — carve forbidden patterns.

For each small k-cell subgrid configuration, check feasibility against
the canonical E2 piece set + constraints. Forbidden subgrids prune
where they would appear in board search.

Twin of CONCRETION (refuted, V127). CONCRETION found nothing forced;
INTAGLIO checks if anything is forbidden.

## Binding items (3 max)

1. **2-cell horiz/vert subgrid feasibility**: for each (piece_i, rot_i,
   piece_j, rot_j) pair adjacent on E or S, is it color-feasible?
2. **3-cell L-shape feasibility**: add a 3rd cell, check.
3. **Count forbidden patterns**: how many of N possible 2-cell, 3-cell
   configurations are impossible? Does it provide useful pruning?

## Linked

- [[sessions/vol-138]]
- [[concepts/concretion-rigid-molecules]] (twin, refuted)
- [[plans/EXTERNAL_BRAINSTORM_2026-05-18]]
