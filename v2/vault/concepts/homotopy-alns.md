# Homotopy-ALNS — β₁-targeted defect-cycle destroy operator

**Status**: `design` — vol-62 (2026-05-15).
**Type**: INVENTED ALGORITHM (per user directive vols 61-70).
**Inventor**: this autonomous run.

## Motivation

Standard ALNS picks destroy regions semi-randomly (random_region,
worst_window, conflict_driven). These operators don't respect the
**topology** of the defect graph — the structure of where mismatches
actually live.

On E2 records (vol-32 458, our 459, cross-machine 459), all defects
cluster in connected components, often forming "almost-cycles"
(closed loops where mismatches go around an interior region). Closing
such a cycle requires coherent re-tiling of the interior, not random
local repair.

Vol-18 R5 measured β₁ of the defect graph on real boards as a
DIAGNOSTIC. The new idea is to USE β₁ generators as destroy targets.

## The math

### Defect graph

Given a board `B` on a 16×16 grid:
- Nodes `V` = cells with at least one mismatched edge.
- Edges `E` = pairs `(c, c')` where `c, c'` are adjacent cells and
  their shared edge is a color mismatch.

The defect graph is a subgraph of the cell-adjacency grid. Its
topology characterizes the structure of defects on the board.

### First Betti number

For a graph `G = (V, E)`:
- `β₀` = number of connected components.
- `β₁` = |E| - |V| + β₀ = number of independent 1-cycles.

`β₁` counts the cyclomatic complexity — the number of "loops" in the
defect graph that cannot be reduced to combinations of simpler loops.

### 1-cycle generators

`β₁` independent 1-cycles form a basis of the cycle space (over GF(2)
or Z, depending on framework). A spanning tree `T` of `G` gives a
natural basis: for each non-tree edge `e ∈ E \ T`, the unique path in
`T` connecting `e`'s endpoints, plus `e` itself, is a 1-cycle. There
are exactly `|E| - |V| + β₀ = β₁` such non-tree edges, giving β₁
cycle generators.

### Cycle interior

A 1-cycle in the grid bounds a planar region (since the grid is
planar). For each cycle, define `Interior(cycle)` = cells inside the
loop (in the planar embedding of the cell-adjacency grid).

There's an ambiguity: a cycle bounds TWO regions (inside and outside).
We pick the smaller one as the canonical interior (Jordan curve
theorem convention).

## The algorithm

Given a current board `B` with mismatches:

```
def Homotopy_ALNS_step(B):
    G = defect_graph(B)
    if G is empty: return B  # solved
    T = spanning_tree(G)
    cycles = []
    for e in E(G) \ T:
        cycle = path_in_T(e.u, e.v) + [e]
        cycles.append(cycle)
    cycles.sort(key=lambda c: size_of_interior(c))  # smallest first
    
    for cycle in cycles:
        interior = compute_interior(cycle)
        B' = remove_pieces(B, interior + cycle.cells)
        B' = refill(B', interior + cycle.cells)
        if score(B') > score(B):
            return B'  # accept
    return B  # no cycle was improvable
```

Where:
- `remove_pieces(B, cells)` un-pins the listed cells from B.
- `refill(B, cells)` runs CP or MWPM matching restricted to the
  removed cells (returning all other cells to their original state).
- `score(B)` = matched internal edges.

### Variants

- **Coherent**: refill with CP-MaxScore objective restricted to the
  cells (must reach a placement with all listed cells re-filled).
- **Probabilistic**: refill with a stochastic operator (e.g.,
  MWPM-defect-pair followed by SA polish).
- **Adversarial**: allow `B'` worse than `B` at SA temperature (so
  the algorithm escapes the current basin if no cycle is locally
  improvable).

## Why this is INVENTED, not a variant

- Existing destroy operators (random, worst_window, etc.) don't look
  at the defect graph topology.
- β₁-cycle-targeted destroy is genuinely new. No published method
  uses defect homology as a destroy heuristic.
- The phrase "defect homology" exists in materials science (crystal
  lattices), but not in CSP solver literature.
- Naming claim: "Homotopy-ALNS" or "β₁-Destroy" or
  "Cycle-Closing-Repair" — none of these are in the E2 literature.

## Expected behavior

### Best case
- All 21 mismatches (on a 459 board) form ~5-8 cycles.
- Each cycle has a small interior (10-30 cells).
- Closing a cycle reduces mismatch count by 2-4.
- Iterating: 459 → 461 → 463 → ... → 469 (community ceiling).

### Worst case
- 21 mismatches form a single huge cycle with interior 100+ cells.
- Refilling 100 cells coherently is too hard for CP/MWPM in budget.
- Algorithm stalls at 459.

### Most likely
- Some cycles close, others don't.
- Net improvement: 1-3 points beyond 459.
- Output: 460-462.

## Implementation plan (vol-62)

### Day 1: math + Python prototype

1. Write `vol62_homotopy_alns.py`:
   - Defect graph from board JSON.
   - Spanning tree (DFS-based).
   - β₁ computation.
   - 1-cycle generators (non-tree edges + tree paths).
   - Interior computation (planar embedding via grid coordinates).
2. Test on the local 459 board (`output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json`):
   - Count cycles, compute interiors, identify smallest.
3. Verify by hand: do the cycles match the visual mismatch geometry?
   (All mismatches in rows 11-14, so cycles should live there.)

### Day 2: destroy operator integration

1. Implement `CycleClose` as a new ALNS destroy op.
2. Refill: try MWPM-defect-pair first (existing op), fall back to CP.
3. Wire into `alns_only` or write a new bin `homotopy_alns_only`.

### Day 3: measurement + close

1. Run on local 459 partial: does cycle-closing beat random destroy?
2. Run on stage 2 of vol-61's pipeline (after ALNS minimal): does it
   bridge to 460+?
3. Variance: multiple seeds.
4. Write vault/sessions/vol-62.md with measurements.

## Pre-checks before building

- Vol-18 R5 already has β₁ measurement code in
  `scripts/cell_defect_mwpm.py` or similar. Reuse if possible.
- The MWPM-defect-pair operator exists in localsearch crate; check
  if it can be retargeted to specific cells.

## Open questions

1. **Cycle interior definition**: which face of a 1-cycle is "interior"?
   We pick the smaller-area face. But that's a heuristic; the cycle
   might be better closed by re-tiling the LARGER face. Both should
   be tried.

2. **Refill via CP vs MWPM**: CP is more powerful but slower. MWPM is
   fast but limited to pair-matching. For small cycles (interior ≤
   10), MWPM probably suffices. For larger cycles (≤ 50), need CP.

3. **Cycle interactions**: closing one cycle may CREATE new defects
   elsewhere (especially at the cycle's boundary). The algorithm
   needs to handle non-monotone iterations.

4. **Acceptance criterion**: pure improvement, or SA-style worse-than-
   current accepted at temperature? Probably SA — pure improvement
   stalls fast.

## Linked

- [[../sessions/vol-62]] — will exist once vol-62 starts
- vol-18 R5 (homology measurements, diagnostic only)
- memory: `feedback_vols_61_to_70_invented_algos`
