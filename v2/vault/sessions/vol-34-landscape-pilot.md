# Vol-34 — landscape mapping pilot (during T3 wait)

**Date**: 2026-05-14 (mid-vol-34, while T3 lottery ran).
**Status**: pilot finding, supports vol-35 T1 plan.

## Setup

User mid-vol-34 proposed: "could we on smaller puzzles map the world
of minima/maxima and from that, see if it scales to bigger puzzles?"

I built `landscape_explorer` (`crates/bench-audit/src/bin/landscape_explorer.rs`)
that runs ALNS-from-random for many independent restarts and saves
each polished local optimum. Tested at 4×4/4c and 6×6/5c.

## What was measured

### 6×6/5c (50 restarts × 2s ALNS + polish_rotations + piece_swap_hillclimb)

| Score | Count |
|---:|---:|
| 42 | 1 |
| 43 | 1 |
| 44 | 2 |
| 45 | 4 |
| 46 | 11 |
| 47 | 6 |
| 48 | 8 |
| 49 | 5 |
| 50 | 5 |
| 51 | 2 |
| 52 | 3 |
| 53 | 1 |
| 54 | 1 |

Max edges = 60. Score range 42-54 (70-90% of optimum).

**All 50 final boards are pairwise distinct** by md5.

Within-score-class pairwise Hamming (on (piece_id, rotation) at each
position): 31-36 out of 36 cells differ.

### 4×4/4c (100 restarts × 1s ALNS + polish)

Score range 14-22 (max 24). Score 18-20 are most common.
**All 100 final boards distinct**.

## Conclusion

**ALNS-from-random doesn't cluster at small scales.** Even on 4×4/4c
with only 24 internal edges and 16 cells, 100 random starts produce
100 distinct LOs.

The basin-radius (Hamming distance an init walks before hitting its LO)
is apparently tiny — most random configurations are AT or near a
local optimum already. ALNS+polish produces a unique attractor per
starting configuration.

## Implications for vol-35 T1

Simple ALNS-from-random + Hamming-clustering won't work. The basin
graph is too granular. Alternative approaches:

1. **Brute-force LO enumeration**: enumerate ALL boards with score ≥ N
   via modified vanilla_fast (size-agnostic), then post-process each
   for LO-ness (no single swap improves). At 6×6 this is feasible.

2. **Strong-attractor mining**: hill-climb with a MUCH longer budget
   and stronger operators. The "super-basin" structure that ALNS
   escapes from might still cluster.

3. **Define basins differently**: use a META-OPTIMIZER (longer ALNS)
   to converge multiple "naive LO" starts to a "super-LO". The
   basin graph then has many tiny pseudo-LOs as nodes and a few
   super-LOs as super-nodes.

User's brute-force suggestion is the cleanest. Vol-35 T1 should
pursue option 1.

## Linked

- [[fitness-landscape-mapping]] — concept page, updated with
  brute-force LO enumeration plan.
- [[trajectory-families]] — vol-18 finding on disjoint basin families
  (this pilot generalizes: every random init has its own micro-basin).
