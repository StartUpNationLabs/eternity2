---
tags: [concept, propagator, ac, reference]
status: unbuilt
origin-vol: 23
---

# AC-4 (Mohr & Henderson 1986)

**Status**: `unbuilt`, reference only
**Origin**: Mohr & Henderson, "Arc and Path Consistency Revisited", AIJ 1986
**Files**: —

## Definition

Fine-grained arc-consistency: for every value `(xi, a)` precompute the support set `S[xi,a,xj] = { b ∈ D_xj : (a,b) consistent }` and the counter `counter[xi,a,xj] = |S|`. When a value `(xj, b)` is removed, walk every `(xi, a) ∈ S[xj,b,xi]` and decrement its counter; if it hits 0, propagate that removal.

## Complexity

- Time: **O(e·d²)** worst case — optimal in the number of constraint checks.
- Space: **O(e·d²)** — the bulky support lists are the well-known drawback.
- Initialization is itself O(e·d²) regardless of how loose the constraints are.

## Why it's mostly obsolete

Wallace (IJCAI'93) "Why AC-3 is almost always better than AC-4" showed AC-3 wins on average because:
- AC-4 pays full O(e·d²) init even when most constraints are easy.
- The support lists don't backtrack cleanly (must restore exact counters).
- Memory traffic >> constraint-check savings on real instances.

AC-6 (Bessière 1994) and AC-2001 / AC-3.1 (Bessière–Régin 2001, Zhang–Yap 2001) both supersede it: same O(e·d²) worst case, dramatically smaller space, coarse-grained queueing.

## E2 applicability

**Skip.** On E2:
- e ≈ 480 (grid joins), d ≈ 764 → support tables of size ≈ 2.8 × 10⁸ entries per propagator, exploding memory in the bitset stack.
- Counters don't survive backtracking without trailing — incompatible with our zero-alloc bitset domain rep ([[bitset-domain-rep]]).
- AC-3 with the vol-16 `same_piece_rots` LUT already amortizes the constraint-check cost where it matters.

If we ever want sub-AC-3 propagation cost we go to [[ac2001]] (residual support), not AC-4.

## Linked concepts

- [[ac3]] — coarse-grained baseline, what we use
- [[ac2001]] — modern fine-grained-with-residue replacement
- [[ac-family-comparison]] — pick-which-one summary
