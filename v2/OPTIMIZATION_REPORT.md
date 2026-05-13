# Eternity II optimization report

Date: 2026-05-13

## Executive verdict

The highest leverage improvement is not raw speed. It is making each run scientifically reproducible, then spending the saved wall-clock on more independent starts.

The session diagnosis is directionally right: CP and ALNS both plateau early, so long single chunks waste most of the budget. The main correction from reading the code is that the current default `run_e2_blackwood` ALNS path is **SA-primary**, not CP-primary. Therefore the same-seed ALNS variance in the current overnight path is more likely caused by **wall-clock-bounded SA repair** than by `cp_repair`'s parallel `gacolor_ac3_par`. Parallel CP repair is still a real reproducibility hazard for CP-primary experiments, but it is not the first suspect for the default `winning5`/SA path.

Recommended priority:

1. Make repair deterministic under a fixed seed.
2. Add true ALNS stagnation stop/pivot, not just restart.
3. Add CP depth-stagnation cancellation and fix CP depth reporting.
4. Reallocate overnight budget from long chunks to many deterministic chunks.
5. Continue algorithmic work only after the measurement layer is clean.

## Code findings

### 1. Default ALNS does not call `cp_repair`

`run_e2_blackwood` builds `AlnsConfig` with `repair: RepairKind::Sa`:

- `crates/bench-audit/src/bin/run_e2_blackwood.rs:147-164`
- `crates/localsearch/src/alns.rs:1147-1156`

`cp_fallback_to_sa` is only used when `cfg.repair == RepairKind::Cp`. With `RepairKind::Sa`, `repair()` dispatches directly to `sa_repair`:

- `crates/localsearch/src/alns.rs:230-243`

So: switching `cp_repair` from `gacolor_ac3_par()` to `gacolor_ac3()` will help CP-primary ALNS runs, but it will not explain or fix same-seed variance in the default `run_e2_blackwood` path.

### 2. The stronger nondeterminism source is wall-clock-bounded SA repair

`sa_repair` sets a time budget in milliseconds:

- `crates/localsearch/src/alns.rs:208-227`

`run_sa_loop` stops by `Instant::elapsed()`:

- `crates/localsearch/src/lib.rs:1416-1424`

Given the same seed, a repair that executes 823,000 SA moves on one run and 819,000 moves on another will diverge after the cutoff. This is enough to explain fixed-seed ALNS variance, especially because each ALNS iteration seeds a nested SA run from `(cfg.seed, stats.iters)`:

- `crates/localsearch/src/alns.rs:1145-1147`

Fix: add an iteration-budget mode for repair. For deterministic experiments, set `SaConfig.max_iters` and leave `SaConfig.time_budget_ms = 0`. Calibrate `repair_budget_ms` to a fixed move count once, then compare configs using fixed work rather than fixed wall time.

### 3. `cp_repair` is parallel and should be configurable

`cp_repair` currently constructs `EngineSolver::gacolor_ac3_par()`:

- `crates/localsearch/src/alns.rs:180`

That is a valid throughput choice but a bad default for single-run scientific A/Bs. The right fix is not a hard delete of parallelism; make it configurable:

- `RepairKind::CpDeterministic` or `AlnsConfig.cp_repair_parallel: bool`
- default deterministic in benchmark/audit binaries
- allow parallel in throughput portfolio runs

If CP repair remains time-bounded, single-threaded CP is still not perfectly comparable across machines, but it removes Rayon scheduling races from the equation.

### 4. ALNS stagnation is only a reset, not a stop

`run_alns` hard-codes `stagnation_limit = 60` and resets `current` to `best`:

- `crates/localsearch/src/alns.rs:1120-1127`
- `crates/localsearch/src/alns.rs:1211-1225`

It does not return, pivot operator set, reduce temperature, or record stagnation metadata. This matches your observation: after early bests, the run cycles through restarts until wall-clock expires.

Fix: replace the hard-coded behavior with config:

```rust
pub enum StagnationAction {
    Restart,
    Stop,
    PivotOps,
}

pub struct AlnsConfig {
    pub stagnation_iters: u32,
    pub stagnation_action: StagnationAction,
    pub min_iters_before_stop: u32,
}
```

For overnight science runs, use `Stop` after 40-60 iterations without a new best. For interactive polishing, keep `Restart`.

### 5. Acceptance makes temperature mostly irrelevant on iso-score plateaus

`Acceptance::SimulatedAnnealing` accepts every `delta >= 0`, including all `delta == 0` moves:

- `crates/localsearch/src/alns.rs:854-860`

The overnight logs show 100% accepted moves in the full11 runs. On a landscape dominated by equal-score moves, temperature cannot matter much because most moves bypass the Metropolis probability entirely.

Fixes to test:

- `StrictSa`: accept `delta > 0`, probabilistic only for `delta < 0`, and handle `delta == 0` through a secondary objective.
- `Lexicographic`: enable/extend `lex_break_isoscore` and only accept neutral moves that reduce largest mismatch component, forbidden-edge count, or row-region entropy.
- `LateAcceptance`: compare to score from `L` iterations ago, useful on plateaus without accepting every neutral move.
- Lower reward for neutral accepted moves. Current `sigma_accept_worse = 13` can reward neutral wandering more than true improving moves (`sigma_improve = 9`).

