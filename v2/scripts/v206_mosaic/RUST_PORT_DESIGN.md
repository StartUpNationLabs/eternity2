# MOSAIC Rust port — design (vol-206/207)

## Why port
Python/RC2 block-solve is ~15s/block → caps the search at single-descent + light
reservation (448/480). A Rust block-solver enables millions of block-solves →
deep block-backtracking + long multi-restart runs → much higher ceiling.

## Key insight: blocks are tiny → exact DFS, not MaxSAT
A BS×BS block (BS=4 → 16 cells) with FIXED boundary has very few candidates per
cell (the vol-204 scarcity: ~2-3 edge-strict survivors, fewer with 2 boundary
sides fixed). MaxScore over ≤16 cells is solvable EXACTLY by a small DFS with the
optimistic-remaining B&B bound the engine already has (solver-engine lib.rs:2268).
No SAT solver needed — microsecond-to-millisecond per block.

## Architecture (new bin in bench-audit: `mosaic`)
Reuse: `eternity2_benchmark::loader` (puzzle), `eternity2_export` (board JSON +
bucas_url), the RowMajorIndex / (N,W) bucket idea from blackwood-fast.

Components:
1. **Block exact MaxScore DFS** `solve_block(cells, pool_bitset, boundary_soft, pins)`
   → best assignment (max internal+boundary matches), via DFS + B&B. Enumerate
   top-K block solutions on demand (for backtracking) by continuing the DFS.
2. **Composition driver**: block order (row/spiral/corners), reservation
   (withhold scarcest pieces by the vol-204 scarcity metric), soft boundaries.
3. **Block-level backtracking**: stack of block states; on a poor/failed block,
   pull the previous block's next-best solution (frees different pieces).
   Focus backtracking on the last/worst blocks (where degradation concentrates).
4. **Hints**: pin hint cells, remove hint pieces from pools (strict-canonical).
5. **Output**: timestamped JSON + bucas_url + history (match the Python persistence
   contract; verify with rescore_board).
6. **Multi-restart / seed diversity**: randomize block-internal tie-breaking by
   seed; run N restarts, keep best (report variance per the rigor rules).

## Performance target
If block-solve is ~1ms, a full 16-block board is ~16ms; 10^5 board-attempts
(with backtracking) in ~30min single-thread; ×8 cores. Enables the search depth
Python can't reach.

## Then: ALNS post-step
Feed MOSAIC's best board (≥448, hopefully higher with backtracking) into the
existing `alns_only basic_lkh` — the pipelines lift +10-15 from a good seed, so
448+ could reach the 458-460 class. Verify every claimed board with rescore_board
+ verify_board (piece-uniqueness) per the anti-patterns.

## Validation gates (rigor)
- Block DFS must match Python RC2 block-optima on the same inputs (correctness).
- Full-board MOSAIC-Rust must reproduce ~448 on the same config as Python.
- Report min/median/max over ≥8 seeds (variance rule).
- rescore_board + verify_board before any record claim.
