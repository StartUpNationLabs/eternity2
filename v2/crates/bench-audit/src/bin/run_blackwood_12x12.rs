// Vol-15 — Blackwood validation harness for the 12×12/12 testbed.
//
// Runs a single seed (per vol-15 plan: 1-seed validation before
// scaling). Compares a Blackwood-mode CP+ALNS run against a baseline
// `joe_depth150_par` CP+ALNS run on the same generated puzzle.
//
// CLI:
//   --size N        default 12
//   --colors N      default 12
//   --seed N        default 1
//   --cp-budget-ms  default 30000
//   --alns-budget-ms default 60000
//
// Output:
//   stderr — per-stage progress + final score
//   output/v15_blackwood_12x12/seed{SEED}_{TS}/{cp,alns}_{baseline,blackwood}.log

use std::path::PathBuf;
use std::sync::Arc;
use std::time::Instant;

use eternity2_bench_audit::ProgressSink;
use eternity2_core::{Board, Puzzle};
use eternity2_generator::{generate, GeneratorConfig};
use eternity2_localsearch::{
    run_alns, Acceptance, AlnsConfig, ConflictDriven, DestroyOp, MwpmDefectPair,
    RandomRegion, RepairKind, WorstWindow,
};
use eternity2_solver_engine::{
    blackwood_schedule_469, BlackwoodSchedule, EngineSolver,
};
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

fn score_board(puzzle: &Puzzle, board: &Board) -> (u32, u32) {
    let (w, h) = (puzzle.width, puzzle.height);
    let total = (w - 1) * h + w * (h - 1);
    let mut matched = 0u32;
    for y in 0..h {
        for x in 0..w {
            let pos = y * w + x;
            let Some((pid, rot)) = board.get(pos) else { continue; };
            let p = puzzle.piece(pid).unwrap();
            let e = p.edges.rotated(rot).as_array();
            if x + 1 < w {
                if let Some((npid, nrot)) = board.get(pos + 1) {
                    let np = puzzle.piece(npid).unwrap();
                    if e[1] == np.edges.rotated(nrot).as_array()[3] { matched += 1; }
                }
            }
            if y + 1 < h {
                if let Some((npid, nrot)) = board.get(pos + w) {
                    let np = puzzle.piece(npid).unwrap();
                    if e[2] == np.edges.rotated(nrot).as_array()[0] { matched += 1; }
                }
            }
        }
    }
    (matched, total)
}

fn placed_count(b: &Board, puzzle: &Puzzle) -> u32 {
    (0..puzzle.cell_count()).filter(|&p| b.get(p).is_some()).count() as u32
}

struct StageScore {
    elapsed_s: f64,
    placed: u32,
    matched: u32,
    total: u32,
    depth: u32,
    nodes: u64,
}

fn run_cp(
    label: &str,
    mut solver: Box<EngineSolver>,
    puzzle: &Puzzle,
    seed: u64,
    cp_budget_ms: u64,
    log_path: &std::path::Path,
) -> (Board, StageScore) {
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = cp_budget_ms;
    opts.seed = seed;

    let mut sink = ProgressSink::new(log_path, 5_000).expect("open cp log");
    sink.write_line(&format!(
        "=== CP ({label}) {}x{}/{} seed={seed} budget={cp_budget_ms}ms ===",
        puzzle.width, puzzle.height, puzzle.color_count - 1
    ));
    eprintln!("[{label}] CP progress log: {}", log_path.display());

    let t = Instant::now();
    let outcome = solver.solve(puzzle, &opts, &mut sink);
    let elapsed_s = t.elapsed().as_secs_f64();
    let stats = sink.final_stats.clone();

    let board: Board = match outcome {
        SolveOutcome::Solved(b) => b,
        SolveOutcome::TimedOut { best_partial, .. } => best_partial,
        SolveOutcome::Cancelled { best_partial, .. } => best_partial,
        SolveOutcome::AllSolutions(bs) => bs.into_iter().next().unwrap_or_else(|| Board::empty(puzzle)),
        SolveOutcome::Exhausted | SolveOutcome::Error(_) => Board::empty(puzzle),
    };
    let (m, t_total) = score_board(puzzle, &board);
    let p = placed_count(&board, puzzle);
    let depth = stats.as_ref().map(|s| s.max_depth_seen).unwrap_or(sink.best_depth);
    let nodes = stats.as_ref().map(|s| s.nodes).unwrap_or(0);

    eprintln!(
        "[{label}] CP: elapsed={elapsed_s:.1}s  depth={depth}  placed={p}/{}  matched={m}/{t_total}  nodes={nodes}",
        puzzle.cell_count()
    );

    (board, StageScore { elapsed_s, placed: p, matched: m, total: t_total, depth, nodes })
}

fn run_alns_stage(
    label: &str,
    puzzle: &Puzzle,
    cp_board: &Board,
    alns_budget_ms: u64,
    seed: u64,
) -> StageScore {
    let mut ops: Vec<Box<dyn DestroyOp>> = vec![
        Box::new(RandomRegion { k: 4 }),
        Box::new(WorstWindow { k: 5 }),
        Box::new(ConflictDriven { max_size: 30 }),
        Box::new(MwpmDefectPair { max_pairs: 12 }),
    ];
    let cfg = AlnsConfig {
        time_budget_ms: alns_budget_ms,
        repair_budget_ms: 500,
        acceptance: Acceptance::SimulatedAnnealing { t: 1.0 },
        segment_iters: 50,
        seed,
        verbose: false,
        repair: RepairKind::Sa,
        cp_fallback_to_sa: true,
        pinned_positions: Vec::new(),
    };
    let t = Instant::now();
    let (board, stats) = run_alns(puzzle, cp_board, ops.as_mut_slice(), &cfg);
    let elapsed_s = t.elapsed().as_secs_f64();
    let (m, total) = score_board(puzzle, &board);
    let p = placed_count(&board, puzzle);
    eprintln!(
        "[{label}] ALNS: elapsed={elapsed_s:.1}s  iters={}  matched={m}/{total}  placed={p}/{}",
        stats.iters, puzzle.cell_count()
    );
    StageScore { elapsed_s, placed: p, matched: m, total, depth: 0, nodes: stats.iters as u64 }
}

