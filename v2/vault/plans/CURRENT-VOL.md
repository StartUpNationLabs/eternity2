# Current Volume — Vol-149

**Theme**: STRATUM — Layered-Algebra Decomposition.
Constructive-from-scratch builder using piece orbit equivalence under
color-permutation symmetries of the Selby-Riordan generator.

User preference (2026-05-19 evening): "those allowing to build better
puzzle from scratch faster feels good" → STRATUM ranks #1 of 6 named
inventions.

## The invention in one paragraph

The Selby-Riordan piece-set generator produced 256 pieces using a
specific algorithm. We hypothesize the generator left a **fingerprint**
— a hidden equivalence relation on pieces under color-permutation
orbits. Two pieces are in the same **stratum** iff their 4-color
multiset is in the same orbit under some color-permutation π. A solved
board respects stratum structure: certain stratum-pairs cannot be
adjacent. Building stratum-by-stratum is **combinatorially cheaper**
than per-piece DFS by a factor of `n_strata * (avg orbit size)!`.

## Why it might work

Vol-65 measured: no rotation-symmetric pieces (256 size-4 orbits under
rotation), 5 multiset-twin pairs (10 pieces sharing edge-color
multiset). The multiset-twin finding hints at **deeper hidden orbits
under generator-internal symmetries**.

If we find ≥ 8 strata of size ~32 pieces each, we can:
1. Place strata in a fixed order (border-first × stratum-rank).
2. Within each stratum, the piece sub-problem is 32!/32^k vs 256!/256^k —
   millions of times smaller.
3. Build from scratch with stratum-CSP much faster than vanilla DFS.

## Binding items (3 max)

1. **Build the equivalence relation**: enumerate all color-permutations
   of the 22 interior colors that map the piece SET to itself. The
   group of such π is the **piece-set automorphism group** $G$. Pieces
   in the same $G$-orbit are stratum-equivalent.
2. **Measure stratum structure on canonical 16×16**: compute |G|, the
   orbit sizes, and whether the 463/469 records respect any orbit
   constraint. Falsifiable: if records ignore orbits, STRATUM is dead.
3. **Build stratum-DFS PoC**: backtracker that places one full stratum
   before moving to the next, vs vanilla DFS. Compare wallclock-to-100
   placements on canonical.

## Kill-criterion

- If |G| = 1 (i.e., no color-permutation preserves the piece set),
  STRATUM fingerprint hypothesis is refuted on canonical E2. Document
  + close.
- If |G| > 1 but records violate orbit constraints (no fingerprint
  visible), refute as "fingerprint exists but doesn't transfer to
  solutions".
- If |G| > 1 AND records respect orbits AND stratum-DFS is no faster
  than vanilla — refute as engineering loss.

## Days budget

3 days. Day 1: compute $G$ and orbit decomposition. Day 2: measure
record-board adherence + design stratum-DFS. Day 3: prototype + compare
to vanilla_fast.

## Linked

- [[../sessions/vol-149]] (to be created)
- [[../concepts/stratum-orbits]] (to be created)
- [[INVENTION_NAMES_2026-05-19]]
- [[../concepts/k11-cross-domain-brainstorm]] (related: piece-set automorphism)
- [[../concepts/piece-set-symmetries]] (vol-65 measured no rotation symmetries)
