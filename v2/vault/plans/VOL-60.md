# VOL-60 — long-ALNS lottery + queued engine work

**Open**: 2026-05-15 (continuation after vol-59 close)

## Mandate

Per autonomous-don't-wait: vol-59 closed with negative-on-record but
positive-on-process. The session has shown 458 is locally tight at
every angle of attack we have. Vol-60 tests one more empirical angle
(long-ALNS budget) and queues the next layer of engine work.

## T1 — long-ALNS lottery (RUNNING)

Launched 15:34 CEST.

40 jobs queued: 5 top-vol-59-snapshots × 8 seeds × 60min ALNS.
- snapshots: `t601_s002_d207`, `t606_s002_d211`, `t601_s001_d206`,
  `t600_s002_d212`, `t602_s002_d207`.
- Compute: ~5h wall on 8 cores. ETA ~20:30 CEST.

Hypothesis: vol-59 lottery used 5min ALNS, found 1×458 (0.64%). With
12× longer ALNS on already-strong snapshots, P(458) and tail
probability might shift. If P(459+) > 0 across 40 jobs, lottery wins.

Analysis script: `/tmp/vol60_analysis.py`.
Monitor armed for 458+/459+ events.

## T2 — engine modifications queued (NOT RUNNING)

Three deferred engine modifications, each ~1-2 days work, that
together would test the McGavin/Blackwood gap:

### T2a — EdgePairLookup value order
Per memory: Blackwood's pruner #1 is "(left_color, up_color) →
sorted piece list" per cell. Add `ValueOrder::EdgePairLookup`. Cheap
implementation; the precompute is just a 2D bucket per (color, color)
pair. ~1 day.

### T2b — Monotone color-count curve propagator
Per memory: Blackwood's pruner #2 enforces "3 specific colors must
keep cumulative count above empirically-tuned piecewise-linear curve
over depth". Similar to vol-12's NS-1 propagator but with depth
conditioning. Tuning the curve requires data from successful Blackwood
runs (which we don't have post-vol-15-depth-wall). ~1-2 days.

### T2c — Scheduled mismatch relaxations
Per memory: Blackwood's pruner #3 allows ONE mismatch at 10 specific
depths. Requires engine support for "AC-3 pass with K allowed
mismatches". Engine refactor: instead of binary success/fail, return
"failed with N mismatches"; if N ≤ K_at_current_depth, continue. ~2
days.

T2a is the most contained; T2b+T2c together replicate Blackwood. Vol-60
should pick T2a first if time permits (after T1 lottery completes).

## T3 — CDCL with E2-specific compact clauses (DEFERRED)

Vol-59 T4 found SAT-style 1-UIP doesn't help E2 (flat cause-graph).
Alternative: store clauses in COMPACT form using per-cell-forbidden-pid
sets instead of literal lists. Multi-day work; defer until vol-60 T1+T2a
have run.

## Vol-60 decision tree

- If T1 finds 459+: standing record breaks, full vol-60 closure on
  this finding.
- If T1 plateaus at 458 (likely): T2a is the next concrete experiment.
- If T2a doesn't break record: T2b+T2c full Blackwood replication or
  pivot to CDCL compact clauses.

## Linked

- [[../sessions/vol-59]] — predecessor
- [[../sessions/SESSION_2026-05-15_summary]] — session summary
