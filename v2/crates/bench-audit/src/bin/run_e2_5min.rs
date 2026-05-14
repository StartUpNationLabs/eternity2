// Vol-12 closeout — raw run on canonical Eternity II with the best v12
// combination: joe_depth150_par. 5-minute time budget.
//
// Vol-33 T5 — migrated to the shared bench_audit::harness {outcome_to_view,
// write_summary, build_postmortem_json} helpers.

use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit::harness::{build_postmortem_json, outcome_to_view, write_summary};
use eternity2_bench_audit::ProgressSink;
use eternity2_puzzle_io::load_puzzle_with_hints;
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, Solver};

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let log_path = PathBuf::from("output/v12_run/run_e2_5min.log");
    let board_path = PathBuf::from("output/v12_run/run_e2_5min_board.json");
    std::fs::create_dir_all("output/v12_run").expect("mkdir");

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");

    let mut sink = ProgressSink::new(&log_path, 5_000).expect("open log");
    let header = format!(
        "=== vol-12 raw run on canonical Eternity II ===\n\
         puzzle: {}\n\
         size: {}x{} colors={} hints={}\n\
         profile: joe_depth150_par (gacolor + AC-3 + NS-1 + depth-150 gate + multi-core)\n\
         budget: 300_000 ms (5 min)\n",
        puzzle_path.display(),
        puzzle.width,
        puzzle.height,
        puzzle.color_count - 1,
        hints.hints.len()
    );
    sink.write_line(&header);
    eprintln!("{header}");

    let mut solver = EngineSolver::joe_depth150_par();
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = 300_000;
    opts.seed = 1;
    opts.hints = hints;

    let t0 = Instant::now();
    let outcome = solver.solve(&puzzle, &opts, &mut sink);
    let elapsed = t0.elapsed();

    let final_stats = sink.final_stats.clone();
    let view = outcome_to_view(outcome);

    let mut summary = String::new();
    write_summary(
        &mut summary,
        &puzzle,
        &view.verdict,
        elapsed.as_secs_f64(),
        final_stats.as_ref(),
        view.board.as_ref(),
        "vol12_5min",
    );

    if view.board.is_some() {
        let json = build_postmortem_json(
            &puzzle,
            &view.verdict,
            elapsed.as_secs_f64(),
            final_stats.as_ref(),
            view.board.as_ref(),
            "vol12_5min",
        );
        std::fs::write(&board_path, serde_json::to_string_pretty(&json).unwrap())
            .expect("write json");
    }

    sink.write_line(&summary);
    eprintln!("{summary}");
    eprintln!("log:   {}", log_path.display());
    eprintln!("board: {}", board_path.display());
}