### 6. CP depth reporting has a discrepancy

In `chunk_0019/cp.log`, live progress reached `best_depth=193`, but the terminal event reported `max_depth_seen=192`. `run_e2_blackwood` prefers `stats_cp.max_depth_seen` over `sink.best_depth`:

- `crates/bench-audit/src/bin/run_e2_blackwood.rs:121`

Parallel aggregation separately tracks `best_depth` and `final_stats.max_depth_seen`:

- `crates/solver-engine/src/parallel.rs:220-241`

Fix reporting by using the maximum of all available values:

```rust
let cp_depth = stats_cp
    .as_ref()
    .map(|s| s.max_depth_seen.max(sink.best_depth))
    .unwrap_or(sink.best_depth);
```

Also consider making parallel final stats set `final_stats.max_depth_seen = final_stats.max_depth_seen.max(best_depth)` before emitting terminal events.

## Budget policy

Current 10+10 minute chunks are inefficient for discovery. The evidence in `RESEARCH_NOTES_17.md` and `RESEARCH_NOTES_17_OVERNIGHT.md` shows:

- CP reaches depth 192/193 early and then backtracks heavily.
- ALNS new bests stop around iteration 33 in the representative long run.
- Overnight ALNS chunks still ran 228-400 iterations.

Use this budget policy for the next serious run:

| Stage | Default now | Proposed science mode |
|---|---:|---:|
| CP | 300-600 s | 90-150 s, stop if no depth gain for 60 s |
| ALNS | 300-600 s | stop after 40-60 no-best iterations |
| Repeats | long n=1 chunks | n>=3 per config, many configs |
| Repair | wall-clock SA/CP | fixed repair steps for deterministic A/B |

For final record attempts, keep a separate "record mode" with larger budgets. Do not mix record mode with hypothesis testing.

## Concrete implementation plan

### Phase 0: measurement cleanup

1. Add `AlnsConfig.repair_step_budget: u64` or `SaConfig.max_iters` plumbing through `sa_repair`.
2. Log per-ALNS repair iterations and total repair iterations in `AlnsStats`.
3. Add `AlnsConfig.cp_repair_parallel` or a CP repair profile enum.
4. Fix CP depth reporting as above.
5. Include `best_score_history`, stagnation count, and stop reason in every saved ALNS JSON.

Expected result: fixed seed plus fixed initial board produces identical ALNS board/score across reruns.

### Phase 1: budget control

1. Replace hard-coded ALNS stagnation restart with configurable `Restart`, `Stop`, and later `PivotOps`.
2. Expose CLI flags in `run_e2_blackwood`, `alns_only`, and `alns_portfolio`:
   - `--alns-stagnation-iters`
   - `--alns-stagnation-action restart|stop`
   - `--repair-steps`
   - `--cp-repair deterministic|parallel`
3. Add CP early stop through a sink-level cancellation policy: after `min_cp_ms`, if `best_depth` has not improved for `cp_stagnation_ms`, `should_continue()` returns false.

Expected result: 3-5x more chunks in the same wall-clock without losing meaningful signal.

### Phase 2: experimental defaults

Use these defaults for the next overnight:

- schedule: `calibrated_v17b`
- op set: `winning5`
- repair: SA-primary, deterministic fixed-step repair
- ALNS stop: 50 no-best iterations after minimum 30 iterations
- CP stop: 90 s minimum, 60 s no-depth-gain stop
- repetitions: n=3 per config minimum
- tested variants: `v17b`, `v17e`, H22 tie shuffle, and one acceptance variant

Keep `full11` only as an ablation. The repo already records that `winning5` is the empirical best set:

- `crates/bench-audit/src/bin/run_e2_blackwood.rs:36-75`

### Phase 3: algorithmic work after determinism

Only after the above is stable:

1. Test neutral-move policy changes, because iso-score wandering is the dominant ALNS failure mode.
2. Test schedule diversity (`v17e`) as the main CP-level diversity lever.
3. Add a pivot action after stagnation: switch from `winning5` to a narrow diversity-injection set for 10-20 iterations, then return.
4. Revisit CP-primary repair with deterministic single-thread CP, but treat it as a separate algorithm, not a drop-in replacement for SA-primary.

## Bottom line

Your proposed "stop or pivot ALNS when it stops finding new bests" is correct and high leverage.

The proposed "make parallel `cp_repair` deterministic first" is only partly correct. It is necessary for CP-primary experiments, but the current default ALNS path uses SA repair, and that SA repair is wall-clock bounded. The first reproducibility fix should therefore be fixed-step SA repair, plus configurable deterministic CP repair for the CP-primary branch.

Once repair is deterministic, shorten chunks aggressively and spend the recovered budget on repeated schedules and seeds. That will produce cleaner evidence than another long single-run plateau.
