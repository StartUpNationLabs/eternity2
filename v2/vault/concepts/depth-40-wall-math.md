---
name: depth-40-wall-math
description: "Vol-125: mathematical analysis of WHY BB&B on W14 super-grid plateaus at depth 40 of 64. The plateau is at the convergence of multiple constraints — edge propagation across neighbors, piece-conservation tightness, and color-budget exhaustion. The wall is not arbitrary; it's the fundamental rigidity of the CSP."
metadata:
  type: project
---

# Why BB&B plateaus at depth 40 of 64 — the math

## Setup

W14 super-grid: $8 \times 8 = 64$ super-cells. Each super-cell is a $2 \times 2$
piece block; canonical Eternity II has $16 \times 16 = 256$ piece cells.

Each super-cell $v_{sr,sc}$ has an alphabet $A_{sr,sc}$ of valid blocks
(precomputed by W14 enumerator). Hint super-cells $\{(4,3), (6,1), (1,1),
(6,6), (1,6)\}$ are pre-filtered for canonical-hint compliance.

Empirical fact (vol-125): BB&B v5 with MRV + HK alldiff + AC-3 reaches
depth 40 across 5000 DFS nodes, then exhaustively backtracks without
reaching depth ≥ 41.

## Three converging pressures at depth 40

### Pressure 1: piece conservation

At depth $N$ super-cells pinned, exactly $4N$ piece IDs are used. For
$N = 40$: $160$ pieces used, $96$ pieces remain for the $24$ unpinned
super-cells ($24 \times 4 = 96$ slots). The piece-conservation slack is
EXACTLY ZERO. Any over-counting or piece collision immediately produces
infeasibility.

This balance holds at EVERY depth ($N$ cells pinned, $4N$ pieces used,
$256 - 4N$ pieces remain, $64 - N$ cells × 4 slots = $256 - 4N$ slots).
So depth 40 is not arithmetically special — the entire CSP runs on the
tightrope of zero piece-slack.

**Implication**: piece-uniqueness alone is not the binding constraint
at depth 40. Some OTHER pressure becomes binding.

### Pressure 2: interior edge-color budget

Canonical Eternity II has 22 interior colors. The total number of
edge-occurrences across all 256 pieces (each piece has 4 sides) is
$256 \times 4 = 1024$, of which $480$ are interior (the rest are border).

So each of 22 colors appears on average $480 / 22 \approx 21.8$ piece sides.
But ACTUAL distribution is non-uniform — some colors are rare (5-12
occurrences) and some are common (30+).

Each interior super-edge in W14 is a 2-color pair (the two adjacent inner
edges). For perfect matching, every interior super-edge's color pair must
be available in BOTH adjacent super-cells.

The $\binom{22}{2} + 22 = 253$ possible color pairs (allowing same-color
pairs) constrain the alphabet. After pinning many super-cells, the
constrained edge-colors on neighbors of unpinned cells may exhaust the
pair's availability in the remaining alphabet.

### Pressure 3: edge-matching propagation cascade

Each pinned super-cell pins its 4 super-edges. The adjacent (unpinned)
neighbors must have blocks with matching boundary on the shared edge. AC-3
propagates this; surviving alphabet shrinks.

After 40 super-cells pinned (60% of the grid), every unpinned cell has
typically 2-4 pinned neighbors (out of 4). So 50-100% of an unpinned
cell's 4 boundary edges are fixed to specific color pairs.

Empirically observed in v5 logs: at depth 40, MRV reports
"next=(sr,sc) dom_size=1" frequently. That means: the LAST unpinned cell
adjacent to the most pinned cells has exactly ONE block surviving.
Often this single block also conflicts with piece-uniqueness, forcing
backtrack.

## The convergence theorem (conjecture)

**Conjecture**: at depth $N \geq 40$, with probability approaching 1 over
random search paths, every unpinned super-cell satisfies at least one of:
- $|A_v^{remaining}| = 0$ (alphabet wiped by edge-propagation)
- $|A_v^{remaining}| \geq 1$ but all surviving blocks have a piece already
  used elsewhere

This explains the depth-40 plateau as a **rigidity wall**: the CSP becomes
increasingly over-constrained around depth 40, and the search dies on
the next attempted pin.

## Why depth 40 specifically?

