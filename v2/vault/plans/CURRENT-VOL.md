# Current Volume — Vol-140

**Theme**: Wire INTAGLIO 2×2 feasibility into Rust ALNS as secondary
objective.

V138-139 found: 99.72% of random 2×2 piece-tuples are forbidden;
forbidden count anti-correlates with board score (109/60/29 across
LOW/MID/HIGH buckets).

## Binding items (3 max)

1. **Rust `count_forbidden_2x2`**: O(225) per board scan; in-board
   patches only.
2. **Lexicographic acceptance**: ALNS prefers (matched_edges,
   -forbidden_count) over just matched_edges.
3. **Benchmark**: ALNS+INTAGLIO vs vanilla on canonical 60s.

## Linked

- [[sessions/vol-140]]
- [[concepts/intaglio-forbidden-patterns]]
