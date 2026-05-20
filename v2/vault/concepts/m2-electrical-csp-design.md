---
name: m2-electrical-csp-design
description: "M2-extension: use electrical-resistance heuristic to guide CSP search from a CLEAN SLATE. Effective resistance as a value-order or variable-order signal. Aims to construct partial boards with low-resistance topology, which (per K11 corpus finding) correlates with high-score basins."
metadata:
  type: project
status: partial
---

# M2-extension — Electrical CSP heuristic (design)

## Origin

User direction 2026-05-17 ~16:13 CEST: "electricity sounds very interesting,
very curious to see. Can we use it to better find solutions from maybe
even a clean slate?"

## Background

M2 (effective resistance) showed that the structurally STRONGEST 5/5-hint
board in our corpus (`RECORD_TIE_457_blackwood_mrv_5min_seed10`) has the
LOWEST corner-to-corner effective resistance (R_avg = 3.4581 vs 459's
3.5601).

Hypothesis: building boards with LOW R_eff from the start may produce
basins with higher matched-edge ceilings.

## Design

### Variable order: effective-resistance-reduction priority

Standard MRV picks the unfilled cell with the smallest remaining domain.

**ER-MRV (Effective-Resistance MRV):** picks the unfilled cell whose
HYPOTHETICAL ADDITION (with the best-matching piece) would MAXIMIZE the
effective-resistance reduction in the partial matched-edge graph.

Cost: for each unfilled cell c, simulate adding 1-4 matched edges to its
neighbors. Compute R_eff. Pick c with largest gain. O(|unfilled| × |V|^3)
= 256 × 256^3 = 4×10^9 per search node. Too slow.

### Cheaper approximation: heat kernel proximity

Approximate effective resistance via the HEAT KERNEL exp(-tL) of the
graph Laplacian. For small t, heat kernel measures local connectivity;
for large t, measures global structure.

Pre-compute heat kernel once per filled-cell snapshot. Use it to rank
cells.

### Even cheaper: hint-anchored Wiener index

Wiener index = sum of shortest-path distances. Lower Wiener = more
compact graph. Cells whose addition would maximally reduce Wiener
distances between hint positions are prioritized.

### Concrete algorithm

```
1. Start with hints placed (5 cells).
2. While unfilled cells exist:
   a. For each unfilled cell c, compute its "electrical priority":
      sum over hint-pairs (h1, h2) of [R_eff(h1, h2) - R_eff(h1, h2 | c filled)]
   b. Pick the cell c with highest priority.
   c. For c, run CSP-fill (try valid pieces in MRV-LCV order).
   d. If placement found, commit. Else backtrack to previous cell.
```

## What's NEW

- Existing E2 search uses cell-position heuristics (border-first, hint-link,
  etc.) — STRUCTURAL but not GRAPH-THEORETIC.
- ER-MRV uses the matched-edge GRAPH's electrical properties — fundamentally
  different signal.
- The graph property evolves as we fill cells — it's a DYNAMIC HEURISTIC.

## Tractability concerns

- O(N^3) Laplacian pseudo-inverse per CSP node would kill performance.
- Heat kernel approximation: O(N k) for small k (using Krylov subspace).
- Wiener index: O(N²) via Floyd-Warshall or BFS.

Heat kernel + small Krylov might be tractable per-node.

## Path forward

1. **PoC: passive observation**. For multiple existing partial boards
   (J1-hinted v2 partial, 459, 458, etc.), compute the ER-priority
   ordering. Does it match where pieces SHOULD go to reach a record?
2. **Active integration**: implement as a custom path in `vanilla_path`
   bin. Generate a partial via ER-priority ordering. Score it.
3. **Compare** vs row-major, border-first, hint-link.

## Status

`design-only`. Implementation depends on tractability assessment.

## Linked

- [[m13-holographic-fft-finding]] (related findings)
- [[k11-corpus-cross-validation]] (the trade-off insight)
- [[inv3-border-dp-seed]] (related path construction)
