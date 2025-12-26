# Solver V3 - Dancing Links (Future Work)

## Status: TODO

This directory is reserved for a future Dancing Links (DLX) implementation of the Eternity II solver.

## Plan

Copy and convert solver_v2 to use Knuth's Algorithm X with Dancing Links data structure for exact cover problem solving.

### Why Dancing Links?

1. **O(1) removal and restoration** - Doubly-linked list pointer manipulation
2. **No backtracking state management** - Inherent in data structure
3. **Proven performance** - "Choosing item with fewest options: 24 min → <1ms" (Knuth)
4. **Sparse matrix efficiency** - Ideal for constraint problems

### Eternity II as Exact Cover

- **Rows:** (piece P, position (x,y), rotation R) tuples
- **Columns:**
  - Piece P is used (256 columns)
  - Position (x,y) is filled (256 columns)
  - Edge constraint satisfied (variable)

### Resources

- [Dancing Links (Wikipedia)](https://en.wikipedia.org/wiki/Dancing_Links)
- [Knuth's Algorithm X](https://en.wikipedia.org/wiki/Knuth's_Algorithm_X)
- [Algorithm X in 30 lines](https://www.cs.mcgill.ca/~aassaf9/python/algorithm_x.html)
