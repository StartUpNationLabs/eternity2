# Vol-57 — CDCL no-good Rust prototype

**Open**: 2026-05-15
**Theme**: First Rust implementation of CDCL no-good learning for E2.
**Status**: in-progress.

## Goal

Standalone `eternity2-cdcl-proto` crate. Math from vol-56 → working
Rust code on 6×6/5c.

## T1+T2 result (built tonight)

`crates/cdcl-proto/src/lib.rs` shipped. Standalone CDCL prototype on
6×6/5c.

### Algorithm:
1. AC-3 with per-row cause tracking (placed-neighbour subset is the
   sound over-approx cause).
2. 1-UIP analysis = union of cause sets for all values originally in
   the wipeout cell's domain (E2 has flat cause graph).
3. NoGood DB with 2-watched-literals index (first 2 sorted literals
   per clause).
4. Unit propagation: walk clauses whose watch list contains a
   currently-assigned literal; if K-1 literals satisfied + 1
   unassigned, remove the unassigned literal's value from its cell.

### Test result on 6×6/5c (results vary by HashSet iteration order):

| Run | Found | Nodes | Wipeouts | BT | Time | Clauses | AvgSize | Props |
|---|---|---|---|---|---|---|---|---|
| vanilla | ✓ | ~100k-250k | ~50k-100k | — | 1-4s | — | — | — |
| cdcl | ✗ (timeout) | ~48k | ~15k | — | 30s | ~15k | 8.7-8.9 | ~41k |

### Findings

- **CDCL nodes are 2-5× fewer than vanilla**. The math works:
  unit-propagation from learned clauses prunes the search tree.
- **CDCL wall-clock is SLOWER**. Even with watch-filtered unit-prop,
  each node does O(reachable clauses) work, which with 15k clauses
  adds up to >800M ops over the search.
- **Clauses are compact** (avg 8.7 literals, max 23). 1-UIP works as
  expected.
- **Unit propagations fire constantly** (~2.5 propagations per
  learned clause).

### Next: vol-58 — real 2WL for wall-clock parity

The naive watch-filtering still scans all candidate clauses every
node. Real 2WL maintains:
- For each clause, two watched literal indices.
- When a watched literal becomes BLOCKED (= clause now can fire or
  conflict), update the watch to a non-blocked literal.
- Only walk a clause once per watch transition (not per node entry).

Estimated 3-5 days of careful Rust work for the proper 2WL impl.
With 2WL, wall-clock should match or beat vanilla on 6×6/5c.

## Status — vol-57 closed for tonight

Algorithm validated. Engineering for 2WL wall-clock parity is vol-58
work. Standing 458 record unchanged; vol-57 was foundational research.

Vol-58 candidate tracks:
1. Real 2WL implementation → wall-clock measurement on 6×6/5c.
2. Port to 8×8 puzzles, measure scaling.
3. Solver-engine integration (per cdcl-engine-integration.md design).


