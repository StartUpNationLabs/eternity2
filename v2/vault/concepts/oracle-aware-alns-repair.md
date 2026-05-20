---
name: oracle-aware-alns-repair
description: "Vol-109 T1 — analytical concern EMPIRICALLY CONFIRMED. The cheap test (`vol109_oracle_graft.py`) grafted the oracle's pieces at σ-cycle positions into offset=100's partial. Result: score DROPPED from 442 to 271 (-171). Cumulative grafting through top-6 cycles never exceeds 271. The boundary mismatch from partial graft dominates. The multi-day oracle-aware-repair infra would face the SAME problem and is NOT justified."
metadata:
  type: project
status: refuted
---

# Oracle-aware ALNS repair (vol-109 T1 — REFUTED EMPIRICALLY)

**Status**: `refuted` 2026-05-16 ~12:50. Tested empirically via
`scripts/vol109_oracle_graft.py`.

## Empirical refutation (T1.a measurement)

Took offset=100 partial (244 placed, score 442) + vol-60's 459
record as oracle. For each σ-cycle (sorted by size desc), grafted
the oracle's `(piece_id, rotation)` at those cycle positions into
the partial. Scored the result.

| graft variant            | placed | score | Δ from partial |
|--------------------------|-------:|------:|---------------:|
| partial (baseline)       |    244 |   442 |             — |
| oracle (reference)       |    256 |   459 |             — |
| graft top-1 cycle (71)   |    244 | **271**|       **-171**|
| graft top-2 cycles (96)  |    244 |   250 |          -192 |
| graft top-3 cycles (120) |    244 |   241 |          -201 |
| graft top-4 cycles (133) |    244 |   250 |          -192 |
| graft top-5 cycles (146) |    244 |   261 |          -181 |
| graft top-6 cycles (157) |    244 |   267 |          -175 |

**Grafting DROPS the score by 170-200 points.** Cumulative grafting
through 6 cycles never recovers past 271. The hypothesis "ALNS
repair could fix this" must lift +200 points just to return to
baseline — vastly beyond ALNS's reach (which typically lifts +5-10).

## Why the graft is catastrophic

The partial achieved score 442 because its piece placements have
MANY matching edges in the non-cycle region. Grafting oracle pieces
at cycle positions creates:
- Matched edges WITHIN the grafted region (the oracle's internal
  matches at those cells) — gain.
- Mismatched edges at the BOUNDARY between grafted and non-grafted
  cells — loss.

The grafted region's boundary is significantly larger than its
interior (perimeter scaling), so boundary mismatches dominate.
Net effect: -170 points.

## What this means for vol-109 T1

The cheap test confirms the analytical concern:
[[oracle-aware-alns-repair]] (this page's previous version).
Even with halo oracle-pinning + repair fills cycle interior, the
boundary mismatch persists at the halo's outer edge. The repair
would have to fill the cycle interior AND choose pieces that
re-match the halo's outer boundary — which is over-constrained
when the halo is FORCED to oracle values that don't match the
non-grafted neighbours.

Multi-day infra not justified.

## What might still work

A successful basin-escape would require **simultaneous** changes
to:
- The σ-cycle interior (free).
- The full halo (free or oracle-pinned).
- The cells JUST OUTSIDE the halo (free) — to match the new
  halo's edge colours.

That's basically destroying ~half the board. At that point we're
no longer doing "local repair" — we're doing "find a new basin
from a tiny prefix." Which is essentially the vol-22 basin-escape
recipe (bound-ascent → Hungarian → ALNS) which we already have.

## Original concern (preserved per "no quiet deletes")

[Previous analytical text:]
The idea was: modify `repair_cells` to accept "oracle pins" so
SigmaCycleDestroy + halo-pin can unlock locked basins. The
analytical concern was that iterative halo expansion converges to
"destroy everything, replace with oracle" — trivially the oracle's
score, not higher.

The empirical test confirms this and more strongly: even ONE step
of grafting (before any expansion) drops the score catastrophically.
The expansion would have to undo all that boundary damage to even
return to the partial's baseline.

## Linked

- [[sigma-cycle-destroy]] — vol-108 T1 (refuted).
- [[sigma-cycle-predicts-alns]] — vol-107 T2 (partial).
- [[basin-escape-recipe]] — vol-22 historical version.
- [[oracle-cycle-swap]] — vol-18 `apply_cycle`.
- `scripts/vol109_oracle_graft.py` — the experiment.

## The idea (from vol-108 T1 follow-up)

Vol-108 T1 found that SigmaCycleDestroy doesn't unlock locked
basins because the halo's edge colours constrain repair. Fix:
modify `repair_cells` to accept "oracle pins" — positions where
the repair is forced to use a reference good basin's (piece, rotation).

Then SigmaCycleDestroy + halo-with-oracle-pins should:
1. Free σ-cycle cells (repair fills these).
2. Force halo to oracle's placement (removing the halo edge-colour
   lock).
3. Repair fills σ-cycle from the now-unfrozen pool.

## Why this might also fail (analytical)

Let σ_cycle = cells where current ≠ oracle. Then:
- Non-cycle cells are IDENTICAL between current and oracle (by def).
- σ-cycle pieces in current and oracle are the SAME pieces in
  different positions.

If we destroy σ-cycle + halo and force halo to oracle's pieces:
- The halo's piece-set in oracle is some subset H_ora.
- For halo to be "force-placed", we MUST have H_ora available — but
  H_ora pieces are currently placed at OTHER positions in current,
  i.e., at σ-cycle interior cells.
- Wait — that's σ-cycle by definition. So if H_ora ⊆ σ_cycle, then
  freeing σ-cycle frees H_ora and we can place them at the halo.
- But then we need pieces to fill the σ-cycle INTERIOR. Those pieces
  are H_ora's CURRENT positions — circular.

**Net effect**: destroying σ-cycle + forcing halo = SWAPPING the
σ-cycle's piece-positions between current and oracle. The "free
cells" become the σ-cycle's interior, which must be filled by
the remaining (current σ-cycle - H_ora) pieces.

Result: the FILL is constrained by:
- The halo (now oracle-pinned) — different edge colours from
  current → different constraint set.
- The boundary BEYOND the halo (still current's pieces) —
  unchanged constraint.

So the local constraint is changed; the global constraint isn't.
**Iterative halo expansion converges to "destroy everything,
replace with oracle"** — which is trivially the oracle board (so
gives oracle's score, not higher).

## What might actually work

A non-trivial fix would force MORE than just halo to oracle —
specifically, the cells where current's halo-pieces conflict with
the cells they'd need to be at in oracle. This is recursive: each
re-placement creates new constraints two cells deep, and the
recursion either terminates (a finite "blast" of cells) or doesn't.

A bounded version: destroy σ-cycle + halo_r=1 + oracle-pin halo;
if the repair can't fill σ-cycle interior, expand to halo_r=2 +
oracle-pin halo_r=2; etc. The "expansion stops" condition isn't
clear without empirical measurement.

## Bottom line

The analytical concern weakens vol-109 T1's prior of payoff. Could
still try empirically — the analytical argument might miss a
favourable instance. But the multi-day infra investment is hard to
justify given the concern.

**Decision**: defer vol-109 T1 until either:
- An empirical bounded-halo experiment refutes the analytical
  concern.
- A different formulation emerges.

## Linked

- [[sigma-cycle-destroy]] — vol-108 T1 origin.
- [[sigma-cycle-predicts-alns]] — vol-107 T2 hypothesis.
- [[basin-escape-recipe]] — vol-22 historical version of this idea.
- [[oracle-cycle-swap]] — vol-18's `apply_cycle` approach.
