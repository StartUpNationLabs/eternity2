// Vol-15 — canonical E2 with the Blackwood algorithm.
//
// Runs two arms in series on the canonical 16×16 puzzle with 5 hints:
//   1. baseline:  joe_depth150_bp_par + ALNS-fill (vol-14 ceiling).
//   2. blackwood: BLACKWOOD_BASE_PAR + ALNS-fill.
//
// CLI:
//   --cp-budget-ms      default 300_000 (5 min)
//   --alns-budget-ms    default 300_000 (5 min)
//   --seed              default 1
//   --arms              "both" (default) | "baseline" | "blackwood"
//
// Output: output/v15_e2_blackwood/run_<ts>/{baseline,blackwood}_{cp,alns}.{log,board.json}

use std::path::PathBuf;
use std::sync::Arc;
use std::time::Instant;

use eternity2_bench_audit::ProgressSink;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::bucas_url;
use eternity2_core::{Board, Puzzle};
use eternity2_localsearch::{
    run_alns, Acceptance, AlnsConfig, ConflictDriven, DestroyOp, MwpmDefectPair,
    RandomRegion, RepairKind, WorstWindow,
};
use eternity2_solver_engine::{
    blackwood_schedule_469, load_edge_bp_marginals, EngineConfig, EngineSolver,
    PathSkeleton,
};
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

fn score_board(puzzle: &Puzzle, board: &Board) -> (u32, u32) {
    let (w, h) = (puzzle.width, puzzle.height);
    let total = (w - 1) * h + w * (h - 1);
    let mut matched = 0u32;
    for y in 0..h {
        for x in 0..w {
            let pp = y * w + x;
            let Some((pid, rot)) = board.get(pp) else { continue; };
            let p = puzzle.piece(pid).unwrap();
            let e = p.edges.rotated(rot).as_array();
            if x + 1 < w {
                if let Some((np, nr)) = board.get(pp + 1) {
                    let npp = puzzle.piece(np).unwrap();
                    if e[1] == npp.edges.rotated(nr).as_array()[3] { matched += 1; }
                }
            }
            if y + 1 < h {
                if let Some((np, nr)) = board.get(pp + w) {
                    let npp = puzzle.piece(np).unwrap();
                    if e[2] == npp.edges.rotated(nr).as_array()[0] { matched += 1; }
                }
            }
        }
    }
    (matched, total)
}

fn placed_count(b: &Board, puzzle: &Puzzle) -> u32 {
    (0..puzzle.cell_count()).filter(|&p| b.get(p).is_some()).count() as u32
}

