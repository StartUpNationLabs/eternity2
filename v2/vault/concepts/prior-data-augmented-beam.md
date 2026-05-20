---
name: prior-data-augmented-beam
description: V150-V151 from-scratch builders saturate at 455/480 (K=16384 beam).
status: built
metadata:
  type: concept
---
# PRIOR — Data-Augmented Beam Value Ordering

**Status**: `built-measured` 2026-05-19 (Vol-155). **From-scratch ceiling lifted to 456/480** (from V151's 453).

## Genesis

V150-V151 from-scratch builders saturate at 455/480 (K=16384 beam).
The greedy local objective hits a ceiling because cell-greedy doesn't
know which pieces TEND TO BE good at which cells.

PRIOR adds an empirical-frequency informed value ordering. The
"corpus" of 1278 high-score boards in `database-400-480/` contains
empirical evidence: piece $p$ at cell $c$ is common in some basins.

## Math

For each (piece_id, position) pair, define:
$$\text{prior}(p, c) = \frac{\text{count}(\text{piece } p \text{ at cell } c \text{ in boards with score} \geq T)}{|\text{boards with score} \geq T|}$$

Default $T = 440$ (filter low-score boards). prior is a 256×256 matrix.

In V151 beam search at cell $c$, candidate (piece, rotation) is ranked by:
1. **Primary**: matched-edges delta from this placement (current).
2. **Secondary (NEW)**: `prior(piece, c)` — higher prior wins ties.

This influences the WAY a beam state is extended, not the search topology.
The constructed board is still from-scratch (no anchoring on any single
board), just biased by the corpus distribution.

## Why this might lift the ceiling

Two reasons:
1. **High-score basins SHARE structural elements**. PALIMPSEST analysis
   (V129) showed many boards have similar piece-at-position assignments
   in some regions. The prior captures this without committing to a
   single basin.
2. **Beam diversity preserved**. The prior is a SOFT bias (tiebreak),
   not a hard constraint. K-1024 beam still explores many alternatives.

## Falsifiable

Run V151 with PRIOR bias enabled. Compare max score to plain V151 at
same K + same wallclock budget.

Expected: +2 to +10 score points. Anything < +1 means the prior
information is too dilute / pieces-at-positions don't transfer.

## Linked

- [[vol-155]] (to create)
- [[weaving-beam]] (V151 parent: 455 ceiling)
- [[INVENTION_NAMES_2026-05-19]]
