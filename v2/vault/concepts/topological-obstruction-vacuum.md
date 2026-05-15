# Topological obstruction is vacuous on E2 — vol-65 note

**Status**: `built` (negative result) — vol-65 (2026-05-15).
**Type**: structural observation.

## The setup

Eternity II can be formulated as a fiber bundle:
- **Base**: the 16×16 cell-grid graph G.
- **Fiber at cell c**: F_c = set of (piece, rotation) tuples valid
  at c (after frame constraint).
- **Transition functions**: for each edge (c1, c2) in G, the
  compatibility relation R(c1, c2) ⊂ F_{c1} × F_{c2}: pairs whose
  facing-side colors match.

A valid E2 assembly is a SECTION of this bundle: a choice s(c) ∈ F_c
for each cell c, such that (s(c1), s(c2)) ∈ R(c1, c2) for every
adjacent pair.

The CECH 1-cocycle of this bundle measures whether sections can be
"glued together" consistently across overlapping patches.

## The vacuum

**The 16×16 grid graph G is contractible** (it's a simply-connected
2D region). On contractible spaces, every fiber bundle is TRIVIAL —
the cocycle is automatically exact, and the cohomology class
H^1(G, ·) = 0.

**Conclusion**: there is no topological obstruction to assembling
E2. The puzzle's hardness is **purely combinatorial**.

## What this rules out

- **Sheaf cohomology / homotopy class arguments** for proving E2's
  hardness or for bounding its score.
- **Obstruction theory** in the Čech sense.
- **Bundle-trivialization tricks** that would reduce E2 to a
  homotopically-simpler problem.

## What remains

E2's hardness lives in the COMBINATORIAL structure of the
compatibility relations R(c1, c2), not in the topology of the base
or the fiber.

The relevant invariants are:
- **LP polytope facets** (cluster MIPs in vol-62)
- **Σ-orbit structure** (vol-65)
- **PSM-matching polytope** (vol-65)

Each is a combinatorial-not-topological measure.

## Connection to maximally-adversarial thesis

This is consistent with [[e2-maximally-adversarial-thesis]]: every
COMBINATORIAL axis is maxed out, while the TOPOLOGICAL axis is
vacuously trivial (no obstruction possible). Selby-Riordan didn't
need to engineer topology — it's automatic.

## Implications for vol-66+ algorithms

- Don't try to compute Čech cocycles or sheaf cohomology — vacuous.
- Don't propose algorithms that exploit base-space topology.
- DO use combinatorial polytope analysis (LP, MIP, matching, σ-orbits).

## Linked

- [[e2-maximally-adversarial-thesis]]
- [[mip-local-optimality-459]]
- [[piece-side-matching]]
