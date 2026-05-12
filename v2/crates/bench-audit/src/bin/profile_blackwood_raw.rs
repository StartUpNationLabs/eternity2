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
    // Vol-16 — shortened default to 15s for the alloc-cleanup A/B
    // (full 60s available via `E2_PROFILE_MS=60000`).
    let budget_ms: u64 = std::env::var("E2_PROFILE_MS")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(15_000);
    opts.time_budget_ms = budget_ms;
    opts.seed = 1;
    opts.hints = hints;

    let mut sink = eternity2_events::BufferSink::default();
    let mut solver = solver;
    let t = std::time::Instant::now();
    let _outcome = solver.solve(&puzzle, &opts, &mut sink);
    let elapsed_ms = t.elapsed().as_millis() as u64;
    let nodes: u64 = sink.events.iter().rev()
        .find_map(|e| match &e.body {
            eternity2_events::EventBody::Stats(s) => Some(s.nodes),
            eternity2_events::EventBody::TimedOut { final_stats, .. }
            | eternity2_events::EventBody::Exhausted { final_stats, .. }
            | eternity2_events::EventBody::Solved { final_stats, .. }
            | eternity2_events::EventBody::Cancelled { final_stats, .. } => Some(final_stats.nodes),
            _ => None,
        })
        .unwrap_or(0);
    let nps = if elapsed_ms > 0 { (nodes * 1000) / elapsed_ms } else { 0 };
    eprintln!("done: budget_ms={budget_ms}  elapsed_ms={elapsed_ms}  nodes={nodes}  nps={nps}");
}
