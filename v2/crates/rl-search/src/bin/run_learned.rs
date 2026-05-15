// Run canonical-E2 CP with ValueOrder::Learned using the model
// pointed to by E2_LEARNED_MODEL env var.
//
// Outputs: final outcome (depth, score, elapsed). One JSON line.

#![forbid(unsafe_code)]

use std::path::PathBuf;
use std::time::Instant;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_events::{EventSink, SolverEvent};
use eternity2_export::score_board;
use eternity2_solver_engine::{EngineSolver, ValueOrder};
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

struct NullSink;
impl EventSink for NullSink { fn emit(&mut self, _e: SolverEvent) {} }

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut seed: u64 = 1;
    let mut budget_ms: u64 = 60_000;
    let mut profile = "joe_depth150_par".to_string();
    let mut iter = args.iter();
    while let Some(a) = iter.next() {
        match a.as_str() {
            "--seed" => seed = iter.next().unwrap().parse().unwrap(),
            "--budget-ms" => budget_ms = iter.next().unwrap().parse().unwrap(),
            "--profile" => profile = iter.next().unwrap().clone(),
            _ => {}
        }
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");

    let mut solver = match profile.as_str() {
        "joe_depth150_par" => EngineSolver::joe_depth150_par(),
        "joe_depth150_bp_par" => EngineSolver::joe_depth150_bp_par(),
        other => panic!("unknown profile: {other}"),
    };
    // Override to ValueOrder::Learned
    solver = solver.with_value_order(ValueOrder::Learned);

    let mut opts = SolveOpts::default();
    opts.time_budget_ms = budget_ms;
    opts.seed = seed;
    opts.hints = hints;

    let model_path = std::env::var("E2_LEARNED_MODEL")
        .unwrap_or_else(|_| "ml/runs/v1/model.onnx".to_string());
    eprintln!("Running canonical-E2 CP with ValueOrder::Learned");
    eprintln!("Model: {model_path}");
    eprintln!("Profile: {profile} (+ Learned override)  seed: {seed}  budget: {budget_ms}ms");

    let t0 = Instant::now();
    let outcome = solver.solve(&puzzle, &opts, &mut NullSink);
    let elapsed = t0.elapsed().as_secs_f64();

    let (best_board, status) = match outcome {
        SolveOutcome::Solved(b) => (b, "Solved"),
        SolveOutcome::AllSolutions(mut v) => (v.pop().expect("empty"), "Solved"),
        SolveOutcome::TimedOut { best_partial, .. } => (best_partial, "TimedOut"),
        SolveOutcome::Cancelled { best_partial, .. } => (best_partial, "Cancelled"),
        SolveOutcome::Exhausted => {
            let r = serde_json::json!({
                "status": "Exhausted",
                "elapsed_secs": elapsed,
                "matched": 0,
                "placed": 0,
                "seed": seed,
                "profile": profile,
                "model": model_path,
            });
            println!("{r}");
            return;
        }
        SolveOutcome::Error(e) => panic!("engine error: {e}"),
    };
    let (m, t) = score_board(&puzzle, &best_board);
    let placed = (0..puzzle.cell_count()).filter(|&p| best_board.get(p).is_some()).count();

    let r = serde_json::json!({
        "status": status,
        "elapsed_secs": elapsed,
        "matched": m,
        "total": t,
        "placed": placed,
        "seed": seed,
        "profile": profile,
        "model": model_path,
    });
    println!("{r}");
}
