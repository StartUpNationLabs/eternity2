# Vol-35 — ALNS recovery from high-bound boards

**Date**: 2026-05-14 (vol-35 mid-vol).
**Status**: testing vol-22's basin-escape claim with current ALNS+bug-fix.

## Premise

Vol-21 produced bound-470 boards via bound-ascent SA (`v21_bound_ascent_b470_s*.json`).
The boards have HIGH BOUND (470) but LOW SCORE (~100). Vol-22's
basin-escape recipe claimed ALNS-recovery from these stuck at ~452,
30 below the bound.

With vol-34's bug fix (piece_swap_hillclimb + alns_only filename
collision), the recovery result might be different. AND with longer
ALNS budgets and stronger ops.

## Experiment

```
./target/release/alns_only --cp-board output/v21_bound_ascent_b470_s101.json \
    --alns-budget-ms 300000 --seed 1 --ops mega_mix --repair-kind sa
```

## Result

| Setup | Start score | ALNS end | Bound | Gap |
|---|---:|---:|---:|---:|
| b470, 60s winning5 | 101 | 384 | 470 | -86 |
| b470, 300s mega_mix | 101 | **400** | 470 | -70 |
| b475, 300s mega (in flight) | 58 | TBD | 475 | TBD |

**Key observation**: ALNS recovers from score 101 to 400 (+299) in
60s, then only +16 more in 300s. The marginal gain per second is
huge initially then collapses.

## Comparison to vol-22

Vol-22 claimed "stuck at ~452" — much higher than my 400. Possibly:
- Vol-22 used different starting bound (b465, not b470)
- Different ALNS ops (vol-22 used different operators)
- The bug fix may have changed behavior

Score 400 with gap=70 to bound is far from a record (458). Confirms
vol-22's conclusion that high-bound boards aren't recoverable to bound.

## Vol-35 hypothesis to test

The bound-ascent recipe shouldn't be used as a record-chase tool;
instead, it's diagnostic — it tells us the basin family's *structural
ceiling*. To break 458, we need a basin family whose **score-recoverable
ceiling** is > 458, not just bound > 458.

The "score-recoverable ceiling" = best ALNS-result from any partial
in the basin family. For vol-32/34's vanilla_fast basin families,
score-recoverable ≈ 457 (per vol-34 T3 data). For vol-22's basin-escape
basin family, score-recoverable ≈ 452 (per vol-22). Both are below 458.

A 458-recoverable basin family is what we need to find. Vol-35 T1's
thread-id sweep + per-family lottery should reveal whether such a
family exists.
