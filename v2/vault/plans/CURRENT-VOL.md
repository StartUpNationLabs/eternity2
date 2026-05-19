# Current Volume — Vol-141

**Theme**: TUNNEL — path-integral quantum annealing replacement for SA.

Standard SA crosses barriers by climbing — exponentially unlikely if
barriers are tall. QA "tunnels" — probability depends on barrier WIDTH
not HEIGHT. E2's basins (e.g. 461 plateau) are walled by tall-but-thin
barriers (sigma-cycle indecomposability says single moves degrade
score, but full transitions reach 469). Tunnel home turf.

## Implementation sketch

Path-integral QA: maintain $P$ replicas of the board (P=8 say).
Replicas are coupled by a transverse-field term $J$. Standard SA
update on each replica + an INTER-REPLICA correlation term that
makes replicas "want" the same state.

Schedule: start with high $J$ (replicas decorrelated) + high $T$
(thermal), anneal both toward zero. Tunneling happens when replicas
disagree on which side of a barrier they're on.

For E2: replicas are 256-cell boards. Update each replica with a
random ALNS-style swap, accept by (thermal + transverse) probability.

## Binding items (3 max)

1. **Rust replica stack**: maintain $P$ boards in parallel.
2. **Transverse coupling**: penalty for replicas disagreeing on
   piece-positions.
3. **Benchmark**: TUNNEL vs SA on canonical from empty + from 461.

## Linked

- [[sessions/vol-141]]
- [[plans/EXTERNAL_BRAINSTORM_2026-05-18]] (TUNNEL from round-4)
- [[concepts/intaglio-forbidden-patterns]] (informs cluster geometry)
