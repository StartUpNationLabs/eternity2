# VOL-59 — Joe's iteration-budget prune-restart policy

**Open**: 2026-05-15 (mid autonomous session, post-vol-58)

## Mandate

Per autonomous-mode + don't-stop-unilaterally. The lottery is running
in background. Concrete next experiment that builds on existing
infra: Joe's iteration-budget prune-restart policy.

## Why this experiment

Vol-23 built `mcgavin-prune-restart` with depth-based triggers.
Vol-50 added node-budget axis. **Joe's policy** (from BACKLOG since
vol-32, per community msg #11725) is a DIFFERENT triggering policy:

> 99% of canonical-E2 cold-start time is spent at depth >132; with
> 150 correctly-placed tiles a solution is found in <1500 iters;
> therefore prune to depth 150 every 2000 iters when depth>150 has
> consumed >2000 iters without progress. 30-49% search-space
> reduction reported.

Hypothesis: short rounds with strict depth-growth-or-restart will
produce DEEPER CP partials than vol-23's fixed-time-budget rounds,
because the restart cycle escapes "stuck-at-depth" patterns.

## Approximate implementation via existing tools

Vol-23 prune_restart has:
- `--node-budget` (vol-50): per-round node cap.
- `--min-depth-growth`: threshold for "round was productive".
- `--rounds`: total rounds.
- `--drop-k`: cells dropped on restart.

Joe's policy approximation:
```
prune_restart \
    --node-budget 2000 \
    --rounds 200 \
    --min-depth-growth 1 \
    --drop-k 20 \
    --cp-budget-ms 60000
```

This runs short rounds; each must grow depth by ≥1 to be kept,
otherwise drop 20 cells and try again. 200 rounds × 2k nodes =
400k nodes total. Modest compute (~30 min on 1 core).

## Vol-59 plan

1. **WAIT for lottery to complete** (so we have free CPU).
2. Launch the experiment above with seeds 1, 2, 3, 4 in parallel.
3. Measure: final depth + score per seed.
4. Compare to vol-23 baseline (depth ~150).
5. If Joe's policy reaches deeper partials, hand off to ALNS for
   record-chase.

## Vol-59 T2 — lucky-snapshot follow-up

Lottery mid-analysis (80 of 156 jobs): **thread 601 produces the
richest basins**.

| Snapshot | n_seeds | max | mean | std |
|---|---:|---:|---:|---:|
| t601_s002_d207 | 4 | **458** | 453.8 | 4.71 |
| t601_s001_d206 | 4 | 457 | 449.2 | 7.08 |
| t600_s002_d212 | 4 | 456 | 453.2 | 4.21 |

The single 458 came from t601_s002_d207. Two adjacent partials
(t601_s001/s002) gave 458 + 457. **Thread 601's basin family has
elevated 458-probability**.

Follow-up: run more seeds (e.g., 16-32) × longer ALNS (15-30 min) on
`t601_s002_d207`. If 458 was lucky, we'd expect ~1/16-32 hits. If
the basin is richer than that, maybe a 459 exists.

Compute: 32 seeds × 30 min / 8 cores = 2 hours wall.

## Linked

- BACKLOG `joe-iteration-budgeted-prune`
- [[prune-restart]]
- [[vol-58]] — predecessor
- memory: `feedback_autonomous_dont_wait`
