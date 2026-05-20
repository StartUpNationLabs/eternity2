# Current vol — vol-51 (opening) — 2026-05-15

**Predecessor**: vol-50 closed with net negative result on records (best
ALNS lift was +4 over vol-23 baseline; blackwood_raw 1h × 4 FAILED due
to CPU oversubscription). See [[vol-50]].

This page started life as a vol-51 draft written DURING vol-50 to
ensure the autonomous loop had a next step. Branches A/B/C below
reflect that. **Branch B is what actually happened**.

## Vol-51 binding item (revised 2026-05-15 mid-session)

**B1 was built but the recovery path is broken. Pivoting to B3 (engine
throughput profiling, scoped only to measurement + write-up).**

### B1 disposition

Shipped clean infrastructure:
- `relaxed_bound` extracted to `bench-audit` lib.
- `prune_restart` accepts `--bound-trigger` flag.
- Per-round bound logged in summary.csv.

The trigger logic CORRECTLY detects full-board + score-stagnant and
escalates drop_k. But the recovery path is broken: dropping 60 cells
(actual: 164 with halo) leaves CP unable to refill in 30s budget;
round 5 score collapses to 188 from 412. **B1 doesn't produce score
lift as implemented.**

Possible fixes (not pursuing this vol):
- Increase per-round CP budget for recovery rounds (5+ min each).
- Drop policy that doesn't expand halo (cap at k=60 strict).
- LNS-style recovery (re-run CP only on the dropped subset, not
  whole board).
- Fresh random seed per recovery round.

The original goal of B1 (different trigger than depth/node) is met;
the new finding is that the recovery is the bottleneck, not the
trigger.

### B3 — engine throughput profiling (locked in)

Community engine ≈ 295M nps, ours ≈ 75k aggregate / ~10k per worker.
4000× gap. McGavin engine parity would close this gap and let
existing algorithms break the depth-27 cold-start wall.

**Scope for vol-51**: PROFILING and ANALYSIS only — not the full
optimization build (which is multi-week).

1. Run our hot profiles (`joe_depth150_bp_par`, `BLACKWOOD_RAW_PAR`)
   under `cargo flamegraph` for representative 60s runs.
2. Identify top 5 hot functions by self-time.
3. Compare each to expected McGavin-style implementation patterns
   (per [[mcgavin-engine]] notes + community E2 commentary).
4. Write durable per-hot-path notes in `vault/concepts/engine-perf-hot-paths.md`
   (already exists from vol-25; amend with vol-51 measurements).
5. Identify the top 1-2 wins that would close ~10× of the gap (not
   100×).

This produces durable research output (vault notes + numbers) that
any future engine-perf volume builds on, even without a record this vol.

### Rationale for the pivot

Per CLAUDE.md "Don't stop unilaterally; pivot to a real next
experiment". B1's trigger axis is exhausted as a record-track path.
B3 profiling is a real next experiment that:
- Cannot fail to produce knowledge.
- Doesn't risk further CPU waste.
- Sets up future engine-perf work with concrete measurements.

## Branch trail (kept for historical reasoning)

### Branch A: (would have applied if vol-50 produced ≥ 458) — DID NOT APPLY

Record-class result. Vol-51 priorities:
1. **Reproduce at >1h budget × more seeds**. 1h × 16 seeds in 4
   batches of 4. Total ~4h. EV: confirm + collect basins.
2. **ALNS-lottery from the new partial × 16 seeds × 5min**.
3. **PT lottery from any new ≥457 board × 1h × N seeds**.

### Branch B: vol-50 plateaued (HAPPENED) — vol-51 = bound-trigger build

Vol-51 binding item candidates (one max):

#### B1. McGavin's prune-restart bound-trigger (BACKLOG vol-36 T2)

Different trigger than vol-23's CP-depth trigger and vol-50's
node-budget trigger: **trigger restart when bound-improvement stalls**.
Bound is computed by `edge_bound_ascent` (already shipped).
- Build: ~1-2 days. Modify `prune_restart` to call bound-ascent
  between rounds; if bound at round N == bound at round N-1, restart.
- EV: bound-improvement stall is a true basin-lock detector
  (stronger than depth-stall). Restart from stalled bound might find
  basins of different ceiling.

#### B2. Per-seed warm-PT recipe at 1h × 16 seeds from vol-32 records

vol-22 found 469-ceiling basins via basin-escape from a 457. But
**we never ran PT for 1h from vol-32's specific 458 record**.
Vol-32 RECORD_BREAK_458 → PT 1h × 16 seeds is the most basin-
specific compute we haven't tried.
- Build: 0 (existing pt_e2).
- EV: 1h × 16 ≈ 16h compute; vol-22 record-class output would be
  another saturated 458 or a new 459/460 basin.
