---
name: v125-bbb-progression
description: "Vol-125 T10 BB&B progression v1→v2→v3→v4. Final state: v3 fastest (0.3s/node), reaches depth 39-40 of 59 search-cells. 1M-node overnight run in flight to test whether 480 lies past depth 40."
metadata:
  type: project
status: built
---

# Super-block BB&B progression

## v1 (early commit, removed)
Snapshot/restore via Vec::clone — ~13s/node. Max depth 2.

## v2 (sparse-set + trail)
- SparseDomain: Vec<u32> + live counter; swap-remove O(1) finding via linear scan O(live).
- Trail-based undo: each removal pushes (sr,sc,prev_live), restored on backtrack.
- Sentinel entries for piece state, pinning.
- ~3s/node, max depth 34.

## v3 (incremental propagation + O(1) sparse-set)
- SparseDomain adds pos_of[block_idx] → O(1) remove.
- Incremental piece-uniqueness: after pin, iterate piece_occ[p] for each newly-used p, remove block-instances at other cells.
- Incremental boundary AC-3: only re-check pinned cell's 4 neighbors.
- ~0.3s/node, max depth 39. **10× faster, deeper search.**

## v4 (piece-live-count + forced-piece propagation)
- piece_live_count[p] tracks # of currently-alive piece occurrences.
- When count drops to 1: piece is forced; pin its cell transitively.
- ~0.37s/node, max depth 40. **Marginal improvement; forced firings rare.**

## Empirical findings

- Init AC-3 + uniqueness fixpoint: 105.3M blocks after 1.21× reduction.
- Per-cell sizes range from 620 (corners) to 3.6M (large interior).
- **DFS consistently backtracks at depth 37-40** across 1000+ nodes tried.
- Implies one of:
  1. Many feasible 480-extensions but pruning fails to identify them.
  2. The visible 480-space is very narrow.
  3. No 480 exists (interesting if true).

## What hasn't been tried

- **Variable ordering other than MRV.** Spatial ordering (concentric layers from hint cells, perimeter-first) might align better with the puzzle's structure.
- **Value ordering (LCV).** Currently candidates iterated in alphabet-index order.
- **Genuine alldiff (bipartite matching).** The current "forced-piece" is partial alldiff. Full alldiff via Hopcroft-Karp would prune more (and detect UNSAT when matching < 256).
- **Cube-and-conquer on top of BB&B.** Split on corner cells (5 hint super-cells already partially pinned), use cubes as parallel branches.

## Currently running

`super_block_bbb_v3 --max-nodes 1000000` overnight to see how far it gets:
- At 0.3s/node, 1M nodes ≈ 83h CPU.
- Will be killed at ~3600s wall = ~12k nodes processed.
- If it reaches depth ≥ 45 anywhere, that's an important signal.
- If consistently 37-40, then the search may be empirically near-infeasible.

## Linked

- [[super-block-bbb]] (design)
- [[v125-bbb-status]] (v1+v2 status)
- [[v125-cube-conquer-finding]]
