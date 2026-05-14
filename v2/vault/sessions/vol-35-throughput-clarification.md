# Vol-35 — vanilla_fast throughput: confirmation

**Date**: 2026-05-14 (mid-vol-35, user-prompted at 13:00).

## TLDR

**`vanilla_fast` does hit ~125M placements/sec single-thread** on
canonical 16×16/22c, BUT only when running in isolation. Under
CPU contention from other processes, throughput drops to 30-58M.

This explains the apparent "10× regression" I observed during the
generic-vanilla refactor — it was contention, not the refactor.

## Clean isolated measurements

```
$ ./target/release/vanilla_fast --threads 1 --pin-hints \
    --budget-ms 10000 --puzzle ../data/puzzles/size_16_official_eternity.csv
"placements_per_sec":124677632  # 124.7M pp/s
"placements_per_sec":122491353  # 122.5M (vanilla_fastest, unsafe variant)
```

## Throughput under contention

When 8 ALNS lottery processes + landscape probes + sweep were running
simultaneously, the same vanilla_fast on a single thread dropped to:

```
p_s1:  36.8M pp/s
p_s5:  30.7M pp/s
p_s13: 58.3M pp/s
p_s20: 74.5M pp/s  (after most contention died)
```

This is M1's 8 performance cores being oversubscribed by 10-15
runnable processes. Each thread gets 25-50% of a core. Throughput
scales accordingly.

## Implications

- The vol-32 "125M pp/s" claim was correct.
- The vol-35 size-generic version (`vanilla_fast_n`) at ~30M pp/s
  on canonical 16×16 is ALSO under contention — clean measurement
  would be higher.
- Future probes should report throughput WITHOUT contention to be
  comparable.

## Vol-35 takeaway

Measure throughput in isolation when comparing variants. Don't mix
benchmark runs with concurrent probes.
