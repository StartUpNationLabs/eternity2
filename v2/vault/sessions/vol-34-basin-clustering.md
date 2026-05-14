# vol-34 — vanilla_fast 8-thread basin clustering analysis

**Date**: 2026-05-14 (mid-vol)
**Status**: empirical finding from T1's 30-min probe

## Headline

Vol-34 T1's 30-min `vanilla_fast --threads 8 --pin-hints` probe
produced 14 snapshots at depth ≥ 200. **These 14 snapshots cluster
into only 5 distinct basin families**:

| Thread | Snapshots | Basin family |
|---:|---:|---|
| 00 | 4 | A (prefix ~87-90 shared) |
| 01 | 2 | B (prefix ~82 shared) |
| 04 | 4 | C (prefix ~80-82 shared) |
| 05 | 2 | D (prefix ~85 shared) |
| 07 | 2 | E (prefix ~82 shared) |

Threads 02, 03, 06 never reached depth 200 — got stuck in shallow
basins. **5/8 = 62% productive thread utilization**.

## Pairwise prefix-agreement (length of identical row-major prefix)

Within a thread family: 80-90 cells agree.
Across thread families: 0-1 cells agree (just the canonical hints
at positions 34, 45 in early prefix).

```
                t00 t01 t04 t05 t07
t00              -   0   0   0   0
t01              0   -   1   0   0
t04              0   1   -   0   0
t05              0   0   0   -   1
t07              0   0   0   1   -
```

## Implication

The 8 threads each pick a different early prefix (via the
per-thread bucket shuffle, seeded from thread_id), but each
prefix locks the thread into a single basin family. Once a
thread's chosen early branches commit, the rest of the search
just explores variants of that one configuration.

The T3 lottery (14 partials × 4 seeds × 5min) lottery becomes a
within-basin sweep, not a between-basin one. ALNS from any of the
4 partials in thread-00 will find the same basin ceiling because
they share 87+ cells of identical prefix.

## Action items for vol-35

1. **Run vanilla_fast with 16-32 threads** (oversubscribed but on
   M1's 8 cores). More distinct early prefixes → more basin
   diversity.
2. **Use `--snapshot-on-visit`** (new vol-34 flag) to capture
   diverse partials WITHIN a basin's exploration, not just the
   max-depth representatives. This may also surface micro-diversity
   within a basin family.
3. **Add a per-thread `--initial-shuffle-seed`** flag so vol-35 can
   run many independent vanilla_fast instances in series (or
   chained via xargs) instead of relying on 8 thread-shuffles.

## Linked

- [[trajectory-families]] — vol-18's finding that score-distance ≠
  configuration-distance. Generalizes here: thread-distance ≠
  basin-distance.
- [[vanilla-fast-backtracker]] — the throughput-king built vol-32.
