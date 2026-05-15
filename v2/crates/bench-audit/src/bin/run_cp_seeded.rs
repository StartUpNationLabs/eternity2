// Run canonical-E2 CP search with a specified seed and profile,
// save the best partial board found.

#![forbid(unsafe_code)]

use std::path::PathBuf;
use std::time::Instant;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_events::{EventSink, SolverEvent};
use eternity2_export::score_board;
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

struct NullSink;
impl EventSink for NullSink { fn emit(&mut self, _e: SolverEvent) {} }

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut seed: u64 = 1;
    let mut budget_ms: u64 = 300_000;
    let mut profile = "joe_depth150_par".to_string();
    let mut out_path = String::new();
    let mut iter = args.iter();
    while let Some(a) = iter.next() {
        match a.as_str() {
            "--seed" => seed = iter.next().unwrap().parse().unwrap(),
            "--budget-ms" => budget_ms = iter.next().unwrap().parse().unwrap(),
            "--profile" => profile = iter.next().unwrap().clone(),
            "--out" => out_path = iter.next().unwrap().clone(),
            other => eprintln!("unrecognized: {other}"),
        }
    }
    if out_path.is_empty() {
        eprintln!("usage: run_cp_seeded --seed N --budget-ms MS --profile P --out PATH");
        std::process::exit(2);
    }

    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");

    let mut solver = match profile.as_str() {
        "joe_depth150_par" => EngineSolver::joe_depth150_par(),
        "joe_depth150_bp_par" => EngineSolver::joe_depth150_bp_par(),
        "gacolor_ac3_par" => EngineSolver::gacolor_ac3_par(),
        "border_first_lcv" => EngineSolver::border_first_lcv(),
        "border_first_full" => EngineSolver::border_first_full(),
        other => panic!("unknown profile {other}"),
    };
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = budget_ms;
    opts.seed = seed;
    opts.hints = hints;

    eprintln!("CP {profile} seed={seed} budget={budget_ms}ms");
    let t0 = Instant::now();
    let outcome = solver.solve(&puzzle, &opts, &mut NullSink);
    let dt = t0.elapsed().as_secs_f64();

    let board = match outcome {
        SolveOutcome::Solved(b) => b,
        SolveOutcome::AllSolutions(mut v) => v.pop().expect("empty"),
        SolveOutcome::TimedOut { best_partial, best_depth: _ } => best_partial,
        SolveOutcome::Cancelled { best_partial, .. } => best_partial,
        SolveOutcome::Exhausted => panic!("exhausted"),
        SolveOutcome::Error(e) => panic!("error: {e}"),
    };

    let (m, t) = score_board(&puzzle, &board);
    let placed = (0..puzzle.cell_count()).filter(|&p| board.get(p).is_some()).count();
    eprintln!("done seed={seed} elapsed={dt:.2}s matched={m}/{t} placed={placed}");

    let placement: Vec<_> = (0..puzzle.cell_count()).filter_map(|p| {
        board.get(p).map(|(pid, rot)| serde_json::json!({ "pos": p, "piece_id": pid, "rotation": rot.as_u8() }))
    }).collect();
    let out = serde_json::json!({ "matched": m, "total": t, "placement": placement, "seed": seed, "profile": profile });
    std::fs::write(&out_path, serde_json::to_string_pretty(&out).unwrap()).expect("write");
    eprintln!("saved: {out_path}");
}