fn main() {
    let mut size: u32 = 12;
    let mut colors: u32 = 12;
    let mut seed: u64 = 1;
    let mut cp_budget: u64 = 30_000;
    let mut alns_budget: u64 = 60_000;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--size" => size = args.next().unwrap().parse().unwrap(),
            "--colors" => colors = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            "--cp-budget-ms" => cp_budget = args.next().unwrap().parse().unwrap(),
            "--alns-budget-ms" => alns_budget = args.next().unwrap().parse().unwrap(),
            _ => eprintln!("(unrecognized: {a})"),
        }
    }

    let cfg = GeneratorConfig { size, interior_colors: colors, seed };
    let puzzle = generate(cfg).expect("generate");
    eprintln!(
        "Generated {}x{}, {} colors, seed={}",
        puzzle.width, puzzle.height, puzzle.color_count - 1, seed
    );
    let internal_total = (puzzle.width - 1) * puzzle.height + puzzle.width * (puzzle.height - 1);

    // Output directory.
    let ts = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let out_dir = PathBuf::from(format!("output/v15_blackwood_12x12/seed{seed}_{ts}"));
    let _ = std::fs::create_dir_all(&out_dir);
    eprintln!("Output dir: {}", out_dir.display());

    let no_hints = eternity2_core::Hints::default();

    // Build Blackwood schedule from the generated puzzle's piece set.
    let schedule: BlackwoodSchedule = match blackwood_schedule_469(&puzzle, &no_hints) {
        Some(s) => s,
        None => {
            eprintln!("WARNING: compute_heuristic_sides returned < 3 colors; running baseline only");
            BlackwoodSchedule {
                heuristic_sides: Vec::new(),
                exhaustion_targets: vec![(0, 0)],
                heuristic_pool_size: 0,
                max_heuristic_index: 0,
                break_indexes_allowed: Vec::new(),
            }
        }
    };
    eprintln!(
        "Blackwood schedule: heuristic_sides={:?}  pool_size={}  max_idx={}  breaks={}",
        schedule.heuristic_sides,
        schedule.heuristic_pool_size,
        schedule.max_heuristic_index,
        schedule.break_indexes_allowed.len()
    );
    let schedule_arc = Arc::new(schedule);

    // === Arm 1: baseline (joe_depth150_par) ===
    let baseline_solver = Box::new(EngineSolver::joe_depth150_par());
    let (baseline_cp_board, baseline_cp) = run_cp(
        "baseline",
        baseline_solver,
        &puzzle,
        seed,
        cp_budget,
        &out_dir.join("baseline_cp.log"),
    );
    let baseline_alns = if alns_budget > 0 && baseline_cp.matched < internal_total {
        Some(run_alns_stage("baseline", &puzzle, &baseline_cp_board, alns_budget, seed))
    } else {
        None
    };

    // === Arm 2: Blackwood ===
    let bw_solver = Box::new(EngineSolver::blackwood_base_par(schedule_arc.clone()));
    let (bw_cp_board, bw_cp) = run_cp(
        "blackwood",
        bw_solver,
        &puzzle,
        seed,
        cp_budget,
        &out_dir.join("blackwood_cp.log"),
    );
    let bw_alns = if alns_budget > 0 && bw_cp.matched < internal_total {
        Some(run_alns_stage("blackwood", &puzzle, &bw_cp_board, alns_budget, seed))
    } else {
        None
    };

    // Summary.
    eprintln!();
    eprintln!("=== SUMMARY (size={size} colors={colors} seed={seed}) ===");
    eprintln!("  baseline   CP   matched={}/{}  placed={}/{}  depth={}",
        baseline_cp.matched, baseline_cp.total, baseline_cp.placed, puzzle.cell_count(), baseline_cp.depth);
    if let Some(a) = &baseline_alns {
        eprintln!("  baseline   ALNS matched={}/{}  placed={}/{}",
            a.matched, a.total, a.placed, puzzle.cell_count());
    }
    eprintln!("  blackwood  CP   matched={}/{}  placed={}/{}  depth={}",
        bw_cp.matched, bw_cp.total, bw_cp.placed, puzzle.cell_count(), bw_cp.depth);
    if let Some(a) = &bw_alns {
        eprintln!("  blackwood  ALNS matched={}/{}  placed={}/{}",
            a.matched, a.total, a.placed, puzzle.cell_count());
    }

    // Determine arm scores for delta reporting.
    let base_final = baseline_alns.as_ref().map(|a| a.matched).unwrap_or(baseline_cp.matched);
    let bw_final = bw_alns.as_ref().map(|a| a.matched).unwrap_or(bw_cp.matched);
    eprintln!();
    eprintln!("  baseline final = {base_final}/{internal_total}");
    eprintln!("  blackwood final = {bw_final}/{internal_total}");
    eprintln!("  Δ (blackwood − baseline) = {:+}", bw_final as i32 - base_final as i32);
}
