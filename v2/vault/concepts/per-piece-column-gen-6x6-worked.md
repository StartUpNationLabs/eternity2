# Per-piece column-gen — worked example attempt + REFUTATION

**Status**: `refuted (subtle)` — vol-53 (2026-05-15).
**Origin**: vol-52 design doc ([[lifted-lp-column-gen-per-piece]]) needed
a 6×6/5c worked example to validate before any engineering investment.
Attempting the math at smaller scale revealed a structural issue with
the vol-52 reasoning.

## What we tried

Build a tiny LP relaxation in Python+highspy on hand-designed toy
instances:
1. 3 pieces, 2 cells, edge matching.
2. 4 pieces, 2 cells, with duplicate pieces (piece-uniqueness pressure).
3. 3 pieces, 2 cells, with the "two left=A, two right=A" structure.

Goal: demonstrate that fractional LP achieves higher score than the
integer optimum (the canonical LP-integer gap).

## What we found

**All toy instances had LP = Integer (zero gap).**

This is structurally expected: on the LP for bipartite-like assignment
with linear coupling (piece-uniqueness + cell-coverage), the LP is
known to be **totally unimodular** at small scale. The fractional
relaxation gives the same integer optimum.

## Where the canonical-E2 gap actually comes from

The 20-point LP-integer gap measured at vol-44/45/46 (and analysed in
[[lp-integer-gap-anatomy]]) does NOT come from piece-uniqueness alone.
It comes from the **y-linearisation interacting with piece-uniqueness
across the full 196-cell interior at scale**.

Specifically:
- Each I-I edge `(c, c')` has y[c, c', k] = min(a[c, right, k], b[c', left, k]).
- a, b are sums over per-piece-per-rotation indicators.
- Summed over ~364 I-I edges and 22 colors, the y-LP allows
  fractional x to claim non-integer-feasible joint matches.

The fractionality of x doesn't violate piece-uniqueness if `Σ_c x[p, c, r] = 1`
holds for each piece. But the **distribution of x across cells** can
arrange to maximise y in a way that no integer x can.

## Implication for vol-52 design

Vol-52's design said: "per-piece column-gen restricts piece-uniqueness
exactly, eliminating fractional x → closes the integer-rounding gap."

**This is partly wrong.** Per-piece column-gen at the MASTER LP level
still produces fractional x (each piece is `Σ_z z[p, z] · placement_z`,
with z ∈ [0,1] convex combination). The gap in y is preserved because
y is a min-of-sums over fractional x.

What per-piece column-gen DOES help with:
- It tightens the **per-piece convex hull** — only convex combinations
  of EXISTING placements are allowed for each piece, not arbitrary
  fractional x.
- This can close PART of the gap, but probably much less than the
  67% I claimed in vol-50.

What per-piece column-gen DOES NOT help with:
- The fundamental y-linearisation gap.
- The fractional convex combination of placements is still fractional.

## What might actually close the gap

For the canonical-E2 LP-integer gap, the correct approach is likely:
1. **Tighter y formulation** — replace `y ≤ min(a, b)` with the
   convex hull of integer matching configurations.
2. **Cuts on x**: integer cuts (Gomory) on the master LP after
   column-gen pricing identifies useful columns.
3. **Branch-and-price**: combine column-generation with B&B over x.
   This is the standard approach in integer programming with column-
   gen. Vol-52 missed this; just "column-gen" alone yields a tighter
   LP bound but not the integer optimum.

## Engineering cost revision

Vol-52 estimated 7-10 days for per-piece column-gen build. **The new
cost estimate is much higher**:
- LP master + column-gen: 5 days (as before).
- Branch-and-price wrapper: 5-10 days (new requirement).
- Cuts (Gomory, clique): 3-5 days.
- Integration + tuning: 5 days.

**Total revised: 3-4 weeks** for a build that meaningfully closes the
20-point gap. The vol-52 cost estimate was too optimistic.

## Verdict for the path

Per-piece column-gen as standalone LP relaxation: not the right tool.
The full branch-and-price-and-cut machinery would work, but is 3-4
weeks of focused engineering for a result that mostly **certifies**
local optimality of 458 (we already proved this via 196-cell MIP at
vol-44 in 1h).

The cost-benefit no longer favors building this. **Per-piece column-
gen as a record-track tool is refuted in light of vol-53's analysis.**

## What still matters from the math

1. The vol-50 LP-integer gap anatomy is correct in its decomposition
   (33% fractional y, 67% integer-rounding).
2. The vol-52 design's framing (column-gen helps piece-uniqueness)
   is partially right but misses that y itself is the bottleneck.
3. The standing 458 record's local-optimality (vol-44 MIP) is
   intact; no new attack vector has emerged.

## Open frontiers (revised)

- **Vol-25 perf backlog**: still engineering, ~20% combined on joe.
- **LNS-style recovery for vol-51 B1**: 1-2 days, modest score lift.
- **No-good CDCL learning**: multi-week, high uncertainty.
- **Branch-and-price-and-cut**: 3-4 weeks, mostly produces optimality
  certificates (not records).

None of these have high P(record-break) given vol-44's MIP result.
The path to >458 likely requires a fundamentally different search
algorithm (multi-week+).

## Linked

- [[lifted-lp-column-gen-per-piece]] — vol-52 design (now partially refuted)
- [[lp-integer-gap-anatomy]] — vol-50 motivation
- [[lp-ub-478-basins]] — vol-44 LP UB landscape
- [[../sessions/vol-52]], [[../sessions/vol-53]] — sessions
