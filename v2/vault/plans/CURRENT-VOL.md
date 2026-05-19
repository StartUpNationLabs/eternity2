# Current Volume — Vol-152

**Theme**: HARMONICS — Frequency-Domain Edge-Demand Matching.
A new invention proposed 2026-05-19 evening following V150-V151
WEAVING line of work hitting a ceiling at 455/480.

## Genesis

V150 (random sweep): 408/480 max.
V151 (beam-search K≤16384): 455/480 max, saturates.

Both V150/V151 work CELL-FIRST: for each cell, pick a piece. The
limitation: this ignores the GLOBAL matching structure across the
whole piece set.

V152 inverts: **match-first construction**. First decide which
piece-side pairs to MATCH (purely abstract pairings). Then embed
the resulting structure onto the 16×16 grid.

## The invention

Stage 1 — **Match Phase**:
The piece set has 1024 sides (256 × 4). Border (color 0) sides
must be at perimeter — 64 such sides on canonical. The remaining
960 interior sides must be partitioned into 480 matched pairs,
where each pair has the SAME color and the pair's two endpoints
are sides of DIFFERENT pieces.

Each color $c$ contributes $|c| = $ 24, 48, or 50 sides;
$|c|/2$ pairs of color $c$. Total pairs = $\sum_c |c|/2 = (5\cdot12 + 5\cdot24 + 12\cdot25) = 480$. ✓

Stage 1 picks an assignment $M$ of 480 same-color pairs. Many such
assignments exist; we want $M$'s induced piece-pairing graph
$G(M)$ — nodes = pieces, edges = (piece $p$, piece $q$) for each
pair (p.side_i, q.side_j) in $M$ — to be ISOMORPHIC to the 16×16
grid graph.

Stage 2 — **Embed Phase**:
Given $M$ and $G(M)$, find a bijection $\phi: \text{pieces} \to
\text{positions in 16×16}$ such that for every edge $(p, q) \in
G(M)$, the positions $\phi(p), \phi(q)$ are adjacent in the grid.
Furthermore, for each piece $p$, rotation $r_p$ must align so
that the four sides match their paired partners.

Stage 2 is graph-isomorphism (NP-hard) but **strongly constrained**:
$G(M)$ already has the right degree sequence (corners=2, edges=3,
interior=4) if $M$ was built consistently.

## Math

Define the demand graph $D$:
- Nodes: $\{(p, s) : p \in P, s \in \{N, E, S, W\}\}$, 1024 total.
- Edges: $((p, s_1), (q, s_2))$ if $\text{color}(p, s_1) = \text{color}(q, s_2)$
  and $p \neq q$.

A perfect interior matching $M$ partitions the 960 non-border nodes
of $D$ into 480 disjoint edges of $D$, with each matched pair same-color.

The induced piece-pairing graph $G(M)$ has vertex set $P$ and edge set
$\{(p, q) : (p, s_1) \sim_M (q, s_2)\}$. For $M$ to be realizable on a
16×16 grid, $G(M)$ must be isomorphic to the 16×16 grid graph (plus
border-perimeter edges going to "border" virtual nodes).

The 16×16 grid graph has 4 corner-degree-2 vertices, 56 edge-degree-3
vertices, 196 interior-degree-4 vertices. So $G(M)$ must have exactly
this degree sequence — easy to check post-matching.

**Necessary conditions on $M$ for grid-isomorphism**:
1. Degree sequence: corner-pieces × 2, edge-pieces × 3, interior × 4.
2. **No 3-cycles** (grid is bipartite). Trivial to check.
3. **4-cycle density** (grid has many 4-cycles around interior cells):
   $\binom{14}{1} \cdot 14 = 196$ interior 4-cycles. Check $G(M)$
   has at least this many.

These are NECESSARY but not sufficient. Sufficient is the full grid-iso
check.

## Binding items (3 max)

1. **Stage 1 PoC**: build maximum-weight matching $M$ on the demand
   graph. Use scipy.sparse + networkx, or hungarian-on-bipartite.
   Output: set of 480 pairs.
2. **Check necessary grid-iso conditions** (degree sequence, bipartite,
   4-cycle count) on the induced graph.
3. **Stage 2 PoC**: simple heuristic embed of $G(M)$ onto 16×16 (random
   start + swap improvement OR Knuth-style randomized greedy).

## Falsifiable claims

- Stage 1 ALWAYS produces a perfect matching (parity argument shows
  feasibility).
- The induced $G(M)$ satisfies degree sequence for SOME matching
  ordering. We want to enumerate matchings that satisfy this.
- Stage 2: at least ONE grid-iso exists for the SPECIFIC piece set
  (the puzzle has a solution, so SOME matching is grid-embeddable).
  Question: does the maximum-weight matching from Stage 1 lead to a
  grid-embeddable $G(M)$? Probably NOT — there are exponentially many
  matchings.
- **Therefore**: Stage 1 must enumerate matchings, not just compute one.
  This is the algorithm's complexity bottleneck.

## Kill-criteria

- If degree-sequence requirement is NEVER satisfied by max-weight
  matching, HARMONICS is structurally infeasible (Stage 1 dead).
- If Stage 2 embedding fails on a degree-correct $G(M)$, the matching
  picked an wrong topology.
- If end-to-end produces a board scoring < 380, HARMONICS is no
  better than WEAVING random sweep.

## Days budget

3-5 days. Day 1: Stage 1 implementation + degree-sequence check.
Day 2: Stage 2 heuristic embed. Day 3+: enumerate matchings + measure.

## Linked

- [[../sessions/vol-152]] (to create)
- [[../concepts/harmonics-matching]] (to create)
- [[../sessions/vol-151]] (parent: beam-search saturated at 455)
- [[INVENTION_NAMES_2026-05-19]]
