# STRATUM — Color-Class Layered Construction

**Status**: Day-1 (color-orbit hypothesis) refuted |G|=1. Day-2
STRATUM v2 (color-weight value-order DFS) shipped but **underperforms
vanilla_fast** (695k nps vs 85M nps, max_depth 86 vs ~250 in 60s).
Pivoted Day-3 to STRATUM-Budgeted (per-color-class matching-budget
propagator on top of vanilla DFS) — the actual invention.

## What was tested

V149-T1 enumerated color-permutations π ∈ S_22 preserving canonical E2
piece set under rotation-orbits. Result: **|G| = 1** (only identity).
Each of 22 interior colors has a UNIQUE adjacency-multiset across the
piece set, so no two colors are confusable. The Selby-Riordan
generator broke every color-swap symmetry.

## What was learned

The color-count classes are highly structured:

| count per color | # colors | total occurrences |
|-----------------|----------|--------------------|
| 24 | 5 | 120 |
| 48 | 5 | 240 |
| 50 | 12 | 600 |

Notes:
- 120 = 24 × 5 = perimeter-interior matching count
  ([[rare-color-geography]] vol-13: rare colors are border-ring-only).
- 240 = 48 × 5 = exactly the interior-side adjacency count of border
  ring (60 pieces × 4 sides = 240).
- 600 = 50 × 12 = remaining interior matching slots.

Total = 120 + 240 + 600 = 960 = 2 × 480 (each interior edge counted
on both adjacent sides).

## STRATUM v2 — color-class sequencing DFS

Original hypothesis (color-permutation orbits → piece strata) was
refuted. But the color-count classes give a NEW constructive direction:
**place pieces in color-class order**, not position order. This is a
**variable-order heuristic**, not a value-order one.

### Layer schedule

1. **Layer 0**: 4 corner pieces (all border-corner). 4 cells.
2. **Layer 1**: 56 border-edge pieces (border colors on 1-2 sides). 56 cells.
   Within this layer, sub-order by "carries rare color (1-5)".
3. **Layer 2**: 196 interior pieces (no border edges).
   Within this layer, sub-order by descending **rare-color-bearing**:
   - 2a: interior pieces with ≥ 1 rare color (1-5). These are the 24 ×
     5 / (some-double-count) pieces from layer-1 spillage. Estimate
     ~40 pieces.
   - 2b: interior pieces with only medium colors (6-10).
   - 2c: interior pieces with only common colors (11-22).

### Why it might be faster

Rare-color pieces have FEWEST candidates per (N, W) bucket because
their colors appear only 24 times across the piece set. CSP MRV would
identify them as high-priority. STRATUM v2 pre-commits to that order
without measuring during DFS — saving the MRV lookup.

More importantly: by placing color-class 1 pieces first, the DFS
*locks in* the rare-color edge structure of the board EARLY. Vol-14
finding ([[../sessions/vol-14]]) was that the 764-domain "plateau"
in interior cells is the actual search bottleneck; placing
rare-color pieces first reduces this plateau because rare-color
constraints are tight.

### Falsifiable claim

A canonical 16×16 DFS using STRATUM-v2 layer order should reach
significantly higher depth in the same wallclock than row-major DFS,
because rare-color pieces account for 120/960 = 12.5% of edges but
provide far more domain reduction.

## Day-2 plan

1. Build the layer schedule generator: for each piece, assign layer
   (0/1/2a/2b/2c).
2. Build a STRATUM-v2 DFS Rust binary (fork of vanilla_fast with
   custom scan_order).
3. Compare to vanilla_fast on canonical at 60s wallclock.

## Day-2 result (2026-05-19 18:30 CEST)

V149-T2 binary `target/bench-fast/v149_stratum_dfs` shipped. 60s
canonical, **no pin-hints**: 695k placements/sec, max_depth 86. By
comparison, vanilla_fast on canonical reaches ~250 in 60s.

