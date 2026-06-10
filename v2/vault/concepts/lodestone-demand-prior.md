---
name: lodestone-demand-prior
description: "LODESTONE (vol-208) — a scarce-demand-frequency prior for the KEYRING/V155 beam constructor, built from the band-monotone score-correlated scarce (N,W)-demand signal. Result: at tiny alpha=0.001 gives median +2 from-scratch (449->451) AND reduces variance (446-451 -> 450-451); at any larger alpha it HURTS (realizing scarce demands trades off vs immediate matching). A real but modest construction-quality lever, NOT a record-mover — confirms the WATERSHED 'scarcity is a real but weak value-order signal' finding for the beam at scale."
status: built
metadata:
  type: concept
---

# LODESTONE — scarce-demand-frequency prior for the beam (vol-208)

**Origin**: vol-208 (2026-06-10), the constructive payoff of the
[[scarcity-skeleton-shared-core]] measurement. Files:
`scripts/v208_confluence/build_lodestone_prior.py` (prior builder),
`output/v208_lodestone/` (A/B boards), prior at
`scripts/v208_confluence/output/lodestone_prior.json`.

## The idea
Today's measurement: high boards (≥458) activate a SOFT, score-correlated set of
scarce (N,W) demands (the count present in ≥50% of boards rises monotonically with
score: 1→2→3→10). LODESTONE converts that into KEYRING's per-(piece,position)
prior: `prior[p][pos] = max_r freq_{≥458}((p@r).N,(p@r).W) · scarcity_boost(mult)`,
broadcast over positions (position-independent → biases *which* pieces commit early,
the piece-theft fix). scarcity_boost = 3 for unique-server demands, 2 for 2-server.
KEYRING ranks children by `score + α·prior_sum`.

This is **genuinely different from V155's prior** (which is piece-at-position
frequency, tied to specific corpus boards' placements): LODESTONE is a
*demand*-realization prior, generalizing across positions and basins.

## What we measured (multi-seed, K=512 beam, 90s, row scan)
| seed | baseline (no prior) | LODESTONE α=0.001 |
|---:|---:|---:|
| 1 | 450 | 451 |
| 2 | 451 | 450 |
| 3 | 446 | **451** |
| 4 | 449 | **451** |
| 5 | 446 | **450** |
| **median** | **449** | **451** |
| **mean** | 448.4 | 450.6 |

**α sweep (single seed, K=512, 120s):** α=0.001 → 451; α=0.005 → 422; α=0.02 → 380.

## Findings
1. **At tiny α (0.001) LODESTONE gives a small consistent gain**: median +2
   (449→451), mean +2.2, and **reduces variance** (baseline 446–451 → LODESTONE
   450–451). It makes the constructor more *reliably* hit the top of its range.
2. **At any non-tiny α it HURTS badly** (422, 380): realizing the corpus-frequent
   scarce demands trades off against immediate edge-matching. The prior must be a
   pure tiebreaker, not part of the objective. This is the *same* tension
   WATERSHED/FORGE found (scarcity value-order is backtrack-neutral / weakly +).
3. **NOT a record-mover.** 451 from-scratch is below V155's tuned 456 and far below
   KEYRING+ALNS 460. LODESTONE improves construction *quality/consistency* by a
   couple edges, not the basin ceiling.

## Verdict
The scarce-demand signal is REAL and now confirmed to help the beam constructor
modestly (+2 median, variance↓). But like every scarcity lever in the project
([[watershed-frontier-flow]]: +12 greedy; MOSAIC reservation: 448 plateau), it
does not break the ~460 from-scratch ceiling. The piece-theft obstruction is a
GLOBAL assignment that a per-piece value-prior cannot resolve — reconfirmed a third
independent way. Useful as a default tiebreaker in construction pipelines; logged
as a minor positive, honestly bounded.

## Linked
- [[scarcity-skeleton-shared-core]] — the measurement LODESTONE operationalizes
- [[watershed-frontier-flow]] — the scarcity diagnosis (same +weak value-order lesson)
- [[mosaic-window-maxsat]] — the scalar-reservation predecessor (448 plateau)
- [[transept-strip-assignment]] — the refuted strip-construction sibling (same vol)
- V155 PRIOR / V181 KEYRING — the beam this priors into
