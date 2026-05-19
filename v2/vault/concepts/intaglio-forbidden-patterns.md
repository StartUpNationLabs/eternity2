# INTAGLIO — Carve Forbidden Patterns

**Status**: `built` (Vol-138, 2026-05-19)
**Origin**: Brainstorm reservoir round-5 (twin of CONCRETION)
**Files**:
- `scripts/v138_intaglio_2cell.py`
- `scripts/v138_intaglio_2x2.py`

## Definition

For each small subgrid configuration (k cells, specific piece IDs
assigned), check if SOME rotation assignment makes it color-feasible.
A subgrid that is feasible for NO rotation combination is "forbidden"
and prunes wherever it would appear.

Twin of CONCRETION (which sought FORCED pairings — refuted on
canonical). INTAGLIO seeks FORBIDDEN pairings — succeeds.

## Measurements on canonical 16×16/22

### 2-cell adjacency (V138-T1)

For each ordered pair $(i, j)$ where $i \ne j$, check if $p_i$'s E
matches $p_j$'s W under some rotation pair.

| Direction | Pairs | Feasible | Forbidden |
|-----------|-------|----------|-----------|
| Horizontal | 65 280 | 30 030 (46.00%) | **35 250 (54.00%)** |
| Vertical | 65 280 | 30 030 (46.00%) | **35 250 (54.00%)** |

**54% of 2-cell adjacencies are forbidden** on canonical.

Per-piece out-degree: min=35, max=151, mean=117.3.

### 2×2 patch feasibility (V138-T2)

Sample 100 000 random 4-tuples of interior pieces (196 interior on
canonical). Check if SOME rotation assignment makes the 2×2 patch
internally consistent.

**Result: 0.282% feasible, 99.72% FORBIDDEN.**

Of $\binom{196}{4} \times 24 \approx 1.46 \times 10^{10}$ possible
patches, only $\sim 4 \times 10^7$ are buildable.

## Why this matters

- 2-cell: 54% of piece-pairs pruned per board edge.
- 2×2: 99.72% of patches forbidden. Any destroy-then-repair that
  produces a forbidden 2×2 can be rejected instantly.

## Practical use

1. **ALNS-with-INTAGLIO propagator**: precompute the ~41M feasible
   2×2 patches (hash table, ~ 1 GB). Reject repairs producing
   forbidden patches.
2. **DFS pruner**: check d-th 2×2 patch against feasible set; prune.
3. **Search-space upper bound**: # of constructible boards is
   exponentially smaller than $4^{256} \cdot 256!$.

## Comparison to CONCRETION

CONCRETION (V127): asked "what's RIGID?" → nothing on canonical.
INTAGLIO (V138): asks "what's EXCLUDED?" → 99.72% of 2×2 space.

The Selby-Riordan piece set avoids forced moves but inadvertently has
a TIGHT 2×2 structure.

## What's still open

- Build the feasible 2×2 hash table.
- Wire into ALNS repair: reject forbidden-2×2 producing repairs.
- 3-cell L-shapes and 2×3 / 3×3 patches.

## Linked

- [[concepts/concretion-rigid-molecules]] (refuted twin)
- [[concepts/grain-polycrystalline]]
- [[plans/EXTERNAL_BRAINSTORM_2026-05-18]]
