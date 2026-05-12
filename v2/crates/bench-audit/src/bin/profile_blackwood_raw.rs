// Vol-15 — single-threaded profiling target for `samply record`.
//
// Runs `BLACKWOOD_RAW` (no AC-3/gacolor/NS-1) on canonical E2 for
// 60 s single-threaded, with no event logging. Designed to be a
// clean profiling target:
//   - single-thread, so CPU samples are unambiguously this work.
//   - 60 s, long enough to amortise warmup but short enough to
//     finish quickly.
//   - no progress log, no JSON output — just solve and exit.
//
// Run with: samply record ./target/bench-fast/profile_blackwood_raw

use std::path::PathBuf;
use std::sync::Arc;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_solver_engine::{
    blackwood_schedule_469, EngineConfig, EngineSolver,
};
use eternity2_solver_trait::{SolveOpts, Solver};

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");

    let schedule = blackwood_schedule_469(&puzzle, &hints).expect("schedule");
    let schedule_arc = Arc::new(schedule);

    // BLACKWOOD_RAW (single-thread variant — no Parallelism::RootSplit)
    let solver = EngineSolver::new(
        EngineConfig::BLACKWOOD_RAW,
        "engine",
        "blackwood_raw_profile",
    )
    .with_blackwood_schedule(schedule_arc);

    let mut opts = SolveOpts::default();
    opts.time_budget_ms = 60_000;
    opts.seed = 1;
    opts.hints = hints;

    let mut sink = eternity2_events::NullSink;
    let mut solver = solver;
    let outcome = solver.solve(&puzzle, &opts, &mut sink);
    eprintln!("done: {outcome:?}");
}
