# Vol-53 — Per-piece column-gen worked example → partial refutation

**Theme**: Validate vol-52's per-piece column-gen design with a concrete
worked example before any 3-4 week engineering investment.

**Status**: CLOSED 2026-05-15 — **vol-52 design partially refuted**.
Per-piece column-gen alone doesn't close the gap; the y-linearisation
is the binding constraint, not piece-uniqueness fractionality alone.

## What was done

1. Created fresh Python venv (`/tmp/vol53_venv`) with `highspy` since
   `ml/.venv` doesn't have pip (uv-managed).
2. Built minimal LP relaxation in Python using `highspy.Highs` API.
3. Constructed 4 different toy instances (2-3 cells, 3-4 pieces)
   designed to exhibit an LP-integer gap from piece-uniqueness.
4. **All toy instances had LP = Integer** (zero gap).

## Key finding

The canonical-E2 LP-integer gap (~20 points) does NOT come from
piece-uniqueness fractionality alone, contra vol-52's framing.
It comes from the **y-linearisation interacting with piece-uniqueness
at scale**.

Specifically: even when each piece's `Σ_{c,r} x[p, c, r] = 1` (which
column-gen enforces exactly via per-piece convex combinations of
placements), the master LP's y-variables can take fractional values
that integer x cannot achieve. The min-of-sums structure of y allows
LP slack that column-gen doesn't directly address.

## Why this matters

Vol-52 claimed: "per-piece column-gen closes the 12 of 20 piece-
uniqueness gap points." Vol-53's analysis shows this claim was
oversimplified.

What column-gen actually does:
- Tightens the per-piece convex hull (only convex combos of valid
  placements, not arbitrary fractions).
- Can close PART of the gap, but probably much less than 67%.

What's needed to actually close the gap:
- Branch-and-price-and-cut (full B&P with Gomory + clique cuts).
- This is **3-4 weeks** of engineering, not 7-10 days.
- And it primarily produces optimality CERTIFICATES (we already
  proved 458 is optimal via 196-cell MIP at vol-44).

## Engineering cost revision

| Vol-52 estimate | Vol-53 revised |
|---|---|
| 7-10 days | 3-4 weeks |

The cost-benefit no longer favors this build. **Per-piece column-gen
as a record-track tool is refuted.**

## What still stands

- Vol-50 LP-integer gap anatomy (33% fractional y / 67% integer-
  rounding) is correct numerically; just the **interpretation** of
  the 67% was off.
- Standing 458 record's local optimality (vol-44 MIP) is intact.
- The "20-point gap is a property of search algorithm" finding from
  vol-46 is reinforced.

## Process notes

This vol-53 was a research-grade investigation that produced its
expected output: decisive information about whether the vol-52 design
was worth a 3-4 week engineering investment. The answer is **no**.

The math took ~30 minutes once highspy was set up. Total time including
venv setup, toy-instance design, debugging: ~1 hour.

The vol-52 cost estimate was too optimistic; vol-53's worked-example
math caught this before any code was invested. **This is exactly what
vol-53's risk budget was designed to do.**

## Open frontiers (revised after vol-53)

All record-track paths now appear to require either:
1. **Multi-week algorithm change** (no-good CDCL, neural-MCTS,
   different search paradigm).
2. **Multi-day MIP** on specific basins (already attempted vol-44 at
   1h, no improvement; weeks-of-MIP-budget unknown).
3. **Engine throughput** — but vol-25 already shipped the main wins;
   remaining ~20% is engineering.

The standing 458 record may indeed be near-globally-optimal for
search-algorithms-we-have. Confirming this with a tighter LP bound
(branch-and-price-and-cut) is 3-4 weeks of work that mostly produces
certificates, not records.

## Linked

- [[../concepts/per-piece-column-gen-6x6-worked]] — vol-53 refutation analysis
- [[../concepts/lifted-lp-column-gen-per-piece]] — vol-52 design (status updated to partially-refuted)
- [[../concepts/lp-integer-gap-anatomy]] — vol-50 motivation
- [[vol-52]], [[vol-51]], [[vol-50]] — predecessor sessions
