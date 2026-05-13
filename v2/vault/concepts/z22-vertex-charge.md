---
tags: [concept, structural, lattice-gauge]
status: built-fingerprint
origin-vol: 7
---

# Z_22 vertex charge

**Status**: `built` (vol-7 measurement); not yet used as propagator
**Origin**: vol-7
**Files**: `scripts/z22_charge_fingerprint.py`

## Definition

Each interior grid vertex is incident to 4 edges (NSEW). Define the **vertex charge** at vertex v as:
```
q(v) = sum of edge colors at v, mod 22
```
(Colors 1-22 are the abundant set after rare-border-exclusivity; mod 22 because the 22 abundant colors form a cyclic gauge group under the Z_22 lattice-gauge framing.)

## Vol-7 measurement

On 29 plateau boards (≥440):
- **44-50 vertices with q ≠ 0** per board (mean ~47 of 225 interior vertices).
- **Spatially localized**: the nonzero-charge vertices cluster in the same hotspot region as the universal-mismatch geometry (rows 10-13, cols 4-13).

→ Z_22 charge is an **alternative fingerprint** of mismatch geometry, viewed through a gauge-theoretic lens.

## Theoretical framing (Kogut / Zohar)

- Each edge color is a Z_22 "link variable" in a 2D Yang-Mills theory.
- A full E2 solution would have q = 0 at every vertex (gauge-invariant ground state).
- Mismatches manifest as nonzero charge → "disclination" defects.

This connects to **disclination-string moves** (vol-7 proposal): a charge can be transported by simultaneously flipping a chain of edges. Speculative; not built.

## Refuted as static lower bound

**Chessboard parity** (vol-7): the natural 2-coloring of the vertex lattice gives cross-class cancellation. Net charge = 0 trivially. No useful lower bound.

## What's still potentially useful

- As a **diagnostic** for visualizing where Z_22 defects cluster (mismatch geometry, gauge view).
- As a **propagator constraint** in late search: enforce q(v) = 0 at vertices known to be in the "good" region. Not built.

## Linked concepts

- [[mismatch-geometry]] — what the Z_22 picture overlays
- [[selby-riordan-generator]] — generator that flattens this signal globally but leaves it hotspot-concentrated

## Linked memory

- `project_e2_state` (vol-7 row)
