# Vol-54 — where does the LP-integer gap actually live?

**Open**: 2026-05-15
**Theme**: Resolve vol-50 vs vol-53 contradiction with cheap math.
**Status**: closed 2026-05-15.

## T1 — per-color INTEGER matches on vol-32 458 board

**Built**: `crates/bench-audit/src/bin/per_color_integer.rs` —
classifies each of 480 internal edges as II / BI / BB by cell-class,
bins by color.

### Sanity

- Edge counts: II=364, BI=56, BB=60, total=480 ✓ matches LP-anatomy.
- Score: II=346, BI=52, BB=60 → 458 ✓.

### Per-color II table (the headline result)

| color | LP_UB  | floor(LP) | INT | gap_to_floor | gap_to_LP |
|------:|------:|----------:|----:|-------------:|----------:|
|     1 | 0.0000|         0 |   0 |            0 |    0.0000 |
|     2 | 0.0000|         0 |   0 |            0 |    0.0000 |
|     3 | 0.0000|         0 |   0 |            0 |    0.0000 |
|     4 | 0.0000|         0 |   0 |            0 |    0.0000 |
|     5 | 0.0000|         0 |   0 |            0 |    0.0000 |
|     6 |19.9419|        19 |  19 |            0 |    0.9419 |
|     7 |19.0000|        19 |  18 |            1 |    1.0000 |
|     8 |20.8874|        20 |  21 |           -1 |   -0.1126 |
|     9 |20.8686|        20 |  20 |            0 |    0.8686 |
|    10 |22.8289|        22 |  22 |            0 |    0.8289 |
|    11 |23.6234|        23 |  22 |            1 |    1.6234 |
|    12 |23.0000|        23 |  22 |            1 |    1.0000 |
|    13 |22.0000|        22 |  21 |            1 |    1.0000 |
|    14 |21.1476|        21 |  20 |            1 |    1.1476 |
|    15 |19.0000|        19 |  17 |            2 |    2.0000 |
|    16 |20.9401|        20 |  20 |            0 |    0.9401 |
|    17 |23.0000|        23 |  22 |            1 |    1.0000 |
|    18 |22.2440|        22 |  20 |            2 |    2.2440 |
|    19 |19.0000|        19 |  19 |            0 |    0.0000 |
|    20 |21.4818|        21 |  20 |            1 |    1.4818 |
|    21 |22.0000|        22 |  21 |            0 |    0.0000 |
|    22 |23.0000|        23 |  21 |            2 |    2.0000 |
| **Σ** |363.96 |       358 | 346 |           12 |   17.9637 |

### Findings from T1

1. **Σ (LP - INT) = 17.96** matches vol-50's "II gap ≈ 18". ✓
2. **Σ (LP - floor) = 5.96** matches vol-50's "fractional 5.96". ✓
3. **Σ (floor - INT) = 12** matches vol-50's "12 points piece-uniqueness". ✓
   — vol-50's anatomy NUMBERS are correct.

4. **HOWEVER, color 8 has INT=21 > floor(LP_UB)=20.** The LP allocates
   only 20.8874 to color 8 at its joint optimum, but the actual integer
   board achieves 21. This means `floor(LP_UB[k])` is NOT a valid
   per-color integer bound. The LP UB is a *joint* allocation, not a
   per-color attainability bound. Vol-50's "12 points piece-uniqueness
   rounding" interpretation is **misleading** — the 12 isn't from
   "inability to jointly achieve per-color LP attainability"; it's
   from "the LP joint optimum allocates colors differently than the
   integer optimum can replicate".

## T2 — minimal y-LP gap example

### Construction (analytical + HiGHS verified)

2 cells in a row (c1, c2), 1 internal edge. 2 pieces:
- P1 sides (N, E, S, W) = (1, 1, 1, 1)
- P2 sides             = (2, 2, 2, 2)

### Integer best

P1 in c1, P2 in c2: east color 1, west color 2 → mismatch, score 0.
P2 in c1, P1 in c2: symmetric, score 0.
**Integer best = 0.**

### LP optimum

Variables: x[p, c] ∈ [0, 1] (rotations folded), y[k] ∈ [0, 1].
Constraints:
- Piece-uniqueness: x[P1, c1] + x[P1, c2] = 1; same for P2.
- Cell-coverage:     x[P1, c1] + x[P2, c1] = 1; same for c2.
- Linearisation:     y[k] ≤ min over each side of color-k mass.
- One match per edge: y[1] + y[2] ≤ 1.

Set t = x[P1, c1]. Then x[P1, c2] = 1−t, x[P2, c1] = 1−t, x[P2, c2] = t.

- y[1] ≤ min(t, 1−t)
- y[2] ≤ min(1−t, t) = same
- Σ y = 2·min(t, 1−t) ≤ 1, maximised at **t = 0.5** giving **Σ y = 1**.

**LP optimum = 1.0**, with x at the (0.5, 0.5, 0.5, 0.5) fractional point.

### HiGHS confirmation

`/tmp/vol54_t2_verify.py` (uses `highspy`):
- LP: obj=1.0, x[P1,c1]=0.5, x[P1,c2]=0.5, x[P2,c1]=0.5, x[P2,c2]=0.5, y[1]=0.5, y[2]=0.5. ✓
- IP (x integer): obj=0.0, x integer assignment, y=0,0. ✓
- **LP - INT = 1.0** on a 1-edge example.

