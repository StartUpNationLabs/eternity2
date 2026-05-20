# V184 LIGHTHOUSE — Bidirectional Row-Build (REFUTED)

Status: **refuted** — MERGE fails. 0 valid pairs across configurations.
Origin: vol-184.
Files: `scripts/v184_lighthouse/build_bidirectional2.py`, `scripts/v184_lighthouse/build_bidir_v3.py`.

## Idea

Build from top down (rows 0..M) and bottom up (rows 15..M) simultaneously; meet
at row $M$. Each side gets the "easier" half (borders + early constraints).

Two variants tried:

- **v2** independent: run top beam and bottom beam independently, then merge
  with disjointness + interface-match constraint.
- **v3** per-state: for each top-state, run a dedicated bottom-up beam using
  only pieces NOT in `top.used`. Guarantees disjointness; 8× compute.

## Why it doesn't work

Two structural obstructions:

1. **Disjointness obstruction (v2)**: independent top and bottom beams pull
   from the same pool of "promising" pieces (top corpus-supported placements).
   Disjointness fails on > 99.9% of pair combinations at $K = 32$. → 0/1024
   valid pairs.

2. **Interface obstruction (v3)**: even with guaranteed disjointness, the row
   $M$ N-edge color sequence from the bottom-up build must exactly match the
   row $(M-1)$ S-edge color sequence from the top-down build. This is a
   16-color match condition. With remaining pieces constrained, the matching
   set is effectively empty.

The interface constraint at row $M$ has the same structural difficulty as the
V183 SEMAPHORE row-10 wall, **just relocated to a different row**.

## Math

Top-down beam ends with $K$ top-states at row $M-1$, each with a 16-color S-edge
sequence $\sigma^{(t)}_i \in \{0,\ldots,22\}^{16}$.

Bottom-up beam (v3, restricted to pieces not in top-state $i$'s used set)
produces $K'$ bot-states at row $M$, each with N-edge sequence
$\nu^{(b)}_j \in \{0,\ldots,22\}^{16}$.

A merge is valid iff $\sigma^{(t)}_i = \nu^{(b)}_j$ exactly.

Under the empirical distributions, this match happens essentially never. The
constraint forces 16 simultaneous color matches on a discrete alphabet of
size 22, with neither side optimising for this match.

## What's open (potential softening)

- **Soft-interface variant**: accept merges with ≤ 4 N-edge mismatches at row
  $M$, then ALNS-repair the mismatched columns. Not yet implemented.
- **Bidirectional via column** instead of row — same wall expected.
- **Triangular meet** (top-left + bottom-right diagonal) — not tried.

## Linked concepts

- [[semaphore-row-hungarian]] (V183, parent obstruction)
- [[prior-data-augmented-beam]] (V155, used in top-down direction)
