---
name: cooperative-frontier-hashing
description: "Vol-106 T9 INVENTION SKETCH — N parallel DFS workers share a probabilistic hash table of explored 'frontier states' (= the placed-cells multiset at a given depth). When worker B reaches a frontier worker A already explored to depth D₁, B can prune at depth D₁ (since A already proved no completion below). NEW: this is dependency-free coordination through a shared lock-free dedupe table. Not in libblackwood (single-thread per process), not in any E2 paper found."
metadata:
  type: project
---

# Cooperative frontier hashing (vol-106 T9 sketch — INVENTION)

**Status**: `unbuilt`. Conceived 2026-05-16 during vol-106 T9
brainstorm under user directive "invent new horizons". Not in
libblackwood, vanilla_fastest, or solver-engine. Not found in
published E2 literature (community-corpus survey vol-65).

## The idea

In an N-worker parallel DFS, all workers explore the SAME state
space, just from different starting orders. Workers redundantly
explore overlapping subtrees. A shared frontier-hash table
deduplicates by recording which (depth, frontier-state) tuples
have already been EXHAUSTED by some worker.

When worker B's DFS reaches frontier F at depth D, and the shared
table records "frontier F at depth D was exhausted by worker A", B
can prune at depth D directly — no point re-exploring a subtree
already proven unfruitful.

## The frontier-state hash

For row-major DFS at depth D, the partial board's "frontier" =
(placed-pieces multiset, frontier-cells-color-requirements). Both
parts are encoded into a u64 Zobrist hash:

  H = XOR(zobrist[piece_id * 4 + rot, position] for each placed cell)

This collides for permutations of the same piece-rotations at the
same positions (impossible — pieces are unique), but DOES NOT
collide when two different trajectories lead to the same set of
placements. (The frontier-color requirements are implicit in the
placements, so the hash captures all the constraints.)

## Shared-table mechanics

- Dense lock-free hash table sized to ~256 MB (32M u64 keys + 32M
  u32 depth/exhausted bits).
- Insertion on FAILURE-EXHAUSTION: when worker A's DFS at depth D
  proves "no completion exists past F", insert (hash(F), D).
- Lookup on DESCENT: when worker B descends INTO depth D with
  frontier F', check `table[hash(F')] == (hash(F'), D')` for
  D' <= D. If yes → prune.

The "exhausted past D" claim is sound IFF A's DFS truly explored
all completions of F past depth D. In a time-bound DFS, A might
have only EXPLORED some completions before time-out — we mustn't
insert F as "exhausted" unless A actually exhausted it.

Easy fix: only insert F when A's DFS naturally backtracks UP THROUGH
depth D (meaning every completion from F was tried).

## Why this is genuinely new

- libblackwood: independent processes, no shared state.
- vanilla_fastest: rayon workers, no coordination.
- DFS+caching (memoization): typically used for game-tree search
  (alpha-beta, MCTS), not constraint-search DFS. E2 has too many
  states for full memoization, but PROBABILISTIC + LAZY
  memoization (only "I exhausted this") is cheap.
- The Zobrist hash trick is borrowed from chess engines but the
  application to constraint DFS sharing is NEW.

## Implementation cost

- Hash table: `Vec<AtomicU64>` of size N (with linear probing or
  cuckoo). u64 stores (hash, depth, exhausted-flag) packed: 56 bits
  for the hash, 8 for depth.
- Zobrist key generation: 1024 (piece_rot) × 256 (positions) = 256K
  u64 entries. Init once.
- Per-placement: XOR one Zobrist key into running hash.
- Per-backtrack-through-frontier-boundary: insert (hash, depth).
- Per-descent: lookup hash, prune if found at depth ≤ current.

Per-node cost: 2 atomic ops, 1 lookup. Maybe 20-50ns overhead.

## Expected benefit

Hypothesis: deep in the search (depth > 150), workers converge on
"similar" partial boards via different paths. The hash table
catches this in O(1) lookup, saving the deep re-exploration cost
(potentially millions of nodes per hit).

The win scales with N × time. At 8 workers × 5 min × 60M nps =
~150B node visits — many would hit the hash table.

## Open questions

1. How frequently do worker trajectories converge to the same
   frontier? Need empirical measurement to estimate hit rate.
2. False-positive cost: if the hash table is too small / collisions
   wrongly prune valid branches. Mitigate by storing the FULL key
   (Zobrist u64) and rejecting collisions.
3. Memory pressure: 256 MB shared table is significant. Trade-off:
   smaller table → more collisions → fewer hits.
4. Sound-vs-time-bound: only worker A's NATURALLY-COMPLETED
   backtracks can insert "exhausted". Workers that time-out cannot.
   This restricts the operator's effective use to fast subtrees.

## Implementation plan (vol-107)

1. Add `frontier_hash: u64` to per-thread state in
   `solve_blackwood_sized`. Maintain via Zobrist XOR per
   placement / backtrack.
2. Build the shared lock-free hash table (`scc::HashIndex` or
   `dashmap::DashSet` or hand-rolled `Vec<AtomicU64>`).
3. Insert on backtrack-through-frontier (when depth drops AND the
   subtree exhausted naturally).
4. Lookup on each descent.
5. A/B vs the non-coordinating multi-thread baseline. Variance ≥ 8
   seeds × 60s. Measure hit rate, hit-cost-amortisation, total
   max_depth lift.

## Linked

- [[blackwood-fast]] — multi-thread baseline.
- [[../sessions/vol-106|vol-106]] — origin.
- [[edge-color-supply-propagator]] — sibling vol-106 invention
  (refuted).
