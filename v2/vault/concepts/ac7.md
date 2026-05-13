---
tags: [concept, propagator, ac, reference]
status: unbuilt
origin-vol: 23
---

# AC-7 / AC-Inference (Bessière, Freuder, Régin)

**Status**: `unbuilt`, reference
**Origin**:
- Régin, "An arc-consistency algorithm optimal in the number of constraint checks", ICTAI'94
- Bessière, Freuder, Régin, "Using Constraint Metaknowledge to Reduce Arc Consistency Computation", AIJ 1999
**Files**: —

## Definition

AC-7 builds on [[ac6]] but exploits **constraint metaknowledge** — properties known about the predicate without enumerating tuples. The two main pieces:

1. **Bidirectionality** — if `b` supports `a` in `C(xi,xj)`, then in a symmetric constraint `a` supports `b` in `C(xj,xi)`. Halves checks for symmetric constraints (equality, distance, edge-matching).
2. **AC-Inference** — generic framework where the propagator queries the constraint object for *"what's the smallest `b ≥ k` that could support `a`?"*. If the constraint can answer this without scanning the domain (e.g. arithmetic / monotone constraints, à la [[ac5]]), AC drops below O(e·d²).

AC-7 is asymptotically optimal in **the number of constraint checks**, not just time; this is the strongest theoretical statement in the family.

## Complexity

- O(e·d²) worst case time; in practice many fewer constraint checks than AC-6.
- Same space as AC-6: O(e·d + n·d).

## Where it shines

Constraints with rich semantics: arithmetic, distance, intervals, monotone — anywhere a "next support" query has a non-trivial closed form. Edge-matching is **symmetric** (color a on left equals color a on right) so bidirectionality applies, but the "find next support" query is just a table scan.

## E2 applicability

**Skip as a separate engine**, but **steal the bidirectionality idea**:
- Our adjacency is symmetric: if rotation `r₁` of piece `p₁` at cell `c₁` supports `(p₂, r₂)` at neighbour `c₂` via shared color `k`, the converse holds.
- Vol-16's `same_piece_rots` LUT is half of this story; the missing half is sharing the support found on the `c₁ → c₂` revision with the immediate `c₂ → c₁` revision in the same propagation round.
- Estimated lift: a constant factor on AC-3 revisions, probably under the noise floor vs the [[ac2001]] residual-support win. Not a priority.

## Linked concepts

- [[ac6]] — base algorithm
- [[ac3]]
- [[ac2001]] — different but complementary axis (coarse + residual)
- [[ac-family-comparison]]
