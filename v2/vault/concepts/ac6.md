---
tags: [concept, propagator, ac, reference]
status: unbuilt
origin-vol: 23
---

# AC-6 (Bessière 1994)

**Status**: `unbuilt`, reference
**Origin**: Bessière, "Arc-Consistency and Arc-Consistency Again", AIJ 65(1), 1994
**Files**: —

## Definition

Fine-grained AC keeping AC-4's optimal worst case while fixing the space blow-up. For each pair `(xi, a)` AC-6 stores **only one** current support `b ∈ D_xj` per neighbour `xj`, not the full support list. When `b` is removed, the algorithm searches forward in `D_xj` (starting from the lex-successor of `b`) for the next support; if none, `(xi, a)` is deleted.

The "lazy support" idea — only look up the next support when the current one dies — is the core insight.

## Complexity

- Time: **O(e·d²)** worst case (same as AC-4, optimal).
- Space: **O(e·d + n·d)** — the win over AC-4.
- Practical: much faster than AC-4 on real instances because init does not enumerate full support lists.

Bessière (1995, with Régin) extended this with **bidirectional support** — re-using a support found from `xi → xj` as the seed for `xj → xi`, halving constraint checks.

## Relation to AC-7

[[ac7]] is AC-6 + metaknowledge: it uses constraint properties (e.g. symmetry) to skip checks. AC-6 is its purely-syntactic baseline.

## E2 applicability

**Skip — for the same reason as [[ac4]]**, slightly weaker:
- Per-value "current support" pointers add a per-domain-value cell of state; with d=764 over 256 cells that's ~200k pointers to trail across backtracks. Workable but heavy.
- The bitset domain rep ([[bitset-domain-rep]]) doesn't carry per-value state cheaply.
- AC-2001 packs the same residual-support idea into a coarse-grained loop that fits our existing AC-3 queue almost verbatim — same asymptotic win, far less retrofit.

## Linked concepts

- [[ac3]] — coarse-grained baseline
- [[ac4]] — what AC-6 deprecates
- [[ac7]] — AC-6 + metaknowledge
- [[ac2001]] — coarse-grained residual-support, the right port for us
- [[ac-family-comparison]]
