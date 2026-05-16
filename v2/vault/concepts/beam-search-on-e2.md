---
name: beam-search-on-e2
description: "Vol-109 T2 — analytical refutation. Beam-search engine variant was sketched as a possible 'different trajectory' source vs DFS. Analysis: beam search doesn't change the underlying constraint structure; at depth 200 only candidates matching (top,left) get expanded and pieces_used prevents reuse — same as DFS. The 'diverse trajectory' claim reduces to 'DFS with random tiebreak' which is already covered by seed_offset multi-thread."
metadata:
  type: project
---

# Beam search on E2 — analytical refutation (vol-109 T2)

**Status**: `refuted-analytical` — not built. 2026-05-16 ~12:30.

## The idea

Maintain top-K partial boards at each depth, expand each by one
ply per generation. Different from DFS (which commits to one path
and backtracks). May reach trajectories DFS misses.

K=8 matches our thread count; K=1000 fills compute differently.

## Why it doesn't help on E2

1. **Same constraint structure as DFS.** At depth 200, a beam state
   can only be extended by candidate pieces whose `(top, left)` edge
   colours match the placed neighbours AND that aren't already in
   `pieces_used`. Both constraints are EXACTLY the same as in DFS.
   Beam search doesn't relax them; it just keeps multiple states
   alive instead of backtracking.

2. **What "keeps a state alive" means in beam.** Beam preserves a
   state at depth D if its score is in the top-K. But a state at
   depth D has the SAME (top, left) constraints at depth D+1 as
   another state at depth D with a different prefix. Beam's
   "alive" doesn't make harder-to-fill cells easier.

3. **The "diverse trajectory" claim reduces to DFS with random
   tiebreak.** If beam picks top-K by (score + noise), the chosen
   states differ randomly. But our existing `seed_offset` flag
   produces 8 randomly-shuffled DFS trajectories at the same cost,
   and vol-106 T10 measured 0.8% pairwise agreement across those
   trajectories — already maximally diverse.

4. **Beam search wins where DFS over-commits.** For E2 row-major
   with constraint-bucket DFS, the DFS doesn't over-commit — it
   immediately backtracks when a depth has no candidates. The
   "savings" of not backtracking that beam would offer are
   marginal at best.

5. **Beam search hurts where DFS depth-first finds dead ends fast.**
   Many partial boards at depth 100 lead to NOTHING at depth 200.
   DFS discovers this fast (descend, fail, backtrack). Beam search
   keeps these dead-end states alive across multiple generations
   until they fail, wasting compute on hopeless branches.

## What would be a real beam-like win

Only if we had a strong "promise" heuristic — a scoring function
that can RELIABLY predict at depth 100 which states will reach
depth 250. For E2 with 22-color adjacency, no such heuristic is
known. The vol-15-29 ML work tried to learn one; vol-29's imitation
ceiling caps at the engine's own behaviour, no lift.

If a stronger heuristic existed, BEAM would be a natural use. Without
it, beam is just slower DFS.

## What this means for vol-109

Refute without building. Pivot to other vol-109 candidates:
- T1 (oracle-aware ALNS repair) — has a real lever (modify halo
  edge constraints by force-placing oracle pieces).
- T3 cross-machine bench (needs Linux access, deferred).
- Per-schedule const tables for v15 — small but concrete.

## Linked

- [[../sessions/vol-109]] (when opened).
- [[blackwood-fast]] — engine reference.
- [[../sessions/vol-106]] — T10 measurement of trajectory diversity.
