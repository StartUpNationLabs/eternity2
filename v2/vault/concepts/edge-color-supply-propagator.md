---
name: edge-color-supply-propagator
description: "Vol-106 T8 SKETCH then REFUTED. New propagator idea (maintain remaining edge-color supply, check frontier feasibility). Implemented + measured 2026-05-16: ZERO PRUNING, ~40% nps slowdown. The check is REDUNDANT with the existing (top, left)-keyed candidate bucket structure. Documented as a dead-end."
metadata:
  type: project
---

# Edge-color supply propagator (vol-106 T8 — REFUTED)

**Status**: `refuted` (built + measured 2026-05-16). The check
caught zero additional pruning opportunities beyond what the
existing candidate-bucket structure already provides, while adding
~40% per-node overhead.

## Refutation (2026-05-16)

The check `supply[P.bottom] < 2` (after consuming P's 4 edges) was
implemented in `solve_blackwood_sized`. Measured on canonical
Selby-Riordan 16×16/v17a schedule, single-thread, 10s budget:

| version              | nodes (M) | max_depth | best_score | nps (M) |
|----------------------|----------:|----------:|-----------:|--------:|
| baseline (no T8)     |      630  |       192 |        344 |     63  |
| + edge-supply check  |      388  |       192 |        344 | **39**  |

Same max_depth, same best_score, just 60% the throughput. Conclusion:
**the check is redundant with the existing candidate bucket structure.**

## Why it's redundant

The bucket at `(tbl, top_color, left_color)` already contains ONLY
piece-rotations whose top edge matches `top_color` and left edge
matches `left_color`. When we walk that bucket, we cannot SELECT a
piece whose colors would later cause supply[k] = 0 for a required-k,
because for cell d+w to demand color k, color k must appear on the
piece P we just placed AT depth d (i.e., P.bottom = k). And then
the next iteration's bucket at `(top=k, left=...)` would contain
ONLY pieces with top=k — if no such unplaced piece exists, the bucket
is naturally empty and we backtrack.

So the bucket structure IS the propagator. Adding an explicit supply
check duplicates the work that the empty-bucket → empty-trial path
already performs.

## When it would have helped

The propagator would catch failures EARLIER than the bucket structure
only if we had richer constraints (e.g., the cell at d+2w requires
top=k AND no remaining piece has top=k). That requires multi-step
look-ahead, which the simple supply check doesn't do.

A more elaborate forward-check (compute "all unplaced pieces' top
edges as a multiset, count occurrences of each color, compare to
the multiset of required-tops across all currently-known frontier
cells") could theoretically catch this. But the per-node cost would
be much higher, and it's not clear the win is positive.

## Lesson

**Bucket-structured DFS already encodes the local-feasibility
propagator.** Adding redundant checks doesn't help. To beat this
baseline, propagators must catch failures that the bucket structure
can't — and on E2 with this row-major scan, those are far between.

The math here: the cheap propagator's expected pruning value is
zero because the search would have backtracked one step later anyway.
The marginal expected node-savings is tiny (~1 node per dead branch),
while the per-trial overhead applies to ~7 trials per success deep
in the search.

## Original sketch (preserved per vault "no quiet deletes" rule)

**Original status (preserved)**: `unbuilt` (sketch only). Conceived
2026-05-16 during vol-106 T8 brainstorm. Not in libblackwood, not in
vanilla_fastest, not in solver-engine. Genuinely new operator. *(See
the rest of this page for the original design.)*

## The propagator

**Invariant**: at any point in the row-major DFS, the partial board
creates a "frontier" of cells whose required-edge colors are
already known (the cells immediately right or below already-placed
cells). Each such known requirement needs at least ONE remaining
piece-edge with the matching color in the unplaced pool. If for any
required color k the unplaced-edge supply of k drops to 0, the
branch is provably infeasible.

## State

Maintain `supply: [u32; N_COLORS]` (24 entries for canonical
22-color + border = 23). Initial value: count of each color
across all piece edges.

At each placement at depth d of piece P:
- For each of P's 4 edges with color c: `supply[c] -= 1`.

At each backtrack from depth d:
- For each of P's 4 edges with color c: `supply[c] += 1`.

Frontier-constraint count: `required[k]` = number of as-yet-unplaced
cells in row-major scan whose required-edge (top from above-neighbour
or left from left-neighbour) is color k. For row-major:

- `required` is bounded by w+1 (one row above d's frontier + 1 cell
  to the right of last placed).
- It's cheap to maintain incrementally: at placement of piece P at
  depth d, the bottom edge of P becomes the required-top of cell
  d+w (`required[P.bottom] += 1`). The right edge of P becomes the
  required-left of cell d+1 (`required[P.right] += 1`). When d+1 is
  placed, that requirement is consumed (`required[required_left_at_d+1] -= 1`).

## Check

At any candidate-trial entry: if `required[k] > supply[k]` for any k,
the branch is dead. Prune all candidates at this depth.

## Cost / Benefit

**Per node cost (canonical 16×16):**
- 4 × 2 = 8 supply increments/decrements on placement.
- 1 increment on required (bottom) + 1 on required (right) on placement
  (mirrored on backtrack).
- N_COLORS = 23 comparisons to check `required ≤ supply` (but only need
  to check the 1-2 colors just decremented OR the colors that just
  picked up new requirements — much cheaper incrementally).

**Expected benefit:** at low-mid depths, supply contention drops
quickly. Many branches that today walk all 12-20 candidates per
depth would be cut entirely. Hypothesis: 1.5-3× faster CP partials
(but per-node nps may DROP because of the per-trial check).

## Why this is new

- **libblackwood** has heuristic-color schedule + break-index allowance.
  Neither directly checks supply.
- **vanilla_fastest** has no propagation.
- **solver-engine**'s `gacolor` + AC-3 + NS-1 propagators DO consider
  supply, but at much higher cost (per-cell, with full domain
  computation). Edge-color supply propagator is a SUBSET of NS-1
  (which is "multi-set equality deficit") but with a cheaper per-node
  cost. NS-1's vol-11 measurement of Δ ∈ {0,1,2,4} on score-448-480
  partials shows the invariant is meaningful at the high-score regime.

## Open questions

1. Is the per-node check cost amortised by the pruning, or does it
   slow the search (vol-15's [[blackwood-layered-depth-wall]] taught
   us depth wins don't always translate to score wins)?
2. Does the check fire at low depths (where it matters for cold-start)
   or only at high depths (where DFS is already dead)?
3. How does it interact with the Blackwood schedule (which already
   does similar pruning for the 3 heuristic colors)?

## Implementation plan (vol-107)

1. Add `supply: [u32; 32]` + `required: [u32; 32]` to
   `RowMajorIndex` state OR pass as stack-allocated arrays into
   `solve_blackwood_sized`.
2. Initialize `supply` from piece-edge count; `required` from
   border-row of cell 0 (init = [BORDER count]).
3. On candidate-place: decrement 4 supply, increment 2 required
   (bottom + right of placed piece).
4. On backtrack: mirror.
5. On candidate-try (before bitset check): if any `required[k] >
   supply[k]`, skip this depth entirely (backtrack the parent).
6. Measure: A/B vs solve_blackwood without the propagator on canonical
   Selby-Riordan, ≥ 8 seeds × 30s budget.

## Linked

- [[blackwood-fast]] — where this would integrate.
- [[../sessions/vol-106|vol-106]] — sketch origin.
- [[../sessions/vol-11|vol-11 NS-1 measurement]] — earlier multi-set
  equality work this generalises.
