---
tags: [concept, propagator, global, alldiff, candidate]
status: unbuilt
origin-vol: 23
priority: MEDIUM
---

# AllDifferent — Régin's matching filter (1994)

**Status**: `unbuilt`, candidate for piece-uniqueness enforcement
**Origin**: Régin, "A Filtering Algorithm for Constraints of Difference in CSPs", AAAI'94
**Files**: — (target: `crates/propagators/src/alldiff_regin.rs`)

## Definition

Achieves **GAC on the AllDifferent constraint** over `n` variables with domains in `D` via bipartite matching:

1. Build bipartite graph `G = (X ∪ V, E)` with `(x, v) ∈ E` iff `v ∈ D_x`.
2. Compute maximum matching `M` (Hopcroft–Karp, O(E·√V)). If `|M| < n` ⇒ infeasible.
3. Orient edges: matching edges value→variable, non-matching variable→value. Add a sink `t` with edges from all unmatched values.
4. Compute strongly connected components (Tarjan O(V+E)).
5. A non-matching edge is in **some** maximum matching iff its endpoints share an SCC **or** the value is reachable from an unmatched-value (and reaches it). Edges not in any max matching → values not supported by GAC → **prune**.

## Complexity

- Per fixpoint: **O(n · √n · d)** for matching + **O(n·d)** for SCC.
- Incremental version (Régin 1995, Mehlhorn–Thiel 2000): only re-match along augmenting paths after a few removals; usually O(d) per domain change in practice.

This is the **canonical "global constraint with polynomial GAC"** result that founded the field of global constraints in CP.

## Strength vs simpler alternatives

| level | propagator | E2 piece-uniqueness effect |
|---|---|---|
| FC (forward checking) | remove placed piece from each remaining cell domain | what we currently do at search nodes (implicit, via domain rep) |
| Hall-filter | k-tuple of cells with combined `|D| ≤ k` ⇒ those k pieces forced into them, prune from others | not enforced |
| Régin GAC | full matching-based pruning | not enforced |

## E2 applicability

**Conditional yes — moderate priority.** Reasoning:

**Why it could help on E2:**
- Piece-uniqueness is a 256-variable AllDifferent over piece IDs. Currently enforced *only* end-state. Every CSP search node has a partial assignment and could in principle invoke Régin's filter on the residual 256 - depth pieces.
- At depths 100-200 (where our search struggles), domains are tight and Hall-style infeasibilities become realistic. Could detect "the 30 unplaced corner/edge/interior buckets cannot bijectively match the remaining cells" *before* AC-3 catches the cell-level contradiction.
- Closes a real gap vs Joe-style search ([[mcgavin-engine]]) that does aggressive piece-pool pruning.

**Why it might disappoint:**
- AC-3 + gacolor already detect most piece-uniqueness violations at the color level (you can't place two copies of the same piece because gacolor matches color-half-edges to piece-half-edges).
- Régin's filter cost (sqrt-scaling matching) is non-trivial per node; the question is whether it prunes enough to amortize.
- Variable domain is (piece × rotation), not pure piece. The clean AllDifferent is over **piece ID** with the rotation marginalized — `D_cell(piece) = { p : ∃r, (p,r) ∈ D_cell }`. This projection is essentially free given [[bitset-domain-rep]].

**Implementation sketch (vol-24 stretch goal, ~3 days)**:
1. Projected piece-domain per cell: `piece_mask[c] = OR over rotations of D_cell`.
2. After AC-3 fixpoint, call `alldiff_regin(piece_mask[c] for unfilled c)`.
3. If a piece `p` is GAC-removed from cell `c`, remove all `(p, r)` for any `r` from `D_cell[c]`. Re-queue affected arcs.
4. Trail: same as AC-3 (per-domain bit changes).
5. Gate: only run at depths ≥ K (cost vs benefit; tune K).

**Soundness under Blackwood**: piece uniqueness is **strict** even in Blackwood — break_index allows mismatched colors, not duplicate pieces. → **Régin AllDifferent is SAFE under `BLACKWOOD_RAW`** (unlike AC-3 and gacolor). This is potentially a big deal: it's a *strong* propagator that survives the break-allowance regime and could close part of the vol-15 BLACKWOOD_RAW pruning gap.

## Linked concepts

- [[gacolor]] — already enforces a related matching, but per-color half-edges, not per-piece
- [[ac3]] [[ac2001]] — value-level AC, layer below
- [[blackwood-algorithm]] — the regime where AC-3/gacolor become unsound but AllDiff stays sound
- [[mcgavin-engine]] — the reference engine that does aggressive piece-pool reasoning

## Linked memory

- `project_e2_vol14_mcgavin_blackwood_gap_analysis` — McGavin's piece-bucket pruning is the missing layer
- `project_e2_vol15_blackwood_results` — BLACKWOOD_RAW dropped soundness; this propagator restores some
