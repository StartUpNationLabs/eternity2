// Vol-14 — full CP + ALNS pipeline on a GENERATED puzzle.
//
// Workflow (mirrors what we do on canonical E2):
//   1. Generate puzzle (size, colors, seed) via eternity2_generator.
//   2. Run CP (border_first_lcv single-thread) for cp_budget_ms.
//   3. Take the partial board → run ALNS for alns_budget_ms.
//   4. Report final matched/total.
//
// 8-seed portfolio version: pass --portfolio to run 8 different
// generation seeds (and 8 different CP seeds) in series, one core
// each via OS parallelism (caller's responsibility — this bin
// itself does single-thread for both CP and ALNS to be
// portfolio-friendly).
//
// CLI:
//   --size, --colors, --seed              puzzle generation
//   --cp-budget-ms, --alns-budget-ms      per-stage budgets
//   --cp-seed, --alns-seed                seeds (default both = puzzle seed)

use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit::{placed_count, score_board_dense as score_board, ProgressSink};
use eternity2_core::Board;
use eternity2_generator::{generate, GeneratorConfig};
use eternity2_localsearch::{
    run_alns, Acceptance, AlnsConfig, ConflictDriven, DestroyOp, MwpmDefectPair,
    RandomRegion, RepairKind, WorstWindow,
};
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};


fn main() {
    let mut size: u32 = 12;
    let mut colors: u32 = 12;
    let mut seed: u64 = 1;
    let mut cp_budget: u64 = 30_000;
    let mut alns_budget: u64 = 60_000;
    let mut cp_profile = "border_first_lcv".to_string();
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--size" => size = args.next().unwrap().parse().unwrap(),
            "--colors" => colors = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            "--cp-budget-ms" => cp_budget = args.next().unwrap().parse().unwrap(),
            "--alns-budget-ms" => alns_budget = args.next().unwrap().parse().unwrap(),
            "--cp-profile" => cp_profile = args.next().unwrap(),
            _ => eprintln!("(unrecognized: {a})"),
        }
    }

    let cfg = GeneratorConfig { size, interior_colors: colors, seed };
    let puzzle = generate(cfg).expect("generate");
    eprintln!("Generated {}x{}, {} colors, seed={}",
        puzzle.width, puzzle.height, puzzle.color_count - 1, seed);
    let internal_total = (puzzle.width - 1) * puzzle.height + puzzle.width * (puzzle.height - 1);

    // === Stage 1: CP ===
    let mut solver = match cp_profile.as_str() {
        "border_first_lcv"    => EngineSolver::border_first_lcv(),
        "gacolor_ac3"         => EngineSolver::gacolor_ac3(),
        "gacolor_ac3_ns1"     => EngineSolver::gacolor_ac3_ns1(),
        "joe_depth150"        => EngineSolver::joe_depth150(),
        _ => panic!("unknown cp profile {cp_profile}"),
    };
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = cp_budget;
    opts.seed = seed;

    // Progress log lives next to the launcher's invocation. Use a
    // timestamp-suffixed filename so parallel invocations don't clobber.
    let log_dir = PathBuf::from("output/v14_generated_pipeline");
    let _ = std::fs::create_dir_all(&log_dir);
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let log_path = log_dir.join(format!("seed{}_cp_{}.log", seed, now));
    let mut sink = ProgressSink::new(&log_path, 5_000).expect("open cp log");
    sink.write_line(&format!("=== CP ({cp_profile}) {}x{}/{} seed={seed} budget={cp_budget}ms ===",
        puzzle.width, puzzle.height, puzzle.color_count - 1));
    eprintln!("CP progress log: {}", log_path.display());
    let t_cp = Instant::now();
    let outcome = solver.solve(&puzzle, &opts, &mut sink);
    let cp_elapsed = t_cp.elapsed();
    let stats_cp = sink.final_stats.clone();

    let cp_board: Board = match outcome {
        SolveOutcome::Solved(b) => b,
        SolveOutcome::TimedOut { best_partial, .. } => best_partial,
        SolveOutcome::Cancelled { best_partial, .. } => best_partial,
        SolveOutcome::AllSolutions(bs) => bs.into_iter().next().unwrap_or_else(|| Board::empty(&puzzle)),
        SolveOutcome::Exhausted | SolveOutcome::Error(_) => Board::empty(&puzzle),
    };
    let (cp_m, cp_t) = score_board(&puzzle, &cp_board);
    let cp_p = placed_count(&cp_board, &puzzle);
    let cp_depth = stats_cp.as_ref().map(|s| s.max_depth_seen).unwrap_or(sink.best_depth);
    let cp_nodes = stats_cp.as_ref().map(|s| s.nodes).unwrap_or(0);

    eprintln!("CP ({cp_profile}): elapsed={:.1}s  depth={cp_depth}  placed={cp_p}/{}  matched={cp_m}/{cp_t}  nodes={cp_nodes}",
        cp_elapsed.as_secs_f64(), puzzle.cell_count());

    // === Stage 2: ALNS ===
    if alns_budget > 0 && cp_m < internal_total {
        let mut ops: Vec<Box<dyn DestroyOp>> = vec![
            Box::new(RandomRegion { k: 4 }),
            Box::new(WorstWindow { k: 5 }),
            Box::new(ConflictDriven { max_size: 30 }),
            Box::new(MwpmDefectPair { max_pairs: 12 }),
        ];
        let cfg = AlnsConfig {
            time_budget_ms: alns_budget,
            repair_budget_ms: 500,
            acceptance: Acceptance::SimulatedAnnealing { t: 1.0 },
            segment_iters: 50,
            seed,
            verbose: false,
            repair: RepairKind::Sa,
            cp_fallback_to_sa: true,
            pinned_positions: Vec::new(),  // generated puzzle, no hints
            iter_budget: 0,
        };
        let t_alns = Instant::now();
        let (alns_board, alns_stats) = run_alns(&puzzle, &cp_board, ops.as_mut_slice(), &cfg);
        let alns_elapsed = t_alns.elapsed();
        let (am, at) = score_board(&puzzle, &alns_board);
        eprintln!("ALNS: elapsed={:.1}s  iters={}  matched={am}/{at}  (delta={:+})",
            alns_elapsed.as_secs_f64(), alns_stats.iters,
            am as i32 - cp_m as i32);
    }
}