fn run_arm(
    label: &str,
    mut solver: Box<EngineSolver>,
    puzzle: &Puzzle,
    hints: &eternity2_core::Hints,
    edge_bp: Option<Arc<Vec<f32>>>,
    seed: u64,
    cp_budget_ms: u64,
    alns_budget_ms: u64,
    out_dir: &std::path::Path,
) -> (u32, u32, u32) {
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = cp_budget_ms;
    opts.seed = seed;
    opts.hints = hints.clone();
    if let Some(bp) = edge_bp.clone() {
        opts.edge_bp_marginals = Some(bp);
    }

    let cp_log = out_dir.join(format!("{label}_cp.log"));
    let mut sink = ProgressSink::new(&cp_log, 5_000).expect("open cp log");
    sink.write_line(&format!(
        "=== Stage 1: CP ({label}), budget={cp_budget_ms}ms, seed={seed} ==="
    ));
    eprintln!("[{label}] CP progress log: {}", cp_log.display());
    let t_cp = Instant::now();
    let outcome = solver.solve(puzzle, &opts, &mut sink);
    let cp_elapsed = t_cp.elapsed();
    let stats_cp = sink.final_stats.clone();

    let cp_board: Board = match outcome {
        SolveOutcome::Solved(b) => b,
        SolveOutcome::TimedOut { best_partial, .. } => best_partial,
        SolveOutcome::Cancelled { best_partial, .. } => best_partial,
        SolveOutcome::AllSolutions(bs) => bs.into_iter().next().unwrap_or_else(|| Board::empty(puzzle)),
        _ => Board::empty(puzzle),
    };
    let (cp_m, _cp_t) = score_board(puzzle, &cp_board);
    let cp_p = placed_count(&cp_board, puzzle);
    let cp_depth = stats_cp.as_ref().map(|s| s.max_depth_seen).unwrap_or(sink.best_depth);
    let cp_nodes = stats_cp.as_ref().map(|s| s.nodes).unwrap_or(0);
    let cp_url = bucas_url(puzzle, &cp_board, &format!("v15_{label}_cp"));
    eprintln!(
        "[{label}] CP: elapsed={:.1}s  depth={cp_depth}  placed={cp_p}/256  matched={cp_m}/480  nodes={cp_nodes}",
        cp_elapsed.as_secs_f64()
    );
    eprintln!("[{label}] CP bucas: {cp_url}");
    let _ = std::fs::write(
        out_dir.join(format!("{label}_cp_board.json")),
        serde_json::to_string_pretty(&serde_json::json!({
            "placement": (0..puzzle.cell_count()).map(|p| {
                cp_board.get(p).map(|(pid, rot)| serde_json::json!({
                    "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
                }))
            }).collect::<Vec<_>>(),
            "bucas_url": &cp_url,
        })).unwrap(),
    );

    if alns_budget_ms == 0 || cp_m >= 480 {
        return (cp_m, cp_p, cp_depth);
    }

    eprintln!("[{label}] Stage 2: ALNS-fill ({}s, hints pinned)", alns_budget_ms / 1000);
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
        pinned_positions: hints.hints.iter().map(|h| h.position).collect(),
    };
    let t_alns = Instant::now();
    let (alns_board, alns_stats) = run_alns(puzzle, &cp_board, ops.as_mut_slice(), &cfg);
    let alns_elapsed = t_alns.elapsed();
    let (am, _at) = score_board(puzzle, &alns_board);
    let ap = placed_count(&alns_board, puzzle);
    let alns_url = bucas_url(puzzle, &alns_board, &format!("v15_{label}_alns"));
    eprintln!(
        "[{label}] ALNS: elapsed={:.1}s  iters={}  placed={ap}/256  matched={am}/480  Δ_vs_cp={:+}",
        alns_elapsed.as_secs_f64(),
        alns_stats.iters,
        am as i32 - cp_m as i32
    );
    eprintln!("[{label}] ALNS bucas: {alns_url}");
    let _ = std::fs::write(
        out_dir.join(format!("{label}_alns_board.json")),
        serde_json::to_string_pretty(&serde_json::json!({
            "placement": (0..puzzle.cell_count()).map(|p| {
                alns_board.get(p).map(|(pid, rot)| serde_json::json!({
                    "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
                }))
            }).collect::<Vec<_>>(),
            "bucas_url": &alns_url,
        })).unwrap(),
    );
    (am, ap, cp_depth)
}

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let bp_path = PathBuf::from("output/v12_bp/edge_bp_60i.json");

    let mut cp_budget: u64 = 300_000;
    let mut alns_budget: u64 = 300_000;
    let mut seed: u64 = 1;
    let mut arms = "both".to_string();
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--cp-budget-ms" => cp_budget = args.next().unwrap().parse().unwrap(),
            "--alns-budget-ms" => alns_budget = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            "--arms" => arms = args.next().unwrap(),
            _ => {}
        }
    }

    let run_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let out_dir = PathBuf::from(format!("output/v15_e2_blackwood/run_{run_id}"));
    std::fs::create_dir_all(&out_dir).expect("mkdir");

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    eprintln!("loaded canonical E2 with {} hints", hints.hints.len());

    let edge_bp = load_edge_bp_marginals(&bp_path).ok();

    // Build Blackwood schedule.
    let schedule = blackwood_schedule_469(&puzzle, &hints)
        .expect("compute_heuristic_sides returned < 3 colors on canonical E2");
    eprintln!(
        "Blackwood schedule: heuristic_sides={:?}  pool_size={}  max_idx={}  breaks={:?}",
        schedule.heuristic_sides,
        schedule.heuristic_pool_size,
        schedule.max_heuristic_index,
        schedule.break_indexes_allowed
    );
    let schedule_arc = Arc::new(schedule);

    let mut results: Vec<(String, u32, u32, u32)> = Vec::new();

    if arms == "both" || arms == "baseline" {
        let baseline = Box::new(EngineSolver::joe_depth150_bp_par());
        let (m, p, d) = run_arm(
            "baseline",
            baseline,
            &puzzle,
            &hints,
            edge_bp.clone(),
            seed,
            cp_budget,
            alns_budget,
            &out_dir,
        );
        results.push(("baseline".into(), m, p, d));
    }

    if arms == "both" || arms == "blackwood" || arms == "all" {
        let bw = Box::new(EngineSolver::blackwood_base_par(schedule_arc.clone()));
        let (m, p, d) = run_arm(
            "blackwood",
            bw,
            &puzzle,
            &hints,
            edge_bp.clone(),
            seed,
            cp_budget,
            alns_budget,
            &out_dir,
        );
        results.push(("blackwood".into(), m, p, d));
    }

    // Vol-15 Priority 1.5: Blackwood × HintRectangle composition.
    // BLACKWOOD_BASE_PAR + path_skeleton = HintRectangle. The
    // composition rule in SearchState::new builds [rectangle prefix]
    // ++ [scan-order tail], so the engine places the 49 rectangle
    // cells first and Blackwood's break-indexes still index by raw
    // scan position (handled inside is_pos_break_index).
    if arms == "blackwood_rect" || arms == "all" {
        let mut cfg = EngineConfig::BLACKWOOD_BASE_PAR;
        cfg.path_skeleton = Some(PathSkeleton::HintRectangle);
        let bw_rect = Box::new(
            EngineSolver::new(cfg, "engine", "blackwood_rect_par")
                .with_blackwood_schedule(schedule_arc.clone()),
        );
        let (m, p, d) = run_arm(
            "blackwood_rect",
            bw_rect,
            &puzzle,
            &hints,
            edge_bp.clone(),
            seed,
            cp_budget,
            alns_budget,
            &out_dir,
        );
        results.push(("blackwood_rect".into(), m, p, d));
    }

    // Same, with the LAYERED rectangle (rectangle → interior →
    // annulus → border). Vol-14's strongest skeleton.
    if arms == "blackwood_rect_layered" || arms == "all" {
        let mut cfg = EngineConfig::BLACKWOOD_BASE_PAR;
        cfg.path_skeleton = Some(PathSkeleton::HintRectangleLayered);
        let bw_rl = Box::new(
            EngineSolver::new(cfg, "engine", "blackwood_rect_layered_par")
                .with_blackwood_schedule(schedule_arc.clone()),
        );
        let (m, p, d) = run_arm(
            "blackwood_rect_layered",
            bw_rl,
            &puzzle,
            &hints,
            edge_bp.clone(),
            seed,
            cp_budget,
            alns_budget,
            &out_dir,
        );
        results.push(("blackwood_rect_layered".into(), m, p, d));
    }

    // Vol-15 — "dumb Blackwood" arm: drops gacolor/AC-3/NS-1, keeps
    // only edge forward-checking + piece-uniqueness + schedule +
    // break allowance. Sound after break-index by construction.
    if arms == "blackwood_raw" || arms == "all" {
        let raw = Box::new(EngineSolver::blackwood_raw_par(schedule_arc.clone()));
        let (m, p, d) = run_arm(
            "blackwood_raw",
            raw,
            &puzzle,
            &hints,
            edge_bp.clone(),
            seed,
            cp_budget,
            alns_budget,
            &out_dir,
        );
        results.push(("blackwood_raw".into(), m, p, d));
    }

    eprintln!();
    eprintln!("=== SUMMARY (canonical E2, seed={seed}) ===");
    for (label, m, p, d) in &results {
        eprintln!("  {label:<24}  matched={m}/480  placed={p}/256  cp_depth={d}");
    }
    // Δ vs baseline for every non-baseline arm.
    if let Some(base) = results.iter().find(|(l, _, _, _)| l == "baseline") {
        eprintln!();
        for (label, m, _, _) in &results {
            if label == "baseline" { continue; }
            let d = *m as i32 - base.1 as i32;
            eprintln!("  Δ ({label:<24} − baseline) = {d:+}");
        }
    }
    eprintln!();
    eprintln!("Boards + logs: {}", out_dir.display());

    // Summary JSON with bucas URLs for both arms.
    let summary = serde_json::json!({
        "puzzle": "canonical_5_clue_16x16",
        "seed": seed,
        "schedule": {
            "heuristic_sides": &schedule_arc.heuristic_sides,
            "pool_size": schedule_arc.heuristic_pool_size,
            "max_heuristic_index": schedule_arc.max_heuristic_index,
            "break_indexes_allowed": &schedule_arc.break_indexes_allowed,
            "exhaustion_targets": &schedule_arc.exhaustion_targets,
        },
        "arms": results.iter().map(|(label, m, p, d)| serde_json::json!({
            "label": label, "matched_final": m, "placed_final": p, "cp_depth": d
        })).collect::<Vec<_>>(),
    });
    let summary_path = out_dir.join("summary.json");
    let _ = std::fs::write(&summary_path, serde_json::to_string_pretty(&summary).unwrap());
    eprintln!("Summary JSON: {}", summary_path.display());
}
