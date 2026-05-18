---
name: v125-bbb-status
description: "Vol-125 T10 super-block BB&B: Day-1 init + Day-2 DFS skeleton built. AC-3 + hint propagation gets 17.5% reduction (127.6M → 105.3M blocks). DFS works but 13s/node due to snapshot/restore cloning 420MB per pin. Needs trail-based undo + bitset domains + incremental AC-3 for real performance."
metadata:
  type: project
---

# Super-block BB&B — vol-125 status

## What works (Day 1+2)

- Loads 64 super-cell W14 alphabets (127.6M blocks, 7.9s).
- Boundary-AC3 + hint-piece-uniqueness propagation to fixpoint (24s).
- Result: 127.6M → 105.3M blocks (17.5% reduction).
- Hint cells (1,1), (1,6), (4,3), (6,1), (6,6) retain small alphabets (5041, 5385, 5041, 5041, 5385 from enum — slightly different after AC-3).
- DFS with MRV variable order + snapshot/restore backtracking.
- Wipeout detection: propagation correctly identifies piece-uniqueness conflicts at depth 1-3.

## What's slow

- **Each DFS node takes ~13 seconds** because:
  - snapshot/restore clones the entire `domain` (Vec<Vec<Vec<u32>>>, ~420MB).
  - propagation re-runs the FULL AC-3 + uniqueness pass (27s for the init alone).
- Net: only ~30 nodes in 400 seconds. To explore the search tree meaningfully, we'd need 10000+ nodes.

## Day-3+ rewrite needed

For real search performance:

1. **Trail-based incremental undo.** Track each `domain[sr][sc]` change as a (cell, removed_indices) entry. On backtrack, restore from the trail.
2. **Bitset-packed domains.** Store `domain[sr][sc]` as a bitvec over the alphabet's block indices. Intersection becomes a bitwise AND.
3. **Incremental AC-3.** When cell A's domain shrinks, only re-check arcs A→neighbors. Don't re-scan all 64 cells.
4. **Per-piece occurrence index.** Maintain `piece_occ[p]` = Vec<(sr, sc, block_idx)> so piece-uniqueness propagation is O(occurrences) not O(64 cells × 1M blocks).
5. **Smarter value ordering.** Pre-rank candidates by some scoring (e.g., LCV — least-constraining-value via cardinality of constraint violations).

Estimated rewrite effort: 3-5 days of focused Rust.

## Empirical observation

The init AC-3+uniqueness reduction is only 17.5%. The piece-uniqueness propagation runs but doesn't fire much because at init, only 5 hint pieces are "used" → only ~12M blocks containing them are removed. The vast majority of pieces are still "free" so cross-cell uniqueness doesn't constrain.

The strong propagation should come AFTER pinning a non-hint cell — its 4 pieces become "used", which prunes more aggressively. This is what we observed: at depth-1, pin (7,7) → cascade hits wipeouts at depth-3.

So the propagation IS strong; the bottleneck is per-node overhead.

## Linked

- [[super-block-bbb]] (design)
- [[v125-cube-conquer-finding]] (related SAT exploration)
- [[../sessions/vol-125]]
