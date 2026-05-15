// Smoke test the lifted LP on a small generated puzzle.
//
// 1. Generate small puzzle (e.g. 8×8 / 6 colors).
// 2. Solve to optimum.
// 3. Strip interior, run lifted LP on the border-only board.
// 4. Compare lifted UB vs standard LP UB.

#![forbid(unsafe_code)]

use std::time::Instant;

use eternity2_bench_audit::border_ub::{lp_ub_with, strip_interior_except_hints, LpOptions};
use eternity2_bench_audit::border_ub_lifted::lifted_lp_ub_with;
use eternity2_events::{EventSink, SolverEvent};
use eternity2_export::score_board;
use eternity2_generator::{generate, GeneratorConfig};
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

struct NullSink;
impl EventSink for NullSink { fn emit(&mut self, _e: SolverEvent) {} }

fn main() {
    let mut size: u32 = 6;
    let mut colors: u32 = 4;
    let mut seed: u64 = 1;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--size" => size = args.next().unwrap().parse().unwrap(),
            "--colors" => colors = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            _ => {}
        }
    }
    eprintln!("Generating {size}x{size}/{colors} colors, seed {seed}");
    let cfg = GeneratorConfig { size, interior_colors: colors, seed };
    let puzzle = generate(cfg).expect("generate");
    eprintln!("Puzzle: {}x{}, color_count={}", puzzle.width, puzzle.height, puzzle.color_count);

    // Solve to find a max-score board.
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = 30_000;
    opts.seed = seed;
    let mut solver = EngineSolver::border_first_lcv();
    let outcome = solver.solve(&puzzle, &opts, &mut NullSink);
    let solved = match outcome {
        SolveOutcome::Solved(b) => b,
        SolveOutcome::TimedOut { best_partial, .. } => best_partial,
        SolveOutcome::AllSolutions(mut v) => v.pop().expect("empty"),
        other => { eprintln!("solver: {other:?}"); std::process::exit(1); }
    };
    let (m, t) = score_board(&puzzle, &solved);
    eprintln!("Solved board: matched={m}/{t}");

    // Strip interior except hints (no hints in generated puzzles, but the helper handles it).
    let border = strip_interior_except_hints(&puzzle, &solved, &[]);

    let lp_opts = LpOptions {
        verbose: false,
        threads: 4,
        time_limit_secs: 60.0,
        use_ipm: true,
        presolve: true,
        integer: false,
        force_bi_match: Vec::new(),
    };

    eprintln!("Standard LP UB...");
    let t0 = Instant::now();
    let std_r = lp_ub_with(&puzzle, &border, lp_opts.clone()).expect("std LP");
    eprintln!("  std UB = {:.4} (bi={:.4} ii={:.4}) time={:.1}s",
              std_r.total_ub, std_r.bi_ub, std_r.interior_ub, t0.elapsed().as_secs_f64());

    eprintln!("Lifted LP UB...");
    let t0 = Instant::now();
    let lift_r = lifted_lp_ub_with(&puzzle, &border, lp_opts).expect("lifted LP");
    eprintln!("  lifted UB = {:.4} (bi={:.4} interior={:.4}) n_z={} avg_z/edge={:.1} time={:.1}s",
              lift_r.total_ub, lift_r.bi_ub, lift_r.interior_ub,
              lift_r.n_z, lift_r.n_z_per_edge_avg, t0.elapsed().as_secs_f64());

    eprintln!();
    eprintln!("RESULT:");
    eprintln!("  integer score:  {m} / {t}");
    eprintln!("  standard LP UB: {:.4}", std_r.total_ub);
    eprintln!("  lifted LP UB:   {:.4}", lift_r.total_ub);
    eprintln!("  lifted - integer gap: {:.4}", lift_r.total_ub - m as f64);
    eprintln!("  standard - integer gap: {:.4}", std_r.total_ub - m as f64);
    if lift_r.total_ub <= std_r.total_ub + 1e-6 {
        eprintln!("  PASS: lifted ≤ standard ✓");
    } else {
        eprintln!("  WARN: lifted > standard, formulation may have bug");
    }
}
