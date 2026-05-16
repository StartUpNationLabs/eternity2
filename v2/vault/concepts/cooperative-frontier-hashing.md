---
name: cooperative-frontier-hashing
description: "Vol-106 T9 INVENTION REFUTED BY T10 MEASUREMENT. Hypothesis: shared frontier-hash dedupe across workers would catch redundant subtree exploration. Empirical (T10): 8 workers each place ~214 cells, pairwise agreement is 1.8 cells (0.8%). Workers explore radically different trajectories; shared hash would have near-zero hit rate. Don't build."
metadata:
  type: project
---

# Cooperative frontier hashing (vol-106 T9 — REFUTED PRE-BUILD)

**Status**: `refuted` (without building) 2026-05-16. The hypothesis
was tested empirically via [[#The T10 measurement]] before building
the lock-free shared table. Result: workers' trajectories diverge
so quickly that the shared dedupe table would have near-zero hit
rate.

## The T10 measurement

`bf_similarity` runs 8 workers × 15s on canonical Selby-Riordan
16×16 with the v17a schedule, then computes pairwise agreement
(cells where two workers' deepest boards have the same piece + rotation):

```
[bf_similarity] per-thread max_depth:
    t0: max_depth=192    t1: max_depth=218    t2: max_depth=220
    t3: max_depth=215    t4: max_depth=220    t5: max_depth=192
    t6: max_depth=235    t7: max_depth=220

mean diagonal (placed cells per thread): 214.0
mean off-diagonal (agreement between threads): 1.8
max off-diagonal: 5
agreement fraction: 0.8%
```

**Interpretation**: workers have effectively NO shared frontier
states at their deepest boards. The variance in `max_depth` (192
to 235) and the near-orthogonal placements confirm that shuffling
the candidate-list order leads to genuinely different search
trajectories. A shared dedupe table would catch only ~0.8% of
states even at maximum exploration depth — and the hit rate at
shallower depths (where dedupe would help most) is probably even
lower, since deep agreements at least reflect the "natural"
constraint structure.

**Conclusion**: the cooperative-frontier-hashing operator is
unbuilt and will stay so. The hypothesis is refuted by direct
measurement, not by analytical argument — the right way.

## Why the hypothesis failed

A row-major DFS with a sentinel-walked candidate list is highly
PATH-DEPENDENT: the FIRST piece tried at depth k determines which
candidates are available at depth k+1, which compounds across the
trajectory. Two workers with different bucket orderings effectively
explore different branches of the search tree from depth ~1 onward.

For a shared hash table to pay off, workers would have to RECONVERGE
on the same partial board through different paths. This requires
that the underlying solution space has a strong "central tendency"
— like a chess engine where many opening sequences lead to the same
mid-game position. E2's row-major DFS has no such reconvergence.

## What this DOES tell us

The diversity of 0.8% agreement is **good news** for the existing
multi-thread parallelism: workers genuinely explore different
parts of the space, justifying the speedup we measured (8t @ 30s
reaches 235 depth / 427 score vs 1t @ 30s reaching 192 depth / 344
score).

## Original sketch (preserved per vault "no quiet deletes")

**Original status (preserved)**: `unbuilt`. Conceived 2026-05-16 during
vol-106 T9 brainstorm. Not in libblackwood, vanilla_fastest, or
solver-engine. Not found in published E2 literature (community-corpus
survey vol-65).

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
