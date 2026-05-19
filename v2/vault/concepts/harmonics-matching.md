# HARMONICS — Edge-Demand Matching + Grid Embedding

**Status**: `refuted` 2026-05-19 (Vol-152, same day).
Match-first stage fails: perfect matching exists with right degree
sequence, but is NOT bipartite. Iterative odd-cycle removal does NOT
converge to bipartite in 200 iters. 8 candidate 2-colorings (random,
parity, color-class) all fail to admit a bipartite perfect matching
(best |M|=440 for pid-parity, still far from 480).

**Conclusion**: the bipartite-perfect-matching property of the demand
graph is so restrictive that ONLY the actual puzzle solution's
2-coloring works. Stage 1 (matching) cannot be solved without Stage 2
(layout) — the two stages are inseparable. HARMONICS as designed (a
priori match-then-embed) is infeasible.

See [[../plans/CURRENT-VOL]] for the design narrative and binding items.

## Why this is genuinely different

| Algorithm | Direction | What it picks first |
|-----------|-----------|---------------------|
| Vanilla DFS | cell-first | piece for each cell, in scan order |
| GRAIN | cell-first | piece for boundary cell, greedy |
| WEAVING (V150) | cell-first | piece for each cell, allow mismatch |
| WEAVING-Beam (V151) | cell-first | top-K piece-trajectories |
| **HARMONICS** | **match-first** | **480 piece-side pairings (no positions yet)** |

The conceptual move: **decouple matching from layout**.

## Why this is hard

The piece set has $24^5 + 48^5 + 50^{12}$-ish possible matchings
(astronomical). Most won't be grid-embeddable. Three filtering layers:

1. **Parity**: each color $c$ has $|c|$ sides, which must be even.
   $|c| \in \{24, 48, 50\}$ — all even ✓ for canonical E2.
2. **Degree sequence**: $G(M)$ must have 4 degree-2 + 56 degree-3
   + 196 degree-4 vertices for grid-iso.
3. **Bipartite + 4-cycle count + ... + full grid-iso**: increasingly
   strong necessary conditions.

The grid-iso step is NP-hard but well-studied; for the specific case
of "is this graph isomorphic to a 16×16 grid", linear-time algorithms
exist (Bondy-Murty, Babai 2016) IF the graph is in fact grid-iso. For
non-grid-iso, the algorithm rejects quickly.

## The crucial open question

**Does a max-weight matching of the demand graph yield a grid-embeddable $G(M)$?**

Probably not on the first attempt. We'll need to ENUMERATE matchings
that pass increasingly tight filters. The hope: max-weight matching
+ degree-sequence filter is a small fraction of all matchings, and the
fraction passing GRID-ISO is non-empty (because the puzzle HAS a
solution).

## Why this might find 480

Unlike cell-first construction, HARMONICS doesn't make
score-suboptimal local choices. Every pair in $M$ is a MATCHED edge
in any board realizing $M$. So if $|M| = 480$ (max possible), the
resulting board is a perfect 480.

The only ways HARMONICS doesn't find 480:
- Stage 1: max-weight matching has weight 480 but isn't unique;
  the one we get may not be grid-embeddable.
- Stage 2: grid-iso fails on the chosen $M$.

Both can be addressed by enumerating Stage 1 matchings.

## Linked

- [[../sessions/vol-152]]
- [[../plans/INVENTION_NAMES_2026-05-19]]
- [[weaving-beam]] (V151 parent; ceiling 455)
- [[k11-cross-domain-brainstorm]] (related: spectral piece-graph)
