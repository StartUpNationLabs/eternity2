// Vol-16 Cat-4e — single-threaded profiling target for joe_depth150_bp_par
// equivalent (the baseline 439/480 canonical-E2 profile). Allows us to
// see what's hot in non-RAW profiles: gacolor_check + class_balance_check
// + multiset_equality_check + AC-3 all run at every node.

use std::path::PathBuf;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_solver_engine::{load_edge_bp_marginals, EngineSolver};
use eternity2_solver_trait::{SolveOpts, Solver};

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");

    let mut solver = EngineSolver::joe_depth150_bp();

    let budget_ms: u64 = std::env::var("E2_PROFILE_MS")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(15_000);
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = budget_ms;
    opts.seed = 1;
    opts.hints = hints;

    // Best-effort BP load — falls back silently if not present.
    let bp_path = PathBuf::from("output/v12_bp/edge_bp_60i.json");
    if bp_path.exists() {
        if let Ok(bp) = load_edge_bp_marginals(&bp_path) {
            opts.edge_bp_marginals = Some(bp);
        }
    }

    let mut sink = eternity2_events::BufferSink::default();
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
