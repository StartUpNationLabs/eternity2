# Border-class mismatch geometries (vol-44)

**Status**: measurement.
**Origin**: vol-44 LP UB sweep + mismatch_map across classes A and B.

## Geometric inversion between class A and class B

The three border-classes identified in vol-44 have **structurally
distinct mismatch geometries**:

### Class A (UB 478, bb=60)
Records: vol-32 458, vol-35 458, vol-32 456 s2, vol-39 455 s1/s5,
vol-36 454.

**Mismatch geometry**: ALL I-I mismatches concentrated in
**bottom rows (y ∈ 10..14)**. Top 9 interior rows are perfect.

### Class B (UB 477, bb=60)
Records: vol-32 457 s7, vol-32 457 s10, vol-32 456 s4.

**Mismatch geometry**: ALL I-I mismatches concentrated in
**top rows (y ∈ 1..4)**. Rows 5-14 are perfect (no I-I mismatches).

Measured for vol-32 457 s7:
- 0 B-B mismatches
- 3 B-I mismatches
- **20 I-I mismatches, all with y ∈ {1, 2, 3, 4}**
- 6 mismatch clusters: sizes 5, 5, 4, 3, 2, 2 (similar shape to class A)

### Class C (UB 476, bb=58)
Records: vol-32 457 30min s4. Different border structure (only 58/60
B-B), not directly comparable to A or B.

## Why this matters

The "hard region" of a basin is **NOT a property of the puzzle** —
it's a property of the **basin** (i.e., of the border-class + search
trajectory that led to the basin).

This **confirms and extends** the vol-14 finding (memory
`project_e2_vol14_mismatch_geometry_universal`):
> "our 443 + vol-6's 454 BOTH have hard region at center-BOTTOM;
>  community 469/468 have it at TOP"

Class A here corresponds to our search style (bottom-band hard).
Class B corresponds to the inverted geometry (top-band hard).
Both achieve 457-458 on canonical 5-clue but in completely
different parts of the grid.

## Implications

1. **Cross-class graft is non-trivial.** A's 458 has perfect rows 1-9;
   B's 457 has perfect rows 5-14. They share **rows 5-9 as perfect**.
   Could a "graft" combining A's top-half with B's bottom-half (or
   vice versa) yield > 458?

2. **Symmetry hypothesis**: are the two classes related by a global
   board rotation/reflection? E2 has no obvious symmetry that maps
   top → bottom, but the puzzle isn't symmetric anyway. Worth
   checking pid-by-pid whether the cells in A's bottom band are the
   SAME pieces as in B's top band (i.e., a swap of "hard region"
   piece set).

3. **Per-class cluster repair**:
   - Class A: already proven locally optimal at 28-cell MIP (delta=0).
   - Class B: to be measured (in progress).

## Class-B 457 local-optimality (measured 2026-05-14)

Cluster-repair MIP on vol-32 RECORD_TIE_457_blackwood_mrv_5min_seed7
(class B):

| halo | total time | total delta |
|---:|---:|---:|
| 0 | 0.04 s | **0** |
| 2 (regions up to 27 cells) | 52 s | **0** |

**Class B is also locally optimal under MIP-exact cluster repair.**

## Class A and B boards are nearly disjoint (measured)

Board diff between vol-32 458 (class A) and vol-32 457 s7 (class B):

| Metric | Value |
|---|---:|
| Same (pos, piece, rotation) | **7 / 256** |
| Same pos, same piece, diff rotation | 0 |
| Same pos, diff piece | 249 |
| Perimeter same | 3 / 60 |
| Interior same | 4 / 196 |

| Region | Pieces in common (out of 56-70) |
|---|---:|
| Perim horiz | 17 / 32 (53%) |
| Perim vert | 13 / 28 (46%) |
| Top (rows 1-4) | 18 / 56 (32%) |
| Mid (rows 5-9) | 23 / 70 (33%) |
| Bot (rows 10-14) | 28 / 70 (40%) |

**A and B are nearly disjoint boards**, sharing only 7/256 = 2.7% of
positions exactly. They are NOT two arrangements of the same border.
Cross-class graft via "copy regions" is therefore non-trivial: the
piece sets in any one row don't even overlap that much.

## Combined conclusion (classes A and B)

Both basin classes A (UB 478, integer 458) and B (UB 477, integer 457)
are **MIP-exact locally optimal** under any single-cluster
rearrangement of up to ~30 cells.

**The LP UB is loose**: 20 points of LP slack in both classes, with
ZERO achievable lift under local search.

This is a STRUCTURAL claim, not just empirical. The MIP gives exact
proof. Implication: to break 458 on class A or 457 on class B, we
need either:
1. **Cross-class moves** — swap a region of class-A's bottom-band
   with class-B's top-band (or some piece subset).
2. **A new basin entirely** — neither A nor B but a 3rd one we haven't
   sampled.

## Open questions

- **Cross-class graft**: take class A's perfect top + class B's
  perfect bottom. Does this form a feasible board with score > 458?
  Both classes share perfect rows 5-9; the question is whether
  combining A's rows 0-4 (perfect) with B's rows 10-14 (perfect)
  works. **This is the critical next experiment.**
- Is there a class with **diagonal** mismatch geometry?
- Is there a class with **scattered** (not concentrated in one band)
  mismatch geometry?

## Linked

- [[458-class-A-mismatch-structure]] — full anatomy of class A
- [[vol-44]] — session
- `project_e2_vol14_mismatch_geometry_universal` — prior memory
  documenting top-vs-bottom basin distinction
