// Vol-14 — canonical E2 with the user's "rectangle skeleton" path
// combined with ALL our best techniques:
//   - Multi-core root-split
//   - gacolor + AC-3 + NS-1 propagators with depth-150 gate
//   - Edge-BP marginals as value-order (vol-14 #1)
//   - PathPolicy::PrefixConstraint with the rectangle skeleton path
//   - 5 canonical hints pinned
//   - ALNS-fill stage (with hint-pinning bug fix)
//
// CLI:
//   --cp-budget-ms      (default 300_000 = 5 min)
//   --alns-budget-ms    (default 300_000 = 5 min; 0 = skip)
//   --seed              (default 1)

use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit::ProgressSink;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::bucas_url;
use eternity2_core::{Board, PathPolicy, Position};
use eternity2_localsearch::{
    run_alns, Acceptance, AlnsConfig, ConflictDriven, DestroyOp, MwpmDefectPair,
    RandomRegion, RepairKind, WorstWindow,
};
use eternity2_solver_engine::{load_edge_bp_marginals, EngineSolver};
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

const W: u32 = 16;

fn pos(x: u32, y: u32) -> Position { y * W + x }

fn build_rectangle_path() -> Vec<Position> {
    // Canonical E2 hint geometry:
    //   (2,2) TL = pos 34       (13,2)  TR = pos 45
    //   (2,13) BL = pos 210     (13,13) BR = pos 221
    //   (7,8)  C  = pos 135
    let mut path = Vec::new();
    let mut seen = std::collections::HashSet::new();
    let push = |p: Position, path: &mut Vec<Position>, seen: &mut std::collections::HashSet<Position>| {
        if seen.insert(p) { path.push(p); }
    };
    // Top row y=2 from x=2 to x=13
    for x in 2..=13 { push(pos(x, 2), &mut path, &mut seen); }
    // Right col x=13 from y=3 to y=13
    for y in 3..=13 { push(pos(13, y), &mut path, &mut seen); }
    // Bottom row y=13 from x=12 down to x=2
    for x in (2..=12).rev() { push(pos(x, 13), &mut path, &mut seen); }
    // Left col x=2 from y=12 up to y=3
    for y in (3..=12).rev() { push(pos(2, y), &mut path, &mut seen); }
    // Spoke to center hint: row y=8 from x=2 to x=7
    for x in 2..=7 { push(pos(x, 8), &mut path, &mut seen); }
    path
}

fn score_board(puzzle: &eternity2_core::Puzzle, board: &Board) -> (u32, u32) {
    let (w, h) = (puzzle.width, puzzle.height);
    let total = (w - 1) * h + w * (h - 1);
    let mut matched = 0u32;
    for y in 0..h {
        for x in 0..w {
            let pp = y*w+x;
            let Some((pid, rot)) = board.get(pp) else { continue; };
            let p = puzzle.piece(pid).unwrap();
            let e = p.edges.rotated(rot).as_array();
            if x+1 < w {
                if let Some((np, nr)) = board.get(pp+1) {
                    let npp = puzzle.piece(np).unwrap();
                    if e[1] == npp.edges.rotated(nr).as_array()[3] { matched += 1; }
                }
            }
            if y+1 < h {
                if let Some((np, nr)) = board.get(pp+w) {
                    let npp = puzzle.piece(np).unwrap();
                    if e[2] == npp.edges.rotated(nr).as_array()[0] { matched += 1; }
                }
            }
        }
    }
    (matched, total)
}

