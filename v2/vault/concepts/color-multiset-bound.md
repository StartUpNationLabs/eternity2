# Color multiset bound on canonical E2 (vol-44)

**Status**: measurement + derivation.
**Origin**: vol-44 strategic re-eval; tool `color_side_count`.

## Combinatorial color-matching bound

Each piece has 4 sides. Sides are coloured (1..22 = interior colours;
0 = BORDER). For a *match* to exist on an internal edge, both
adjacent sides must have the same colour ∈ {1..22}.

The 480 internal adjacencies use 2 × 480 = **960 non-BORDER side-slots**.

Each colour k contributes $N_k$ non-BORDER sides across all 256 pieces.
$\sum_k N_k = 960$ (consistency check).

**For matches**: matched-edge count on colour k ≤ ⌊N_k / 2⌋.

**Combinatorial UB**: $\text{total matches} \le \sum_k \lfloor N_k/2 \rfloor$.

## Measured values on canonical E2

| Colour | $N_k$ | ⌊$N_k$/2⌋ | Wasted |
|:---:|---:|---:|---:|
| 1, 2, 3, 4, 5 (rare) | 24 each | 12 | 0 |
| 6, 7, 8, 9, 10 (mid) | 48 each | 24 | 0 |
| 11, …, 22 (common) | 50 each | 25 | 0 |
| **Total** | **960** | **480** | **0** |

Sum: 5×12 + 5×24 + 12×25 = 60 + 120 + 300 = **480**. ✓

## Implications

1. **Combinatorial UB = 480.** The colour-multiplicity argument is
   *not* the constraint that prevents a 480-score solution. Every
   colour has an even count, so no parity waste.
2. **Original Eternity II** has a 480 solution. This is consistent
   with the combinatorial UB.
3. **Rare colours (1–5)** each appear exactly 24 times — they're
   special. 24 = 4×6 sides → they appear specifically on certain
   piece-side patterns (per [[rare-opposite]] / vol-7).
4. The **LP UB 478** we measure on class A is therefore **spatially
   restricted**, not combinatorially restricted. The LP picks up
   spatial constraints (which cells are adjacent to which) that the
   raw colour count misses.

## What this tells us about the 478 → 480 gap

The LP UB 478 on class A's border is 2 below the combinatorial UB
of 480. **That 2-point gap is the LP picking up spatial structure**:
the colour mass on specific cell-sides can't form integer matches
exactly because of where the cells are.

For a 480 solution to exist on a border (matching original Eternity
II's answer), the border must be the one specific border that admits
the unique 480 solution (or one of few — uniqueness is conjectural).

Our 478-class borders are **2 LP-points away** from admitting 480.
A different border could admit higher LP UB up to 480.

## Linked

- [[lp-ub-478-basins]] — current LP UB ceiling
- [[border-class-geometries]]
- [[vol-44]] — session
