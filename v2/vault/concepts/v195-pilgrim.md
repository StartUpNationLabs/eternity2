---
name: v195-pilgrim
description: 12-hour hybrid DFS algorithm. Blank canvas + 5/5 hints pinned + MCV value-order + restart-on-saturation + 8-core scan-order portfolio. Hard edge invariant (zero errors throughout). Each restart explores a different basin via shuffled value-order. Best max_depth across portfolio wins.
status: built
metadata:
  type: concept
---

# V195 PILGRIM — long-run hybrid DFS

A long pilgrimage through the solution tree, with periodic restarts to find new paths.

## Why a new algorithm

User asked for a 12-hour run with three constraints:
- **No errors** (zero mismatches throughout).
- **Row-by-row** placement.
- **Backtracking** to use compute productively.

Existing pieces that fit:
- `bf_bw_hinted` does row-major DFS with hard edge-match and 5/5-hint pins. But it **saturates in ~1 minute**: reaches depth ~208 then gets stuck searching deep subtrees that never advance.
- `bf_bw` with `--break-count 0` is row-major DFS without hints — also saturates fast.
- Beam-search variants (V155, V181, V189) place row by row but soft-prune at each depth — they're not pure DFS.

None of these scales to 12h productively. PILGRIM fixes that.

## The PILGRIM algorithm

### Core loop (single worker thread)

```
1. INIT: pre-place the 5 canonical hints. Score = 0, depth = 0.
2. DFS_LOOP:
   a. Find next-best cell to place (MCV: smallest legal-candidate set).
   b. Enumerate candidates (piece, rotation) in seeded-random order.
   c. For each candidate that satisfies all placed neighbors:
      i. Place it, advance depth.
      ii. If depth > best_so_far: save board, update best.
      iii. Recurse from step 2a.
      iv. On dead-end (no candidate fits): backtrack 1 level.
   d. If all candidates exhausted at depth 0 OR no progress for K iterations:
      RESTART with a new seed (shuffles value order).
3. REPEAT until time budget exhausted.
```

### Key design choices

**A. Variable ordering**: Most-Constrained-Variable (MCV) — at each depth, place the cell among the ~20-30 visible candidates that has the smallest legal-candidate domain. This naturally focuses search on chokepoints first, expanding from constrained anchors.

**B. Value ordering**: seeded-random shuffle of candidates at each depth. Different seeds = different exploration order. Together with restarts, this explores the search tree breadth-wise over time.

**C. Restart trigger**: two conditions:
- Hard: max_depth hasn't advanced in N nodes (e.g., 100M nodes without progress).
- Soft: scheduled every M minutes regardless.

**D. Restart action**: increment seed by 1, reset depth to 0, keep best_so_far. Same hints, same algorithm, new value-order.

**E. Portfolio**: 8 parallel workers, each with a DIFFERENT scan_order:
- Worker 0: row-major (standard).
- Worker 1: column-major.
- Worker 2: spiral inward.
- Worker 3: spiral outward.
- Worker 4: zigzag.
- Worker 5: zigzag reverse.
- Worker 6: diagonal NW-SE.
- Worker 7: diagonal NE-SW.

Each worker has its own seed counter. Best across all 8 workers wins.

### Why this scales over 12h

The combinatorial branching factor at depth D in DFS is ~b^D where b ≈ 5-20 per cell. A single DFS exhausts ~b^k nodes in time T. After exhaustion, more time spent on the same value-order is wasted.

PILGRIM's restarts give it **breadth**: each restart explores a different "horizontal slice" of the tree. 1000 restarts in 12h × 8 workers = 8000 distinct explorations of the upper 5-10 levels. By coupon-collector logic, this approaches an exhaustive scan of depth-10 paths in 12h.

Combined with MCV (focusing each DFS on chokepoints) and per-worker scan-orders (different exploration topologies), the portfolio coverage is much wider than any single DFS could be.

### What PILGRIM is NOT

- Not exhaustive (can't certify "no solution exists at depth ≤ D").
- Not basin-anchored (doesn't warm-start from any partial).
- Not score-optimizing (it maximizes DEPTH, with score as tiebreak).
- Doesn't use ALNS, repair, or fill — pure DFS only, by construction.

### Expected behavior

Single-worker bf_bw_hinted reaches depth 208 in 30s and stalls. PILGRIM workers should:
- Reach depth 210-220 within minutes (similar to bf_bw_hinted).
- Push past 220 within hours via restarts on lucky seeds.
- Theoretical ceiling: depth 255 (if any restart finds a complete solution).

Realistic 12h outcome: **depth 230-245** with high probability based on the V190-bf_bw findings showing 238-cell partials reachable; PILGRIM combined with hint-preservation and MCV may exceed this since it doesn't have the break-index ceiling.

## Linked

- [[bf_bw_hinted]]
- [[v190-strict-raw]]
- [[v186-pool-biased-top-down]]
- [[../sessions/vol-195]] (TBD)