### What this proves

1. **Vol-53's worded intuition is correct**: even with piece-uniqueness
   `Σ_c x[p, c] = 1` satisfied, y-LP can take fractional values that
   integer x cannot reproduce.
2. **The mechanism is cell-fractional x, not rotation-fractional x.**
   Per-piece column-gen (vol-52) tightens the rotation-level convex hull
   but doesn't restrict `x[p, c]` to {0, 1} across cells. The gap
   persists.
3. **The assignment polytope (Birkhoff-von Neumann) is TU**, so for a
   pure-x objective the LP is tight. But y is min-of-sums of x, which
   makes the y-LP *prefer* fractional x. TU doesn't help when the
   objective is min-of-x.

## Synthesis — vol-50 vs vol-53

Both were partially right; the actual mechanism is more specific:

| Source | Claim | Verdict |
|---|---|---|
| Vol-50 numerical | 5.96 fractional + 12 rounding = 18 II gap | **Numbers correct** ✓ |
| Vol-50 interpretation | "12 from piece-uniqueness joint-infeasibility" | **Loose / misleading** — color 8 has INT > floor(LP); the 12 is "LP makes different per-color allocations than integer can", not "piece-uniqueness violation" |
| Vol-53 worded | "y-linearisation slack persists with piece-uniqueness" | **Right** ✓ (T2 worked example) |
| Vol-53 toy-LP zero-gap | At 3-cell tiny scale LP=integer | **Right** but doesn't generalise; gap is multi-edge × multi-color × multi-cell-fractional |
| Vol-52 design | "per-piece column-gen closes 67% of gap" | **Refuted** — column-gen tightens rotation polytope but not cell-fractionality |

## What WOULD close the gap

The gap mechanism is **cell-fractional assignment chosen to favor y**.
To close:

1. **Branch-and-bound on x[p, c]**: standard MIP. Each branch fixes
   piece p to cell c or excludes it. Integer feasible region = integer
   hull. This is the standard B&P approach vol-53 priced at 3-4 weeks.

2. **Set-partitioning cuts**: enumerate small infeasible fractional
   patterns (like t=0.5 in T2) and add cuts. Cuts on the y-side that
   say "y[k] ≤ Σ_(c, r in compatible placements) x[c, r, k]" tighter
   than the basic linearisation.

3. **Reformulate y as integer**: `y[k] ∈ {0, 1}` for each edge-color,
   not [0, 1]. Already an integer variable in any MIP formulation, but
   the LP RELAXES it to [0, 1]. Combined with x-branching this is
   standard MIP.

4. **Vol-44 already did this exactly** with HiGHS MIP on a single
   border for ~1h, confirming local optimality. Scaling to all basins
   is multi-day MIP per basin.

## Implication for vol-52 design

[[lifted-lp-column-gen-per-piece]] page amended: the design is
mathematically sound for what it does (tighten the rotation-level
convex hull per piece), but **the binding constraint is cell-fractional
x interacting with y-linearisation**, NOT rotation-fractional x. Vol-52
estimate 7-10 days → vol-53 revised 3-4 weeks → vol-54 confirms 3-4
weeks (need full B&P-and-cut for the gap, per-piece column-gen alone
is genuinely insufficient).

## Implication for the standing 458 record

Vol-53's session close said "458 may be near-globally-optimal for
current search algorithms". Vol-54 sharpens: the 458's distance to
optimal is bounded by the joint integer hull around its basin, not by
any tighter LP we can compute cheaply. The 458 record's certified
upper bound (vol-44 MIP, 1h, integer-feasible 458) is **the tightest
honest bound we have**. The 478 LP is loose by 20 because of cell-
fractional x slack — closing that requires MIP, which has been done
on one border in 1h and found the same 458.

So 458 is, on the basins we've MIP-verified:
- **Globally optimal within that basin's frozen border**.
- The "20-point LP gap" is not a record-breaking lever; it's a measure
  of LP looseness vs the integer truth.

The actual record-breaking lever would be **a different basin** with
higher integer optimum, OR an algorithm that escapes the basin's local
hull. Neither is in scope for an autonomous session.

## Vol-54 outputs

- `crates/bench-audit/src/bin/per_color_integer.rs` (new bin, builds, runs).
- `/tmp/vol54_t2.py`, `/tmp/vol54_t2_verify.py` (worked example, math + HiGHS).
- `vault/sessions/vol-54.md` (this page).
- Updates to `concepts/lp-integer-gap-anatomy.md` and `concepts/lifted-lp-column-gen-per-piece.md` (amendments below).
- Updates to `concepts/per-piece-column-gen-6x6-worked.md` (vol-54 makes the refutation precise).
- New concept: `concepts/y-linearisation-cell-fractional-gap.md` (the actual gap mechanism).

## Linked

- [[vol-50]] — anatomy table, numerically correct but loose interpretation
- [[vol-53]] — refutation of vol-52, intuition vindicated by T2
- [[../concepts/lp-integer-gap-anatomy]] — vol-50's concept page; update needed
- [[../concepts/lifted-lp-column-gen-per-piece]] — vol-52 design; update needed
- [[../concepts/per-piece-column-gen-6x6-worked]] — vol-53 refutation; gets a sharper proof
- (NEW) [[../concepts/y-linearisation-cell-fractional-gap]] — gap mechanism, vol-54
