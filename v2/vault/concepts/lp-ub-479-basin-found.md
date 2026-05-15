# First LP-UB-479 basin discovered (vol-46)

**Status**: DISCOVERED 2026-05-15 morning during basin-rep sweep.
**Origin**: vol-46 LP UB sweep on previously-untested high-score class
representatives.

## The basin

File: `output/v17_alns_only/winning5_sa_t1_s1_1778670467.json`

| Metric | Value |
|---|---:|
| Score (current) | 457 |
| bb | 60 / 60 |
| bi_ub (LP) | 55.48 |
| lp_interior | 363.52 |
| **total UB** | **479.0** |
| n_x | 145929 |

**LP UB = 479** — one point above class A's 478 — **the first basin
in our archive with theoretical ceiling > 478**.

## Mismatch geometry

| Type | Count | Location |
|---|---:|---|
| B-B | 0 | — |
| B-I | 5 | All in TOP perimeter row (y=0 → y=1) and one at (15,1)-(14,1) |
| I-I | 18 | TOP band (y=1..2..3..4) |

Class-B style (top mismatches), but with LP UB 1 point higher than
class B's 477. So this is a NEW class — call it **class D** (UB 479,
top mismatch geometry).

## What this proves

The 478 LP UB cap we've been observing across vol-44/vol-45 is **NOT
the canonical-5-clue ceiling**. A basin with UB 479 exists in our
own search archive — we just hadn't tested its LP UB until now.

This means:
- There may be more basins with UB 479+ in the 4746-board archive.
- The 478 finding is a SAMPLE artifact, not a structural ceiling.
- Pushing this basin to 459 would be a RECORD BREAK.

## Status

8 ALNS-diverse seeds × 1h each launched on this basin. 

Outcomes to watch:
- 457 (no lift): basin locked at 457 like our class A 458.
- 458: ties our 458 record in a new basin.
- 459+: **RECORD BREAK**.

## Linked

- [[lp-ub-478-basins]] — vol-44/45 LP UB landscape
- [[border-class-geometries]]
- [[vol-46]] — vol where this was found
