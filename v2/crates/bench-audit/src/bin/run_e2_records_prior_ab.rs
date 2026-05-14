// Vol-41 — A/B test ValueOrder::RecordsPrior vs baseline (EdgeBpMarginals).
//
// Two arms back-to-back on canonical Eternity II, same seed:
//   A) baseline: joe_depth150_bp_par + EdgeBpMarginals (vol-14 default)
//   B) records-prior: joe_depth150_bp_par + RecordsPrior (vol-41 new)
//
// Same budget. Measures max_depth, nodes, edge_matches.
// Gate: ≥5% depth lift OR ≥5% node reduction at iso-depth.
//
// CLI:
//   run_e2_records_prior_ab [--budget-ms 60000] [--seed 1]
//     [--records-json output/vol-37_revised/cell_value_order.json]
//
// Output: stdout + per-arm log under output/vol-41/records_prior_ab/

#![forbid(unsafe_code)]

use std::path::{Path, PathBuf};
use std::time::Instant;

use eternity2_bench_audit::{placed_count, score_board_dense as score_board, ProgressSink};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_solver_engine::{load_edge_bp_marginals, load_records_prior_map, EngineSolver};
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

struct ArmResult {
    label: String,
    elapsed_s: f64,
    nodes: u64,
    max_depth: u32,
    edge_matches: u32,
    pieces_placed: u32,
    board: eternity2_core::Board,
}

fn run_arm(
    label: &str,
    mut solver: EngineSolver,
    puzzle: &eternity2_core::Puzzle,
    opts: SolveOpts,
    log_path: &Path,
    budget_ms: u64,
) -> ArmResult {
    let mut sink = ProgressSink::new(log_path, 5_000).expect("open log");
    sink.write_line(&format!("=== {label}  budget={budget_ms}ms ==="));
    let t0 = Instant::now();
    let outcome = solver.solve(puzzle, &opts, &mut sink);
    let elapsed = t0.elapsed();
    let stats = sink.final_stats.clone();
    let (board, _) = match outcome {
        SolveOutcome::Solved(b) => (b, true),
        SolveOutcome::TimedOut { best_partial, .. } => (best_partial, false),
        SolveOutcome::Cancelled { best_partial, .. } => (best_partial, false),
        _ => (eternity2_core::Board::empty(puzzle), false),
    };
    let (matched, _) = score_board(puzzle, &board);
    let placed = placed_count(&board, puzzle);
    let max_depth = stats.as_ref().map(|s| s.max_depth_seen).unwrap_or(0);
    let nodes = stats.as_ref().map(|s| s.nodes).unwrap_or(0);
    ArmResult {
        label: label.to_string(),
        elapsed_s: elapsed.as_secs_f64(),
        nodes,
        max_depth,
        edge_matches: matched,
        pieces_placed: placed,
        board,
    }
}

fn save_board_sparse(path: &Path, puzzle: &eternity2_core::Puzzle, board: &eternity2_core::Board) {
    let placement: Vec<serde_json::Value> = (0..puzzle.cell_count())
        .filter_map(|p| board.get(p).map(|(pid, rot)| serde_json::json!({
            "pos": p,
            "piece_id": u32::from(pid),
            "rotation": rot.as_u8(),
        })))
        .collect();
    let json = serde_json::json!({ "placement": placement });
    std::fs::write(path, serde_json::to_string_pretty(&json).unwrap()).expect("write board");
}

