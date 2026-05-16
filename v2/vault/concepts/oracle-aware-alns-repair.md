---
name: oracle-aware-alns-repair
description: "Vol-109 T1 candidate — analytical concern. Continuation of vol-108 T1 SigmaCycleDestroy refutation. Idea: destroy σ-cycle + halo, force halo to oracle's pieces, let repair fill cycle interior. Concern: even with halo oracle-pinned, the boundary BEYOND the halo still constrains, just one halo-ring further out. Iterative halo-expansion converges to 'destroy everything, replace with oracle' — which is trivially the oracle. Need a more principled formulation before building."
metadata:
  type: project
---

# Oracle-aware ALNS repair (vol-109 T1 — concern documented before build)

**Status**: `unbuilt` with analytical concern. 2026-05-16 ~12:40.

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