- Risk: comfort-lottery. The vol-32 close memory says "458 basin
  PROVEN locally optimal under MIP cluster-repair", suggesting PT
  on the SAME basin returns nothing.

#### B3. McGavin engine parity (vol-25 BACKLOG, multi-week)

Community engine = 295M nps; ours = ~75k aggregate (~10k per worker).
4000× gap. Closing this is multi-week. Quantified expectation: at
295M nps, our existing algorithms in 60s would search 17B nodes
(vs current 4.2M aggregate). That's enough to break the depth-27
wall on cold-start. **Could be the actual record-breaker.**
- Build: profile the hot paths in BLACKWOOD_RAW and joe_depth150_bp;
  measure ours vs published McGavin nps; identify the gap.
- EV: very high if successful.
- Risk: multi-week, big-build risk.

### Branch C: vol-50 blackwood_raw+MRV fails (< 457)

Less likely but possible. The 1h × 4 parallel sharing 170%/worker
could be slower than vol-32's full-CPU 10min runs.

Then vol-51 = re-run vol-32 recipe EXACTLY (single seed, full CPU,
5min, ALNS-5min). Validates reproducibility.

## Recommended pre-commit (vol-51 binding item)

Pending vol-50 close. Best guess: **B1 (McGavin bound-trigger
prune-restart)** because:
- Distinct from vols 23/50 (depth-trigger, node-trigger). Genuinely
  unfetched search-side axis.
- Build is contained (1-2d), measurement is contained.
- EV: medium. Probability of record-break ≥ 5%, much higher than
  another lottery on existing partials.

Backup if B1 surprises: **B3 (McGavin engine perf)** scoped to "profile
and identify the gap" only — research-grade preparation work that
DOES NOT require multi-week build to be valuable.

## VOL-46 LP-UB-479 CONTEXT (critical for vol-51 thinking)

Vol-46 found a basin with LP UB = 479 ("class D"). 8 ALNS-diverse
seeds × 1h: ALL 8 plateau at 457. MIP on 28-cell mismatch union:
delta=0 in 0.46s — **proven locally optimal at 457**.

Across basin classes A/B/C/D, the LP UB → integer-best gap is
uniformly ~20 points. **Local search cannot close this gap**.

What this implies for vol-51:
- More basin diversification (PT, ALNS lotteries) ≈ comfort lottery.
- The gap is a property of the SEARCH ALGORITHM, not basin choice.
- Breaking 458 requires: (a) McGavin throughput parity (raw bandwidth
  closes the gap), (b) no-good CDCL learning in solver-engine, or
  (c) multi-day MIP on specific basins.

This pushes vol-51 strongly toward **algorithm-side innovation**,
not lottery. B1 (bound-trigger) is still good because it's
algorithm-shaped; B3 (engine parity) is now the highest-EV
multi-week direction.

## Vol-50 CPU-oversubscription lesson

Mid-vol-50 (2026-05-15 11:35) observation: my 4-parallel
`run_e2_blackwood` runs each got ~170% CPU (rayon auto-throttled
under contention). Vol-32's 458 record was via vanilla_fast + ALNS
**at 800% CPU single-seed**. My 4×170% = 680% total spread, so each
seed effectively runs ~12 min of single-thread-equivalent compute
over the 1h wall.

**Result**: 1h × 4 parallel = 1h-equivalent per seed, NOT 4× vol-32's
10min. Same effective budget per seed as vol-32, just diversified
across 4 seed initializations.

**Lesson for vol-51 + future big-CPU experiments**: parallel-of-N runs
of an already-parallel solver gives N× diversification, NOT N× per-seed
compute. To compete with vol-32's 458 wall-time, must run SEQUENTIALLY
at full CPU. With 4 seeds × 1h sequential = 4h wall budget needed
for a clean N=4 lottery.

This insight changes vol-51's planning math: for any "more compute on
existing algorithm" experiment, **either** run sequentially at full
CPU **or** use a different (low-CPU-cost) inner algorithm.

## Audit-at-open targets (when vol-51 actually opens)

Aged ≥ 3 vols (from BACKLOG):
- `mcgavin-prune-restart-bound-trigger` (since vol-36)
- `unsat-soft-value-order-vol37` (since vol-34)
- `joe-iteration-budgeted-prune` (since vol-32 open) — **resolved by vol-50**
- `multi-cell-bound-ascent` (since vol-22, deferred vol-31, still aged)
- `bound-floor-alns-with-per-step-check` (since vol-22, deferred vol-27)
- `restore-or-simd` (since vol-25 perf)
- `precompute-cell-nb-info` (since vol-25 perf)
- `vault-validation-of-perf-wins` (since vol-25)

Most are stale. The discipline at vol-51 open: each gets a real
decision (pick / wont-do / argue).
