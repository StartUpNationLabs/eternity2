---
name: piece-orbit-structure
description: Built the rotation-orbit + edge-multiset analysis of the canonical
status: built
metadata:
  type: concept
---
# Piece-orbit & multiset structure of canonical E2 (vol-65 day 3.5)

**Status**: `built` — vol-65 (2026-05-15).
**Origin**: gap-list item 7 + structural analysis triggered by PSM-LP work.
**Files**: `scripts/vol65_piece_orbits.py`, `output/vol-65/piece_orbits.json`.

## Findings

Built the rotation-orbit + edge-multiset analysis of the canonical
E2 piece set (256 pieces from `size_16_official_eternity.csv`).

### 1. No rotation-symmetric pieces

All 256 pieces have full rotation orbit of size 4. Selby-Riordan
ensured no piece is invariant under any non-trivial rotation.
This means EVERY piece has 4 genuinely distinct placement-orientations.

Consequence: the puzzle has 256 × 4 = 1024 distinct piece-rotations.
No rotation-symmetry reduces this count.

### 2. Edge-multisets — 5 twin-pairs

The set of UNORDERED edge-color quadruples has **251 distinct
multisets** across 256 pieces. So **5 multisets appear in 2 pieces
each**:

| multiset | piece A | piece B | kind |
|---|---|---|---|
| {0, 0, 2, 3} | 2: (0,0,2,3) | 3: (0,0,3,2) | both corners |
| {0, 1, 2, 7} | 5: (0,1,7,2) | 14: (0,2,7,1) | both edges |
| {0, 1, 5, 9} | 7: (0,1,9,5) | 51: (0,5,9,1) | both edges |
| {7, 10, 15, 17} | 109: (7,10,15,17) | 110: (7,10,17,15) | both interior |
| {9, 12, 14, 21} | 171: (9,14,21,12) | 181: (9,21,14,12) | both interior |

These 10 pieces are **structural twins**: pairs that share the
same edge-color multiset but are NOT related by rotation OR
reflection.

Mathematical fact: pieces 109 (7,10,15,17 in NESW order) and
110 (7,10,17,15) are NOT in each other's orbits under the symmetry
group D₄ (rotation + reflection). They are genuinely different
pieces with the same "color budget."

### 3. Near-twin groups (3-of-4 edges shared)

In canonical rotation, **79 groups** of pieces share 3 of 4 edges,
giving **114 near-twin piece-pairs**. Largest groups (4+ pieces):

- omit_side=1 (East), edges (N=0, S=15, W=2): pieces 10, 19, 30, 42
- omit_side=2 (South), edges (N=0, E=2, W=1): pieces 14, 21, 23, 24
- omit_side=2 (South), edges (N=0, E=3, W=3): pieces 26, 27, 28, 31

These groups have 3-cell-shared geometry; swapping among them
within a placement perturbs ONE edge per neighbor.

## Implications for E2 solving

### Multiset-twin swap as an ALNS move

A swap between pieces 109 and 110 (or any of the 5 twin pairs)
changes 4 incident edges per cell but preserves the cell's
edge-color budget. This is a CONSERVATIVE perturbation that ALNS's
standard operators don't target specifically.

Hypothesis: 5 multiset-twin swap moves, each potentially
+2/+3/+4-edge improvement at some boards, could be a productive
ALNS extension. **Implementation cost low.**

### Near-twin 3-of-4 swap

The 114 near-twin pairs (3-of-4 shared edges) are larger pool of
"low-disruption" exchanges. Each pair shares 3 edges, so swapping
them at a cell changes at most 2 incident edges (one per shared
side preserved, one per differing side changed). Conservative basin
exploration primitive.

### Implication for PS-LP cutting planes

The piece-set's multiset distribution is **highly non-uniform** —
251 multisets, only 5 collisions. This means most pieces have a
UNIQUE color-budget signature. Adding a "piece p must be the one
whose multiset matches {c1, c2, c3, c4}" constraint is a strong
cut, but rarely-applicable.

### Vol-65 takeaway

The puzzle's symmetry structure is **MAXIMALLY ASYMMETRIC**:
- No rotation symmetries (orbit size = 4 for all pieces)
- Only 5 multiset-twins out of 32,640 piece-pairs
- Near-twins (3-of-4 shared) are 114 of 32,640 pairs (0.35%)

Selby-Riordan generator went to lengths to break symmetries.
This makes the puzzle harder than a "random" 16×16 piece-matching:
fewer structural shortcuts.

## Open

- Test multiset-twin-swap as an ALNS operator (vol-65d): does it
  help escape basins?
- Where in known 459 boards do the 10 twin pieces sit? Are any of
  the twin pairs swapped across our different 459s? If yes, we have
  a candidate "uncertain piece" that varies between equally-good
  solutions.

## Linked

- [[piece-side-matching]] — the PSM polytope (parent concept)
- [[vol-65]]
- memory: vol-65 piece-orbit & multiset-twins
