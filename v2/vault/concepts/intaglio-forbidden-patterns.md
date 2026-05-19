# INTAGLIO — Carve Forbidden Patterns

**Status**: `built` (Vol-138 + 139, 2026-05-19)
**Origin**: Brainstorm reservoir round-5 (twin of CONCRETION)
**Files**:
- `scripts/v138_intaglio_2cell.py`
- `scripts/v138_intaglio_2x2.py`
- `scripts/v139_count_forbidden_in_records.py`

## Definition

For each small subgrid configuration (k cells, specific piece IDs
assigned), check if SOME rotation assignment makes it color-feasible.
A subgrid that is feasible for NO rotation combination is "forbidden"
and prunes wherever it would appear.

Twin of CONCRETION (which sought FORCED pairings — refuted on
canonical). INTAGLIO seeks FORBIDDEN pairings — succeeds massively.

## Measurements on canonical 16×16/22

### 2-cell adjacency (V138-T1)

For each ordered pair $(i, j)$ where $i \ne j$, check if $p_i$'s E
matches $p_j$'s W under some rotation pair.

| Direction | Pairs | Feasible | Forbidden |
|-----------|-------|----------|-----------|
| Horizontal | 65 280 | 30 030 (46%) | **35 250 (54%)** |
| Vertical | 65 280 | 30 030 (46%) | **35 250 (54%)** |

### 2×2 patch feasibility on RANDOM piece-tuples (V138-T2)

Sample 100K random 4-tuples of interior pieces. Check feasibility.

**Result: 0.282% feasible, 99.72% FORBIDDEN.**

### Forbidden 2×2 count in REAL DB BOARDS (V139)

For each board in `database-400-480/` (1278 boards), count
forbidden 2×2 patches (out of 225 total patches per 16×16 board).

| Score bucket | n | min | max | mean | median |
|--------------|---|-----|-----|------|--------|
| LOW (<440) | 340 | 91 | 127 | 108.6 | 109 |
| MID (440-459) | 915 | 51 | 71 | 60.5 | 60 |
| **HIGH (≥460)** | **23** | **19** | **34** | **27.9** | **29** |

**Forbidden 2×2 count is STRONGLY anti-correlated with board score.**

## The 4× gap

Low-score boards: ~109 forbidden 2×2.
High-score boards (≥460): ~29 forbidden 2×2.

The 461 record has ~29 forbidden patches. A perfect 480 board has 0.
**To reach 480, we need to eliminate ~29 forbidden patches.**

The 461→480 score gap (19 edges) ≈ the forbidden-patch gap (29
patches). Each forbidden patch represents on average ~0.65 mismatched
edges. So fixing forbidden patches IS fixing mismatches, but at
2×2-granularity rather than per-edge.

## Why this matters

This gives us a **NEW SECONDARY OBJECTIVE** beyond matched edges:
forbidden 2×2 count. Two boards with the same matched-edge score
can have different forbidden-patch counts; the one with fewer
forbidden patches is presumably closer to a valid completion.

**Practical use**:
1. **ALNS as repair filter**: reject any repair that increases
   forbidden-patch count.
2. **ALNS as secondary objective**: lexicographic tiebreak —
   matched_edges first, then -forbidden_patches.
3. **Pruning in destroy-target selection**: focus destroy on regions
   containing forbidden 2×2 patches.

## Comparison to CONCRETION

CONCRETION (V127): asked "what's RIGID?" → nothing on canonical.
INTAGLIO (V138-139): asks "what's EXCLUDED?" → 99.72% of random 2×2
space is forbidden; even our 461 record has 29 forbidden patches.

The Selby-Riordan piece set avoids forced moves but inadvertently
has a TIGHT 2×2 structure.

## What's still open

- Rust impl of the 2×2 feasibility check.
- Wire into alns_e2 as a repair filter (compare to baseline).
- 3-cell L-shape / 2×3 / 3×3 patches: probably stronger pruning.
- Build a hash table of feasible patches; query in constant time.

## Linked

- [[concepts/concretion-rigid-molecules]] (refuted twin)
- [[concepts/grain-polycrystalline]]
- [[concepts/constraint-density-vs-alns-gap]]
- [[plans/EXTERNAL_BRAINSTORM_2026-05-18]]