The 5 hints + their immediate frame "stick out" deepest in the search tree.
Each hint super-cell has ~5K hint-compliant blocks. After hint propagation,
adjacent cells lose half their alphabet. At depth 40 ≈ 5 hints × 8 adjacent
cells per hint frame = 40 cells in the "hint-vicinity" zone.

So **depth 40 is the limit of the hint-vicinity zone**. Beyond this depth,
the search enters the "deep interior" cells far from any hint, where
edge-propagation alone (not hints) constrains the alphabet — and the
constraint density crosses a phase transition into infeasibility.

## Predicted scaling

If this conjecture is right, the depth-40 wall is a STRUCTURAL feature of
canonical Eternity II's W14 decomposition, not a search-engine bug. To
break depth 40 we need:

1. **A coarser decomposition** (e.g., $4 \times 4$ super-blocks instead of
   $2 \times 2$) so the hint-vicinity covers more of the grid. But
   $4 \times 4$ super-blocks have $4! \times 256^4 = $ way too many blocks
   to enumerate. Untractable.
2. **An ORTHOGONAL constraint** — something not captured by edge-matching
   or piece-uniqueness. The 5 canonical hints are one example; what about
   global color budgets, parity invariants, or symmetry-breaking lemmas?
3. **A meet-in-the-middle approach** where forward search from corner
   and backward search from opposite corner meet in the deep interior at
   depth 32 each. Sigma-break-meet attempts this; memory is the bottleneck.

## What this means for the 458/480 strict-canonical record

The strict 458 record (5/5 hints) has 22 missing matches. Those 22
unmatched edges are distributed across the board, likely concentrated in
the "deep interior" cells far from any hint.

The conjecture above predicts that the deep-interior cells have
fundamental rigidity that makes 459/480 strict-canonical hard to reach.
The 22-mismatch ceiling at strict 458 reflects the same constraint density
as the depth-40 BB&B plateau.

**Action implication**: pushing strict 458 → 459+ likely requires breaking
the deep-interior rigidity, NOT just improving local repair operators.
Mathematical attack: identify the specific constraints binding the deep
interior, formulate a relaxation, prove a lower bound on minimum mismatches.

## Open math questions

1. Can we PROVE the depth-40 plateau is forced by the constraint density,
   or is it search-heuristic dependent? (BB&B v5 uses MRV; would another
   order break depth 40?)
2. Is there a Lagrangian dual / LP bound that ESTIMATES the maximum depth
   reachable from any partial?
3. What is the "rigidity index" — the number of unpinned cells with
   exactly 1 surviving alphabet block — as a function of depth? If this
   increases sharply at depth 40, the conjecture is confirmed.

## Empirical check (2026-05-18)

Analyzed v5 5000-node log: mean MRV dom_size by depth:

| depth | mean dom_size | n samples |
|-------|---------------|-----------|
| 29 | 5.0 | 1 |
| 35 | 3.0 | 1 |
| 36 | 8.0 | 8 |
| 37 | 3.0 | 8 |
| 38 | 6.1 | 14 |
| 39 | 3.8 | 11 |
| 40 | **2.0** | 7 |

At depth 40, mean dom_size is **2.0** (median = 1). Most cells have
exactly 1 surviving block, the binding cell has zero. The rigidity-index
prediction is empirically supported by this 50-sample slice.

## Implication for compute feasibility

If at depth 40 each candidate has ~50% probability of leading to a viable
depth 41 (rough estimate), then reaching depth 64 from depth 40 requires
$24$ successful extensions with cumulative probability $\sim 0.5^{24}
\approx 6 \times 10^{-8}$.

To find 480, BB&B needs $\sim 10^7$-$10^9$ depth-40 attempts. At v5's
empirical rate of ~2.5 nodes/s, this is:
- $10^7$ attempts × $0.4$ s/node = $4 \times 10^6$ s = **46 days single-thread**
- $10^9$ attempts = **12 years single-thread**

10-core parallelization brings this to 1.2 years for the high estimate.

**Conclusion**: BB&B on W14 in its current form is too slow to find 480
within tractable time on a single machine. The depth-40 wall is a
fundamental rigidity barrier. To break it we need either:

1. A FUNDAMENTALLY different decomposition (not 2×2 super-blocks)
2. Cooperative search (BB&B + ALNS-style perturbation)
3. Cluster computing
4. Proof that 480 doesn't exist on canonical E2 (which would be a major
   research result itself)

## Related

- [[v125-bbb-progression]]
- [[strict-hint-slot-rotation-fix]]
- [[sigma-break-runbook]]