**Diagnosis**:
- The general DFS engine pays a constant per-candidate cost for the
  4-side neighbour check that vanilla_fast amortizes via NW-buckets.
- The "color_weight per piece-rot" sort is GLOBAL — every cell sees
  the same candidate order. Not adaptive. Equivalent to a single
  piece-id permutation, which doesn't add information.
- 99.1% of placements at depths 80-99 means the DFS thrashes on layer
  transitions where many candidates conflict.

**The "color-weight value order" architecture is not a real invention.**
It's just a sorted DFS that lost its NW-bucket optimization.

## STRATUM v3 — Per-Color-Class Matching-Budget Propagator

The genuine invention is to add a NEW PROPAGATOR that tracks per-color
matching budgets and prunes infeasible partials.

### Math

Let $C$ = set of 22 interior colors, partitioned into:
- Rare $R = \{1,...,5\}$ — 24 occurrences each.
- Medium $M = \{6,...,10\}$ — 48 occurrences each.
- Common $K = \{11,...,22\}$ — 50 occurrences each.

For a complete 480-matched board, each color $c$ contributes exactly
$|c|/2$ matched edges, where $|c|$ is its occurrence count. So:
- Rare: 5 × 12 = 60 matched edges.
- Medium: 5 × 24 = 120 matched edges.
- Common: 12 × 25 = 300 matched edges.
- Total: 480. ✓

During DFS at a partial board, let $u_c$ = number of color-$c$ sides
currently on placed cells that face *unplaced* neighbours (= still
unmatched, could be matched in the future). Let $m_c$ = number of
color-$c$ sides on placed cells that face placed cells with a
DIFFERENT color (= permanently unmatched).

**Propagator condition** (a 480 solution is reachable from current
partial only if):
$$\forall c \in C: 2 \cdot (\text{matched}_c) + u_c \geq |c| - 2 \cdot \text{m}_c$$
$$\Leftrightarrow \text{matched}_c \geq \frac{|c| - u_c}{2} - m_c$$

When we place a new piece, $m_c$ can only INCREASE (mismatches lock
in). When $m_c$ pushes the inequality past the matched-budget, the
partial is infeasible for 480 — prune.

For score-targets below 480, weaken to $\geq T$ where $T$ is the target
matched-edges-per-color floor.

### Why this is novel

- Vol-25 incremental AC-3 maintains per-cell domain consistency, not
  per-color global budgets.
- Vol-44 cell-pair LP-UB computes a STATIC bound; this is a DYNAMIC
  per-partial bound.
- Vol-122 J7 HFFM analysed forced-pieces from color-pair supply but
  didn't turn it into a per-partial propagator.

The propagator is **incremental and O(1) per placement** if we
maintain per-color running counts of $u_c$ and $m_c$.

### Implementation plan (Day-3)

1. Augment vanilla_fast (NOT a clean rewrite — we keep the NW-bucket
   for speed) with per-color budget counters.
2. After each placement, update $m_c$ and $u_c$ for the up-to-4
   internal edges of the new cell.
3. At the start of each placement, check the propagator condition; if
   violated, skip directly to backtrack without exploring candidates.
4. Measure: nodes/sec, max_depth at 60s, vs vanilla_fast baseline.

### Falsifiable claim

If per-color budget propagation prunes meaningfully, STRATUM-Budgeted
should reach **higher max_depth** than vanilla_fast at equal wallclock,
even at lower nps. If max_depth is the same or lower, the propagator
fires too late to help (matches V147 INTAGLIO-DFS lesson: pruners that
fire AFTER damage-done are vacuous).

## Linked

- [[../sessions/vol-149]]
- [[rare-color-geography]] (vol-13: rare colors on border ring)
- [[piece-set-symmetries]] (vol-65: zero rotation symmetries, 5 twin pairs)
- [[../plans/INVENTION_NAMES_2026-05-19]]
