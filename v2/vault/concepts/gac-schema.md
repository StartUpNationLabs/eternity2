---
tags: [concept, propagator, ac, table, reference]
status: unbuilt
origin-vol: 23
---

# GAC-Schema (Régin 1997)

**Status**: `unbuilt`, reference
**Origin**: Bessière & Régin, "Arc consistency for general constraint networks: preliminary results", IJCAI'97
**Files**: —

## Definition

A **generic schema for enforcing GAC (generalized arc-consistency) on n-ary constraints given as a table** of allowed (or forbidden) tuples. Generalizes AC-6 / AC-7 from binary to n-ary by maintaining, for each `(xi, a)`, the **current supporting tuple** (not just supporting value).

When a value `b` is removed from some variable, only the tuples containing `b` need to be examined. The schema processes the table `T` once during init to set up `Last[xi, a]` = pointer into `T` of a tuple still supporting `(xi, a)`. On removal, walk forward from `Last` until a still-valid tuple is found, or remove `a`.

## Complexity

- Time: **O(r · |T|)** per AC fixpoint, where `r` is arity, `|T|` allowed tuples.
- Linear in the size of the table — **proportional to the number of allowed tuples**. This is the headline result: GAC for arbitrary table constraints in time you'd already need to *read* the table.

## Modern descendants

- **STR (Simple Tabular Reduction)** — Ullmann 2007 — different data layout, often faster in practice
- **STR2 / STR3** — Lecoutre 2011
- **MDD-based GAC** — Cheng & Yap 2010; Régin's own follow-up "Improving GAC-4 for Table and MDD Constraints" CP'14
- **Compact-Table** — Demeulenaere et al. CP'16, current state of the art for table GAC

## E2 applicability

**Skip in the obvious form, but think about MDD compression.**

The naive translation — "encode each grid edge as a binary table constraint over (piece-rotation × piece-rotation)" — gives `|T|` up to 764² × match-rate ≈ several hundred thousand tuples per edge × 480 edges ≈ 10⁸ tuples. Too big.

But:
- The compatibility relation factors trivially as "shared color equal AND pieces distinct". GAC-Schema buys nothing over the existing per-color bucketing in our gacolor/AC-3.
- **MDD compression** could be interesting: build one MDD per row or column that compactly represents all sequences of (piece-rotation) consistent with the inter-piece color chain. This is a real research direction (cf. [[mcgavin-engine]] which conceptually does something similar with column-wise pruning) but it's a multi-week project, not a propagator port.
- The `same_piece_rots` LUT (vol-16) is already a tiny instance of "precomputed compatibility table" — gains there are exhausted.

## Verdict

Don't port GAC-Schema as a generic propagator. **DO** keep MDD-row decomposition on the long-term unbuilt list as a potentially powerful global propagator (would subsume AC-3 + gacolor on row/column slices). Adjacent to [[boundary-mps]] but compact-exact rather than approximate.

## Linked concepts

- [[ac2001]] — binary cousin, the cheap win
- [[gacolor]] — current per-color global filter
- [[boundary-mps]] — tensor-network analogue
- [[mcgavin-engine]] — column-pruning engine
- [[ac-family-comparison]]