fn main() {
    let mut budget_ms: u64 = 60_000;
    let mut seed: u64 = 1;
    let mut records_json = PathBuf::from("output/vol-37_revised/cell_value_order.json");
    let bp_path = PathBuf::from("output/v12_bp/edge_bp_60i.json");

    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--budget-ms" => budget_ms = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            "--records-json" => records_json = PathBuf::from(args.next().unwrap()),
            _ => panic!("unknown arg: {a}"),
        }
    }

    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    eprintln!("loaded canonical E2 with {} hints", hints.hints.len());

    let edge_bp = load_edge_bp_marginals(&bp_path).ok();
    if edge_bp.is_some() {
        eprintln!("loaded edge_bp_marginals from {}", bp_path.display());
    }

    let records_prior = load_records_prior_map(&records_json).ok();
    if let Some(ref r) = records_prior {
        let n_nonzero = r.iter().filter(|v| !v.is_empty()).count();
        eprintln!("loaded records-prior map from {}, {} cells with priors",
            records_json.display(), n_nonzero);
    } else {
        eprintln!("WARNING: failed to load records-prior map from {}", records_json.display());
    }

    let out_dir = PathBuf::from("output/vol-41/records_prior_ab");
    std::fs::create_dir_all(&out_dir).expect("mkdir");

    // === Arm A: baseline EdgeBpMarginals ===
    let solver_a = EngineSolver::joe_depth150_bp_par();
    let mut opts_a = SolveOpts::default();
    opts_a.time_budget_ms = budget_ms;
    opts_a.seed = seed;
    opts_a.hints = hints.clone();
    opts_a.edge_bp_marginals = edge_bp.clone();
    let log_a = out_dir.join("arm_a_baseline.log");
    eprintln!("\n=== ARM A: baseline (EdgeBpMarginals) ===");
    let result_a = run_arm("baseline_edge_bp", solver_a, &puzzle, opts_a, &log_a, budget_ms);

    // === Arm B: RecordsPrior ===
    // Use joe_depth150_bp_par as base but override value_order to RecordsPrior.
    let solver_b = EngineSolver::joe_depth150_bp_par()
        .with_value_order(eternity2_solver_engine::ValueOrder::RecordsPrior);
    let mut opts_b = SolveOpts::default();
    opts_b.time_budget_ms = budget_ms;
    opts_b.seed = seed;
    opts_b.hints = hints.clone();
    opts_b.records_prior_map = records_prior;
    let log_b = out_dir.join("arm_b_records_prior.log");
    eprintln!("\n=== ARM B: RecordsPrior ===");
    let result_b = run_arm("records_prior", solver_b, &puzzle, opts_b, &log_b, budget_ms);

    eprintln!("\n=== A/B SUMMARY ===");
    eprintln!("Metric           |     A (baseline)  |  B (records-prior)  |  Δ");
    eprintln!("max_depth        |  {:>16}  |  {:>17}  |  {:+}",
        result_a.max_depth, result_b.max_depth,
        result_b.max_depth as i64 - result_a.max_depth as i64);
    eprintln!("nodes            |  {:>16}  |  {:>17}  |  {:+}",
        result_a.nodes, result_b.nodes,
        result_b.nodes as i64 - result_a.nodes as i64);
    eprintln!("matched_edges    |  {:>16}  |  {:>17}  |  {:+}",
        result_a.edge_matches, result_b.edge_matches,
        result_b.edge_matches as i64 - result_a.edge_matches as i64);
    eprintln!("placed           |  {:>16}  |  {:>17}  |  {:+}",
        result_a.pieces_placed, result_b.pieces_placed,
        result_b.pieces_placed as i64 - result_a.pieces_placed as i64);
    eprintln!("elapsed_s        |  {:>16.1}  |  {:>17.1}  |  {:+.1}",
        result_a.elapsed_s, result_b.elapsed_s,
        result_b.elapsed_s - result_a.elapsed_s);

    let depth_change_pct = if result_a.max_depth > 0 {
        100.0 * (result_b.max_depth as f64 - result_a.max_depth as f64) / result_a.max_depth as f64
    } else { 0.0 };
    let node_change_pct = if result_a.nodes > 0 {
        100.0 * (result_b.nodes as f64 - result_a.nodes as f64) / result_a.nodes as f64
    } else { 0.0 };
    eprintln!("\nDepth change: {:+.1}%   Node change: {:+.1}%", depth_change_pct, node_change_pct);
    eprintln!("Gate: ≥5% depth lift OR ≥5% node reduction at iso-depth");
    if depth_change_pct >= 5.0 {
        eprintln!("** GATE PASS ** (depth lift ≥ 5%)");
    } else if result_b.max_depth >= result_a.max_depth && node_change_pct <= -5.0 {
        eprintln!("** GATE PASS ** (node reduction at iso-depth ≥ 5%)");
    } else {
        eprintln!("** Gate not met **");
    }

    // JSON summary
    let summary = serde_json::json!({
        "budget_ms": budget_ms,
        "seed": seed,
        "arm_a": {
            "label": result_a.label,
            "max_depth": result_a.max_depth,
            "nodes": result_a.nodes,
            "matched_edges": result_a.edge_matches,
            "placed": result_a.pieces_placed,
            "elapsed_s": result_a.elapsed_s,
        },
        "arm_b": {
            "label": result_b.label,
            "max_depth": result_b.max_depth,
            "nodes": result_b.nodes,
            "matched_edges": result_b.edge_matches,
            "placed": result_b.pieces_placed,
            "elapsed_s": result_b.elapsed_s,
        },
        "depth_change_pct": depth_change_pct,
        "node_change_pct": node_change_pct,
    });
    let json_path = out_dir.join("summary.json");
    std::fs::write(&json_path, serde_json::to_string_pretty(&summary).unwrap()).unwrap();
    eprintln!("\nsaved summary: {}", json_path.display());

    // Save partial boards from both arms for downstream ALNS testing.
    let board_a_path = out_dir.join("arm_a_baseline_partial.json");
    save_board_sparse(&board_a_path, &puzzle, &result_a.board);
    eprintln!("saved arm A partial: {}", board_a_path.display());
    let board_b_path = out_dir.join("arm_b_records_prior_partial.json");
    save_board_sparse(&board_b_path, &puzzle, &result_b.board);
    eprintln!("saved arm B partial: {}", board_b_path.display());
}
