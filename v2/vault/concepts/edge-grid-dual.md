---
name: edge-grid-dual
description: Switch search variables from CELLS (256, each with ~1024 piece-rot values) to EDGES (480 internal, each with 23 color...
status: partial
metadata:
  type: concept
---
# Edge-grid dual

**Status**: `partial` — Kempe-chain probe was null, full reformulation not built
**Origin**: vol-20 (catalog N1), explored vol-21
**Files**: `crates/bench-audit/src/bin/edge_kempe.rs`

## Definition

Switch search variables from CELLS (256, each with ~1024 piece-rot values) to EDGES (480 internal, each with 23 color values).

A move flips one edge color. The two adjacent cells then need pieces whose corresponding side matches the new color. Piece-uniqueness must still hold globally.

The promise: a 76-cell σ-cycle in cell-space might be a 5-edge-flip path in dual-space.

## What got built (vol-21)

`edge_kempe.rs` — Phase 1/2/3 probe:
- Phase 1 single-edge 2-piece flip: 0/23 mismatched edges had a fix.
- Phase 2 alt-piece counts: 18 k=3 alts across 38 mismatch cells, 466 k=2 alts.
- Phase 3 cycle search: 6 intra-mismatch arrows, 0 net-positive 2-cycles, 0 net-≥0 3-cycles.

## What this revealed

Result was null, but it led to:
- The realization that piece-uniqueness is the binding constraint, not edge-feasibility.
- Building [[relaxed-bound]] which probes "what if uniqueness were relaxed."

## What's still unbuilt

- A real dual representation with edge-flip operators and incremental piece-rederivation.
- Kempe-chain operator (multi-edge flip in connected component of 2 colors).

Likely `wont-do`: the relaxed-bound work superseded this conceptually. The dual would be useful only if we needed to enumerate edge-configurations, but bound-ascent already optimizes that landscape.

## Linked concepts

- [[relaxed-bound]] — supersedes this conceptually
- [[bound-ascent]] — the relaxation-based optimizer