fn placed_count(b: &Board, puzzle: &eternity2_core::Puzzle) -> u32 {
    (0..puzzle.cell_count()).filter(|&p| b.get(p).is_some()).count() as u32
}

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let bp_path = PathBuf::from("output/v12_bp/edge_bp_60i.json");

    let mut cp_budget: u64 = 300_000;
    let mut alns_budget: u64 = 300_000;
    let mut seed: u64 = 1;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--cp-budget-ms" => cp_budget = args.next().unwrap().parse().unwrap(),
            "--alns-budget-ms" => alns_budget = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            _ => {}
        }
    }

    let run_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let out_dir = PathBuf::from(format!("output/v14_e2_full/run_{run_id}"));
    std::fs::create_dir_all(&out_dir).expect("mkdir");

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    eprintln!("loaded canonical E2 with {} hints", hints.hints.len());

    let edge_bp = load_edge_bp_marginals(&bp_path).expect("load bp");
    eprintln!("loaded edge-BP marginals");

    let path = build_rectangle_path();
    eprintln!("rectangle path: {} cells, first 5: {:?}, last 5: {:?}",
        path.len(),
        &path[..5.min(path.len())],
        &path[path.len().saturating_sub(5)..]);

    // === Stage 1: CP with everything turned on ===
    eprintln!("\n=== Stage 1: CP (joe_depth150_bp_par + rectangle path, {}s) ===", cp_budget/1000);
    let mut solver = EngineSolver::joe_depth150_bp_par();
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = cp_budget;
    opts.seed = seed;
    opts.hints = hints.clone();
    opts.edge_bp_marginals = Some(edge_bp);
    opts.path = path.clone();
    opts.path_policy = PathPolicy::PrefixConstraint { k: path.len() as u32 };

    let cp_log_path = out_dir.join("cp.log");
    let mut sink = ProgressSink::new(&cp_log_path, 5_000).expect("open cp.log");
    sink.write_line(&format!("=== Stage 1: CP (joe_depth150_bp_par + rectangle path), budget={cp_budget}ms, seed={seed} ==="));
    eprintln!("CP progress log: {}", cp_log_path.display());
    let t_cp = Instant::now();
    let outcome = solver.solve(&puzzle, &opts, &mut sink);
    let cp_elapsed = t_cp.elapsed();
    let stats_cp = sink.final_stats.clone();

    let cp_board: Board = match outcome {
        SolveOutcome::Solved(b) => b,
        SolveOutcome::TimedOut { best_partial, .. } => best_partial,
        SolveOutcome::Cancelled { best_partial, .. } => best_partial,
        SolveOutcome::AllSolutions(bs) => bs.into_iter().next().unwrap_or_else(|| Board::empty(&puzzle)),
        _ => Board::empty(&puzzle),
    };
    let (cp_m, cp_t) = score_board(&puzzle, &cp_board);
    let cp_p = placed_count(&cp_board, &puzzle);
    let cp_depth = stats_cp.as_ref().map(|s| s.max_depth_seen).unwrap_or(sink.best_depth);
    let cp_nodes = stats_cp.as_ref().map(|s| s.nodes).unwrap_or(0);
    let cp_bucas = bucas_url(&puzzle, &cp_board, "v14_full_cp");

    eprintln!("CP: elapsed={:.1}s  depth={cp_depth}  placed={cp_p}/256  matched={cp_m}/{cp_t}  nodes={cp_nodes}",
        cp_elapsed.as_secs_f64());
    eprintln!("CP bucas: {cp_bucas}");
    let _ = std::fs::write(out_dir.join("cp_board.json"), serde_json::to_string_pretty(
        &serde_json::json!({
            "placement": (0..puzzle.cell_count()).map(|p| {
                cp_board.get(p).map(|(pid, rot)| serde_json::json!({
                    "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
                }))
            }).collect::<Vec<_>>(),
            "bucas_url": &cp_bucas,
        })
    ).unwrap());

    // === Stage 2: ALNS-fill ===
    if alns_budget > 0 && cp_m < cp_t {
        eprintln!("\n=== Stage 2: ALNS-fill (hints pinned, {}s) ===", alns_budget/1000);
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
            verbose: true,
            repair: RepairKind::Sa,
            cp_fallback_to_sa: true,
            pinned_positions: hints.hints.iter().map(|h| h.position).collect(),
        };
        let t_alns = Instant::now();
        let (alns_board, alns_stats) = run_alns(&puzzle, &cp_board, ops.as_mut_slice(), &cfg);
        let alns_elapsed = t_alns.elapsed();
        let (am, at) = score_board(&puzzle, &alns_board);
        let ap = placed_count(&alns_board, &puzzle);
        let alns_bucas = bucas_url(&puzzle, &alns_board, "v14_full_alns");
        eprintln!("\nALNS: elapsed={:.1}s  iters={}  placed={ap}/256  matched={am}/{at}  Δ={:+}",
            alns_elapsed.as_secs_f64(), alns_stats.iters, am as i32 - cp_m as i32);
        eprintln!("ALNS bucas: {alns_bucas}");

        let _ = std::fs::write(out_dir.join("alns_board.json"), serde_json::to_string_pretty(
            &serde_json::json!({
                "placement": (0..puzzle.cell_count()).map(|p| {
                    alns_board.get(p).map(|(pid, rot)| serde_json::json!({
                        "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
                    }))
                }).collect::<Vec<_>>(),
                "bucas_url": &alns_bucas,
            })
        ).unwrap());
    }

    eprintln!("\nReports saved to {}", out_dir.display());
}
