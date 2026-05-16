---
name: sigma-cycle-destroy
description: "Vol-108 T1 — built a SigmaCycleDestroy ALNS operator (+ halo variant) that destroys cells along the largest σ-cycle to an oracle good basin. Tested on offset=100 partial (max-cyc 71, baseline ALNS-lift 446). Result: NO IMPROVEMENT (448 with or without sigma op). The destroy-and-let-repair-figure-it-out approach doesn't work because the σ-cycle's structural lock comes from the HALO constraints, not the cycle cells themselves. The oracle's PIECES are needed in those slots, not just cell-clearance."
metadata:
  type: project
---

# σ-cycle-aware ALNS destroy operator (vol-108 T1 — refuted)

**Status**: `refuted`. Built + tested 2026-05-16 ~11:50 CEST.
**Origin**: vol-107 T2 found that partials with max-σ-cycle > 50
to a reference 459 basin have low ALNS-liftability. Vol-108 T1
hypothesis: target those σ-cycle cells specifically with a
custom destroy op.

## What was built

`crates/localsearch/src/alns.rs::SigmaCycleDestroy` — DestroyOp that:
1. Computes σ-permutation between current board and an oracle Board.
2. Decomposes into cycles (existing `compute_sigma_cycles` from vol-18).
3. Returns largest cycle(s)' positions as the destroy set, with
   optional L∞ halo expansion.

`alns_only` bin: `--oracle <path>` flag + `sigma_only` /
`sigma_halo` / `winning5_sigma` presets.

Bug fix shipped along the way: `compute_sigma_cycles` (vol-18) was
pushing a position into the cycle BEFORE checking it was in σ's
domain, which crashed on partial boards. Vol-108 T1 fix: check
`sigma.contains_key(&q)` before push.

## Empirical results

**Test target**: offset=100 partial (depth 244, score 442, max
σ-cycle 71 to vol-60's 459 record). Baseline `winning5` ALNS on
this partial lifts to **446-448** in 60-120s.

| ops preset           | 120s seed=42 final |
|----------------------|-------------------:|
| winning5 (baseline)  |               446-448 |
| sigma_only           |                **448** |
| sigma_halo (halo=1)  |                **448** |
| winning5_sigma       |                **448** |

**No improvement.** The sigma_cycle op fires (9-13 invocations per
run), accepts at 100% rate, but the FINAL score is the same as
without it.

## Why it doesn't work

The σ-cycle is the set of cells where the partial DIFFERS from the
oracle. Destroying those cells leaves the **halo** intact — and the
halo's edge colors CONSTRAIN what pieces can refill the destroyed
cells. ALNS's repair pass picks the same locked-basin pieces.

To actually unlock, we'd need to either:

1. **Apply the oracle's pieces directly** to the σ-cycle slots
   (= `apply_cycle` from vol-18 used as a meta-move). But that's
   `OracleCycleSwap`, a different operator class — apply-not-destroy.
   The whole vol-18 work was that THIS doesn't help either,
   because the cycle in isolation has Δ < 0; only full-cycle
   application crosses the barrier with Δ > 0.
2. **Destroy σ-cycle + halo + force-place oracle pieces in the
   halo**. More invasive; the repair has to honour partial-
   placement-with-some-pieces-pinned. Vol-108 T1.c candidate.
3. **Use σ-cycle as a HINT to existing ops** rather than as a
   destroy set. E.g., bias `ConflictDriven`'s seed cell toward
   σ-cycle membership. Vol-108 T2 candidate.

## What this means for vol-107 T2's hypothesis

The vol-107 finding that "max-cycle > 50 = negative signal" still
holds — those partials ARE harder to lift. But the LOCAL fix
(target the cycle) doesn't work without an oracle-aware repair pass.

The structural lock is real; cell-clearance alone doesn't break it.

## Linked

- [[../sessions/vol-107|vol-107]] — origin of the hypothesis.
- [[../sessions/vol-108|vol-108]] — this concept's origin.
- [[sigma-cycle-predicts-alns]] — the vol-107 hypothesis (status PARTIAL).
- [[oracle-cycle-swap]] — vol-18 apply-cycle as a meta-move.
- [[basin-escape-recipe]] — vol-22 bound-ascent → Hungarian → ALNS.
