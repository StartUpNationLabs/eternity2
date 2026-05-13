// Vol-23 user-proposed X-skeleton pipeline.
//
// Stage 1: joe_depth150_bp_x_par CP for --cp-ms (default 300_000 = 5 min).
//          Uses PathSkeleton::XSkeleton (two 3-cell-wide diagonals through
//          the 5 canonical hints, then Chebyshev-outward fill from centre).
// Stage 2: ALNS-fill for --alns-ms (default 600_000 = 10 min) with the
//          same 11-operator portfolio + SA(t=1.0) repair as
//          run_e2_blackwood_then_csp.rs.
//
// Pins canonical 5 hints only — no Blackwood seed.
//
// CLI:
//   --cp-ms    CP budget in ms (default 300_000)
//   --alns-ms  ALNS budget in ms (default 600_000)
//   --seed     (default 1)

#![forbid(unsafe_code)]

use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit::{placed_count, score_board_dense as score_board, ProgressSink};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::bucas_url;
use eternity2_core::{Board, Puzzle};
use eternity2_localsearch::{
    piece_swap_hillclimb, polish_rotations, run_alns, Acceptance, AlnsConfig,
    ComponentDestroy, ComponentPlusHaloDestroy, ConflictDriven, DestroyOp, HingeDestroy,
    MwpmDefectPair, RandomRegion, RepairKind, WorstBand, WorstRow, WorstWindow,
};
use eternity2_solver_engine::{load_edge_bp_marginals, EngineSolver};
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

