# Vol-37 — re-evaluation mid-session

**Date**: 2026-05-14 16:48 CEST.
**Context**: ~4 hours into autonomous run. User asked "take a deep breath
and re-evaluate what you are doing/planning".

## What I had been doing

- Vol-37 lottery (140 ALNS runs from 7 canonical partials × 5 seeds × 4 ops)
- Vol-38 plan (32-seed lottery from regenerated blackwood_mrv partial)
- Both = ~5h compute on the M1 8 cores

## Why I cancelled both

**Vol-37 lottery (canceled after 4 results)**:
- 4/4 runs gave 451/480 from canonical 446 source. Saturated plateau.
- 3 of 7 starts are already-canonical 457s. ALNS from those would test
  "can ALNS escape the 457 attractor?". Vol-22 already showed 457 is
  ALNS-locked under all current ops. So that part of the lottery would
  confirm known dead-end.
- 4 of 7 starts are make-canonical 446-447 partials. ALNS from those
  (small lottery already done with 8 seeds × 5min) capped at 454. More
  seeds → maybe 455-456 but unlikely 458+.
- Expected best: 454-457. Doesn't break records.

**Vol-38 lottery (cancelled before launch)**:
- Same partial as vol-32 (deterministic CP). 8 seeds gave 1×457 in vol-32.
- 32 seeds → ~4×457 expected by Poisson. P(any 458) ≈ very small.
- Still on the saturated 457 attractor.

## Why these were wrong

Both were **luck-chase on saturated basins**. Confirmed wisdom: when an
ALNS attractor has been hit by ≥3 distinct seeds and remains saturated
across budgets (vol-22 measured this for 457: stable across 60s, 5min,
15min, 30min), MORE SEEDS gives Poisson scaling but doesn't break out.

To break 458, need either:
1. A DIFFERENT basin family (vol-22 basin-escape recipe)
2. A STRONGER repair operator (ALNS plateau is ALNS-shaped, not
   true-optimum-shaped)
3. A NEW algorithm class (RL self-play, exact MaxSAT, etc.)

I was running #2 weakly. The same ops + same starting basins =
predictable plateau.

## New plan (revised vol-37)

**T1 (in flight)**: PT-from-canonical-454 hot exploration.
- Vol-6 historic 454 record came from PT-from-453. Same approach;
  fresh basin (we just produced canonical 454).
- 8 replicas × T_min=0.05, T_max=2.0 × 30min = ~50k rounds.
- First 60s already gave global_best=455 (+1 over start). Promising.

**T2 (next)**: prune_restart multi-round cold-start.
- The Joe-iter-prune spirit: multi-round prune-restart from canonical hints.
- prune_restart cold-start ROUND 1 reaches depth 27 / score 23.
- Round 2 (batch-pin all from round 1) reaches depth 150 / score 289.
- The ROUND 2 partial → ALNS could give a fresh canonical attractor.

**T3 (later)**: stronger ALNS repair operators.
- Houdayer cluster swap implemented properly.
- The "destroy 50 cells in a cluster + multi-step SA repair" operator.

## What I'm NOT doing this volume

- ❌ Lottery on saturated basins.
- ❌ Engine changes (vol-37 was originally "Joe iter-prune engine" but
  I realized prune_restart driver is enough; engine plumbing exists).
- ❌ ML training (vol-29 hit imitation ceiling; RL = vol-40+).

## Records ledger (no change yet)

| score | canonical | source |
|---:|:---:|---|
| 458 | 3/5 | vol-32 vanilla_fast → ALNS |
| 457 | 5/5 | vol-32 blackwood_mrv × 3 |
| 454 | 5/5 | vol-36 make-canonical → ALNS seed 5 |

Cold-start non-canonical: 458. Cold-start canonical: 457. New from this
session: 454 canonical (not a record, but a new path).

## Active compute (16:53)

- 1× pt_e2 (8 replicas, 1800s budget) from canonical 454.
- Monitor armed for global_best ≥ 456.
