// Validate the LP UB formulation on a small generated puzzle.
//
// 1. Generate an 8x8 puzzle.
// 2. Solve it (border_first_lcv usually finds optimal in seconds).
// 3. Extract its border.
// 4. Run lp_ub on the border.
// 5. Assert UB ≥ score(solved_board); report LP slack.

#![forbid(unsafe_code)]

use std::time::Instant;

use eternity2_bench_audit::border_ub::{lp_ub, strip_interior_except_hints};
use eternity2_events::{EventSink, SolverEvent};
use eternity2_export::score_board;
use eternity2_generator::{generate, GeneratorConfig};
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

struct NullSink;
impl EventSink for NullSink {
    fn emit(&mut self, _event: SolverEvent) {}
}

fn main() {
    let mut size: u32 = 8;
    let mut colors: u32 = 6;
    let mut seed: u64 = 1;
    let mut budget_ms: u64 = 30_000;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--size" => size = args.next().unwrap().parse().unwrap(),
            "--colors" => colors = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            "--solve-budget-ms" => budget_ms = args.next().unwrap().parse().unwrap(),
            _ => eprintln!("(unrecognized: {a})"),
        }
    }

    eprintln!("Generating puzzle: {size}x{size}, {colors} interior colors, seed={seed}");
    let cfg = GeneratorConfig { size, interior_colors: colors, seed };
    let puzzle = generate(cfg).expect("generate");
    eprintln!("Puzzle: {}x{}, color_count={}", puzzle.width, puzzle.height, puzzle.color_count);

    let mut opts = SolveOpts::default();
    opts.time_budget_ms = budget_ms;
    opts.seed = seed;

    let mut solver = EngineSolver::border_first_lcv();
    let mut sink = NullSink;
    eprintln!("Solving with border_first_lcv (budget {budget_ms}ms)...");
    let t0 = Instant::now();
    let outcome = solver.solve(&puzzle, &opts, &mut sink);
    eprintln!("solve elapsed: {:.2}s", t0.elapsed().as_secs_f64());

    let solved_board = match outcome {
        SolveOutcome::Solved(b) => b,
        SolveOutcome::AllSolutions(bs) => bs.into_iter().next().expect("empty"),
        SolveOutcome::TimedOut { best_partial, .. } => {
            eprintln!("WARN: timed out — using best partial");
            best_partial
        }
        other => {
            eprintln!("ERROR: solver did not find a solution: {other:?}");
            std::process::exit(1);
        }
    };
    let (matched, total) = score_board(&puzzle, &solved_board);
    eprintln!("Solved board: matched={matched}/{total}");

    let border_board = strip_interior_except_hints(&puzzle, &solved_board, &[]);
    let placed = (0..puzzle.cell_count()).filter(|&p| border_board.get(p).is_some()).count();
    eprintln!("Border-only placed cells: {placed}");

    eprintln!("Running LP UB...");
    let t0 = Instant::now();
    match lp_ub(&puzzle, &border_board) {
        Ok(r) => {
            eprintln!("LP solve: {:.3}s", r.solve_secs);
            eprintln!("  bb_matches  = {}", r.bb_matches);
            eprintln!("  bi_matches  = {}", r.bi_matches);
            eprintln!("  lp_interior = {:.4}", r.interior_ub);
            eprintln!("  total_ub    = {:.4}", r.total_ub);
            eprintln!("  n_x = {}, n_y = {}, n_constraints = {}", r.n_x, r.n_y, r.n_constraints);
            eprintln!("  total elapsed: {:.2}s", t0.elapsed().as_secs_f64());

            let solved_score = matched as f64;
            let max_score = total as f64;
            eprintln!();
            eprintln!("Validation:");
            eprintln!("  solved_score = {solved_score}");
            eprintln!("  total_ub     = {:.4}", r.total_ub);
            eprintln!("  max_score    = {max_score}");
            if r.total_ub + 1e-6 < solved_score {
                eprintln!("FAIL: UB ({:.4}) < solved score ({solved_score})!", r.total_ub);
                std::process::exit(1);
            }
            if r.total_ub > max_score + 1e-6 {
                eprintln!("WARN: UB ({:.4}) > max_score ({max_score})", r.total_ub);
            }
            let slack = r.total_ub - solved_score;
            eprintln!("PASS: UB - solved_score = {slack:.4} (LP slack on this border)");
        }
        Err(e) => {
            eprintln!("LP UB failed: {e}");
            std::process::exit(1);
        }
    }
}
