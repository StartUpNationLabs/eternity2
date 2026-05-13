---
status: refuted
since: vol-25
---

# Symmetry analysis of canonical 5-clue E2

**Status**: `refuted` (no exploitable symmetry exists post-hints; cleared at vol-25 open)
**Origin**: vol-25 investigation, prompted by re-reading `reference_blackwood_decoded` and asking whether the σ bijection enables a coset-enumeration solver.

## The question

Can we find a non-trivial automorphism group of canonical 5-clue E2 (post-hints) and use its orbit structure to:
(a) prune the search space by a known multiplicative factor, or
(b) enumerate solutions one-per-orbit?

## The five candidate symmetries, each refuted

### S1. Board geometric symmetry (D₄: 4 rotations + 4 reflections)

The 16×16 board has D₄ symmetry. **Broken by the 5 canonical hints**: corners at (0,0), (15,0), (0,15), (15,15) hold pieces 207, 180, 254, 248 with rotations 1, 1, 1, 2; centre at (8,8) holds the central piece. The 4 corner pieces are all distinct, the rotations are inhomogeneous, so no non-trivial element of D₄ fixes the hint set. **Residual symmetry: trivial.**

### S2. Color permutation symmetry (S₂₂ acting on interior colors)

Permuting interior colors (1-22) uniformly across all pieces gives an isomorphic puzzle. Theoretical orbit count: 22! ≈ 10²¹. **Broken by the 5 hints**: the corner + centre pieces have specific edge colors that fix the permutation. After fixing the 4 corner pieces and the centre, every interior color appears on at least one hint piece at a determined position. **Residual symmetry: trivial.**

### S3. Piece rotation symmetry (Z₄ per piece)

Globally rotating one piece type by k ∈ {1,2,3} preserves the puzzle iff the piece's edge tuple is rotation-invariant under that k. For canonical E2 pieces, the only rotation-invariant edge tuples are pieces where all 4 sides have the same color — these don't exist in canonical E2 (Selby-Riordan generator excludes them by construction; the 5 rare colors {1-5} are never repeated within a single piece, see `rare-color-rule`). **No piece admits non-trivial rotation symmetry.**

### S4. Frequency-class permutation (the σ structure)

The σ bijection from `reference_blackwood_decoded` is a 5-cycle on three 5-element frequency classes and an involution on {0, 21, 22}. **This is a property of the colour-labelling convention, NOT a symmetry of the puzzle.** σ translates between Blackwood's labels and ours; two boards related by σ are the *same physical board* under two naming schemes. There is no information gain from quotienting by σ — both copies count as the same solution.

### S5. Hint-set automorphism

Could the 5-hint configuration itself have a residual automorphism? E.g., is there a non-trivial permutation π ∈ S_{256} mapping the puzzle to itself with π(hints) = hints (modulo geometric and color permutations from S1-S2)? **No.** The 5 hint pieces have distinct edge multisets (verified by inspection of `data/puzzles/size_16_official_eternity.csv`); any automorphism π must map each hint piece to itself; combined with the fixed positions, π must fix every cell. **Residual: trivial.**

## What this means

**Canonical 5-clue E2 post-hints has trivial automorphism group.** There is no algebraic quotient to exploit. Every solution must be enumerated individually; no orbit-based pruning is available.

This is why approaches like:
- "exploit the symmetry to reduce search" — fails (no symmetry).
- "enumerate solutions one-per-orbit" — fails (orbit = singleton).
- "use σ as a solver tool" — category error; σ is a translation table.

## What this does NOT refute

- σ as a **logistic tool** for cross-referencing community boards. Still useful (and `blackwood_decoded.json` uses it).
- Approximate / asymptotic symmetries (e.g., "swapping two pieces of the same orbit-multiset class barely changes the score"). These are local search arguments, not automorphisms. Covered by `piece-orbit-as-atom` (BACKLOG, also `wont-do` per low value).
- Symmetries of the 1-clue variant (`E2ncud`). The 1-clue variant pins only the central piece, so it retains the D₄ board symmetry / 8 equivalent solutions per orbit. This is why Blackwood's 470 is on the easier variant. **Not our target.**

## Decision

**No further work on symmetry-based solvers for canonical 5-clue E2.** If the question recurs in a future volume, this page is the answer.

## Linked concepts

- [[blackwood-algorithm]] — Blackwood's three pruners (his approach is empirical, not algebraic).
- [[rare-color-rule]] — relevant to S3 refutation.
- [[basin-blackwood-470]] — the 1-clue variant where D₄ DOES apply.

## Linked memory

- `reference_blackwood_decoded` — source of the σ definition.
