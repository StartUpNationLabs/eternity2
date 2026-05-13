# Session — vol-10

**Theme**: Static spectral analysis. Per-piece structural mining (pieces 17/38/62, multiset equality).
**Raw**: [[../sessions/archive/raw/RESEARCH_NOTES_10|RESEARCH_NOTES_10.md]]

## What was attempted

- PCA on 256×23 piece-histogram space.
- Graph Laplacian spectrum (L_0 / L_freq / L_avail).
- Position-aware pairwise PCA.
- Per-piece combinatorial structure mining.

## What was measured / kept

- **PCA top-1 ratio 0.0856** (vs iid baseline 0.0455) — 1.88× iid baseline. Selby-Riordan flatness confirmed; top-3 PCs only 25% of variance.
- **Rank-65 pairwise interaction matrix** of 88 possible: 37/65 dims for 80% Frobenius energy. Modest, not dominant.
- **Piece 17**: unique inward-k constraint (forces second-ring placement to ~22% of cells).
- **Piece 38**: unique inward-l constraint.
- **Piece 62**: no hint-adjacency possible (~80 placements forbidden).
- **Multiset-equality (NS-1)**: closed-ring boards satisfy {12,12,12,12,12} rare-color multiset. Foundation for vol-11 [[ns1-deficit]] measurement.

## What was refuted

- **Static spectral structure** as a search lever: closed. λ_2 degenerate, no spatial bottleneck visible.
- **Histogram clustering** as a discriminator: ruled out (PCA flat).
- **Low-rank pairwise interaction**: only partial — 37 dims modest, not dominant. Doesn't drive the search.

## Concepts touched

- [[selby-riordan-generator]] (PCA-flatness measurement)
- [[ns1-deficit]] (multiset invariant identified here, measured vol-11)
- [[community-corpus]] (per-piece community insights, onesmallstep Discord)

## Insight

The Selby-Riordan generator successfully **defeats global static structure detection** (PCA, Laplacian, pairwise). But per-piece *exact* structure (pieces 17/38/62) leaks through — these forced placements are not statistical, they're combinatorial.

→ **Don't bet on global statistics. Do exploit per-piece exact structure.**

## Linked memory

- `project_e2_state` (vol-10 row)