fn solve_to_board(
    label: &str,
    solver: &mut Box<EngineSolver>,
    puzzle: &Puzzle,
    opts: &SolveOpts,
    log_path: &std::path::Path,
) -> (Board, u32, u32, u32, u64) {
    let mut sink = ProgressSink::new(log_path, 5_000).expect("open log");
    sink.write_line(&format!("=== {label} ==="));
    eprintln!("[{label}] progress log: {}", log_path.display());
    let t = Instant::now();
    let outcome = solver.solve(puzzle, opts, &mut sink);
    let elapsed = t.elapsed();
    let stats = sink.final_stats.clone();
    let board: Board = match outcome {
        SolveOutcome::Solved(b)
        | SolveOutcome::TimedOut { best_partial: b, .. }
        | SolveOutcome::Cancelled { best_partial: b, .. } => b,
        SolveOutcome::AllSolutions(bs) => bs.into_iter().next().unwrap_or_else(|| Board::empty(puzzle)),
        _ => Board::empty(puzzle),
    };
    let (m, _t) = score_board(puzzle, &board);
    let p = placed_count(&board, puzzle);
    let depth = stats.as_ref().map(|s| s.max_depth_seen).unwrap_or(sink.best_depth);
    let nodes = stats.as_ref().map(|s| s.nodes).unwrap_or(0);
    eprintln!(
        "[{label}] {:.1}s  depth={depth}  placed={p}/256  matched={m}/480  nodes={nodes}",
        elapsed.as_secs_f64()
    );
    (board, m, p, depth, nodes)
}

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let bp_path = PathBuf::from("output/v12_bp/edge_bp_60i.json");

    let mut cp_ms: u64 = 300_000;
    let mut alns_ms: u64 = 600_000;
    let mut seed: u64 = 1;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--cp-ms" => cp_ms = args.next().unwrap().parse().unwrap(),
            "--alns-ms" => alns_ms = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }

    let run_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let out_dir = PathBuf::from(format!("output/vol-23-x_skeleton/run_{run_id}"));
    std::fs::create_dir_all(&out_dir).expect("mkdir");

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    eprintln!("loaded canonical E2 with {} hints", hints.hints.len());

    let edge_bp = load_edge_bp_marginals(&bp_path).ok();
    if edge_bp.is_none() {
        eprintln!("[warn] edge BP marginals not found at {} — running without", bp_path.display());
    }

    // ---------- Stage 1: joe_depth150_bp_x_par CP ----------
    let mut cp_opts = SolveOpts::default();
    cp_opts.time_budget_ms = cp_ms;
    cp_opts.seed = seed;
    cp_opts.hints = hints.clone();
    if let Some(bp) = edge_bp.clone() { cp_opts.edge_bp_marginals = Some(bp); }

    let mut cp_solver = Box::new(EngineSolver::joe_depth150_bp_x_par());
    let (cp_board, cp_m, cp_p, cp_d, _cp_n) = solve_to_board(
        "stage1_x_skeleton_cp",
        &mut cp_solver,
        &puzzle,
        &cp_opts,
        &out_dir.join("stage1_cp.log"),
    );
    let cp_url = bucas_url(&puzzle, &cp_board, "v23_stage1_x_skeleton");
    eprintln!("[stage1] bucas: {cp_url}");
    let _ = std::fs::write(
        out_dir.join("stage1_cp_board.json"),
        serde_json::to_string_pretty(&serde_json::json!({
            "placement": (0..puzzle.cell_count()).map(|p| {
                cp_board.get(p).map(|(pid, rot)| serde_json::json!({
                    "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
                }))
            }).collect::<Vec<_>>(),
            "bucas_url": &cp_url,
        })).unwrap(),
    );

    // ---------- Stage 2: ALNS ----------
    let mut ops: Vec<Box<dyn DestroyOp>> = vec![
        Box::new(RandomRegion { k: 4 }),
        Box::new(WorstWindow { k: 5 }),
        Box::new(ConflictDriven { max_size: 30 }),
        Box::new(ConflictDriven { max_size: 80 }),
        Box::new(MwpmDefectPair { max_pairs: 12 }),
        Box::new(WorstBand { k_rows: 4 }),
        Box::new(WorstBand { k_rows: 6 }),
        Box::new(ComponentDestroy { max_size: 100, min_size: 6 }),
        Box::new(ComponentPlusHaloDestroy { max_size: 100, min_size: 6 }),
        Box::new(WorstRow),
        Box::new(HingeDestroy { halo: 1 }),
    ];
    let pinned_positions: Vec<u32> = hints.hints.iter().map(|h| h.position).collect();
    let cfg = AlnsConfig {
        time_budget_ms: alns_ms,
        repair_budget_ms: 1500,
        acceptance: Acceptance::SimulatedAnnealing { t: 1.0 },
        segment_iters: 50,
        seed,
        verbose: false,
        repair: RepairKind::Sa,
        cp_fallback_to_sa: true,
        pinned_positions: pinned_positions.clone(),
        iter_budget: 0,
        lex_break_isoscore: false,
        checkpoint_path: None,
        checkpoint_every_ms: 60_000,
        repair_step_budget: 0,
        cp_repair_parallel: true,
    };
    eprintln!("[stage2] ALNS pinning {} canonical positions, budget={}s",
              pinned_positions.len(), alns_ms / 1000);
    let t_alns = Instant::now();
    let (alns_board, alns_stats) = run_alns(&puzzle, &cp_board, ops.as_mut_slice(), &cfg);
    let alns_elapsed = t_alns.elapsed();
    let pinned_set: std::collections::BTreeSet<u32> =
        pinned_positions.iter().copied().collect();
    let (alns_board, polish_gain) = polish_rotations(&puzzle, &alns_board, &pinned_set);
    if polish_gain > 0 {
        eprintln!("[stage2] polish-rot: +{polish_gain} matches");
    }
    let (alns_board, swap_gain) = piece_swap_hillclimb(&puzzle, &alns_board, &pinned_set);
    if swap_gain > 0 {
        eprintln!("[stage2] polish-swap: +{swap_gain} matches");
    }
    let (am, _at) = score_board(&puzzle, &alns_board);
    let ap = placed_count(&alns_board, &puzzle);
    let alns_url = bucas_url(&puzzle, &alns_board, "v23_stage2_alns");
    eprintln!(
        "[stage2] ALNS: {:.1}s  iters={}  placed={ap}/256  matched={am}/480  Δ_vs_cp={:+}",
        alns_elapsed.as_secs_f64(),
        alns_stats.iters,
        am as i32 - cp_m as i32
    );
    eprintln!("[stage2] bucas: {alns_url}");
    let _ = std::fs::write(
        out_dir.join("stage2_alns_board.json"),
        serde_json::to_string_pretty(&serde_json::json!({
            "placement": (0..puzzle.cell_count()).map(|p| {
                alns_board.get(p).map(|(pid, rot)| serde_json::json!({
                    "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
                }))
            }).collect::<Vec<_>>(),
            "bucas_url": &alns_url,
        })).unwrap(),
    );

    // ---------- Summary ----------
    eprintln!();
    eprintln!("=== vol-23 X-skeleton pipeline summary (seed={seed}) ===");
    eprintln!("  stage1 cp:   matched={cp_m}/480  placed={cp_p}/256  depth={cp_d}");
    eprintln!("  stage2 alns: matched={am}/480  placed={ap}/256  Δ_vs_cp={:+}",
              am as i32 - cp_m as i32);

    let summary = serde_json::json!({
        "puzzle": "canonical_5_clue_16x16",
        "seed": seed,
        "cp_ms": cp_ms,
        "alns_ms": alns_ms,
        "stage1_cp": { "matched": cp_m, "placed": cp_p, "depth": cp_d, "bucas": cp_url },
        "stage2_alns": { "matched": am, "placed": ap, "bucas": alns_url, "iters": alns_stats.iters },
    });
    let _ = std::fs::write(out_dir.join("summary.json"), serde_json::to_string_pretty(&summary).unwrap());
    eprintln!("\nlogs + boards: {}", out_dir.display());
}
