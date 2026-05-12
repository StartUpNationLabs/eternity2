// Vol-14 experiment — hint-centric variable-order via SolveOpts.path
// + PathPolicy::PrefixConstraint.
//
// Builds a path that orders all 256 cells by minimum Chebyshev
// distance to the nearest canonical hint, breaks ties by row-major
// position. With path_policy = PrefixConstraint { k: 256 }, the
// engine follows this path strictly for the entire search.
//
// Empirical hypothesis (vol-14 scan-order analysis): on canonical
// 5-clue E2 the hard region is centered around the hint cluster.
// Top-down scan reaches it at depth ~136 on the 442 board; a
// hint-centric scan reaches it at depth ~10-50, making conflicts
// fail-fast and reducing search-tree size.
//
// CLI: --budget-ms <ms> (default 60_000), --seed <u64> (default 1),
// --profile {joe,joe_bp} (default joe), --use-edge-bp (load BP marginals).

// Vol-16 Cat-3 — migrated to shared `bench_audit` helpers.

use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit::{placed_count, score_board, ProgressSink};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::bucas_url;
use eternity2_core::{PathPolicy, Position};
use eternity2_solver_engine::{load_edge_bp_marginals, EngineSolver};
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

const W: u32 = 16;
const H: u32 = 16;

/// Build a path of length cell_count, ordered by:
///   primary: min Chebyshev distance to any hint cell (smaller first)
///   secondary: row-major position (deterministic)
fn build_hint_centric_path(hint_positions: &[Position]) -> Vec<Position> {
    let hints_xy: Vec<(u32, u32)> = hint_positions.iter().map(|&p| (p % W, p / W)).collect();
    let mut all: Vec<(u32, u32, Position)> = Vec::with_capacity((W * H) as usize);
    for pos in 0..W * H {
        let x = pos % W;
        let y = pos / W;
        let d = hints_xy.iter()
            .map(|&(hx, hy)| std::cmp::max(x.abs_diff(hx), y.abs_diff(hy)))
            .min()
            .unwrap_or(0);
        all.push((d, pos, pos)); // (primary: distance, secondary: row-major pos)
    }
    all.sort_by_key(|&(d, p, _)| (d, p));
    all.into_iter().map(|(_, _, pos)| pos).collect()
}


fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let bp_path = PathBuf::from("output/v12_bp/edge_bp_60i.json");

    let run_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let out_dir = PathBuf::from(format!("output/v14_hintcentric/run_{run_id}"));
    std::fs::create_dir_all(&out_dir).expect("mkdir");
    #[cfg(unix)] {
        let latest = PathBuf::from("output/v14_hintcentric/latest");
        let _ = std::fs::remove_file(&latest);
        let _ = std::os::unix::fs::symlink(format!("run_{run_id}"), &latest);
    }

    // CLI
    let mut budget_ms: u64 = 60_000;
    let mut seed: u64 = 1;
    let mut profile = "joe_bp".to_string();
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--budget-ms" => budget_ms = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            "--profile" => profile = args.next().unwrap(),
            _ => eprintln!("(unrecognized: {a})"),
        }
    }

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    eprintln!("loaded canonical E2: {}x{} {} hints", puzzle.width, puzzle.height, hints.hints.len());

    let hint_positions: Vec<Position> = hints.hints.iter().map(|h| h.position).collect();
    let path = build_hint_centric_path(&hint_positions);
    eprintln!("hint-centric path built: {} cells, first 10: {:?}",
        path.len(), &path[..10.min(path.len())]);

    // Dump path for inspection
    let path_path = out_dir.join("path.json");
    let _ = std::fs::write(&path_path,
        serde_json::to_string_pretty(&path).unwrap());

    // Run side-by-side: A = default (PathPolicy::Ignored), B = PrefixConstraint
    let edge_bp = if profile == "joe_bp" {
        eprintln!("loading edge-BP marginals...");
        Some(load_edge_bp_marginals(&bp_path).expect("load edge_bp"))
    } else { None };

    let mut summary = serde_json::json!({
        "schema_version": 1,
        "puzzle": "canonical E2",
        "budget_ms": budget_ms,
        "seed": seed,
        "profile": profile,
        "arms": [],
    });
    let arms_idx = summary.as_object_mut().unwrap()
        .get_mut("arms").unwrap().as_array_mut().unwrap();

    for (label, policy) in [
        ("default_top_down", PathPolicy::Ignored),
        ("hint_centric",     PathPolicy::PrefixConstraint { k: 256 }),
    ] {
        eprintln!("\n=== arm: {label} ===");
        let log_path = out_dir.join(format!("{label}.log"));
        let mut sink = ProgressSink::new(&log_path, 5_000).expect("open log");

        let mut opts = SolveOpts::default();
        opts.time_budget_ms = budget_ms;
        opts.seed = seed;
        opts.hints = hints.clone();
        opts.edge_bp_marginals = edge_bp.clone();
        if matches!(policy, PathPolicy::PrefixConstraint { .. }) {
            opts.path = path.clone();
            opts.path_policy = policy;
        }

        let mut solver = match profile.as_str() {
            "joe"    => EngineSolver::joe_depth150_par(),
            "joe_bp" => EngineSolver::joe_depth150_bp_par(),
            _ => panic!("unknown --profile {profile}"),
        };
        let t0 = Instant::now();
        let outcome = solver.solve(&puzzle, &opts, &mut sink);
        let elapsed = t0.elapsed();
        let final_stats = sink.final_stats.clone();

        let board = match outcome {
            SolveOutcome::Solved(b) => Some(b),
            SolveOutcome::TimedOut { best_partial, .. } => Some(best_partial),
            SolveOutcome::Cancelled { best_partial, .. } => Some(best_partial),
            _ => None,
        };

        let (placed, matched, bucas) = if let Some(b) = board.as_ref() {
            let p = placed_count(b, &puzzle);
            let (m, _) = score_board(&puzzle, b);
            let bu = bucas_url(&puzzle, b, &format!("v14_hc_{label}"));
            (p, m, Some(bu))
        } else { (0, 0, None) };

        let (nodes, depth, nps) = final_stats.as_ref().map(|s| (
            s.nodes, s.max_depth_seen,
            s.nodes as f64 / elapsed.as_secs_f64().max(1e-6)
        )).unwrap_or((0, sink.best_depth, 0.0));

        let line = format!(
            "{label:>20}  elapsed={:.1}s  depth={depth:>4}  placed={placed:>3}/256  matched={matched:>3}/480  nodes={nodes:>8}  nps={nps:.0}",
            elapsed.as_secs_f64()
        );
        eprintln!("{line}");
        arms_idx.push(serde_json::json!({
            "label": label,
            "elapsed_s": elapsed.as_secs_f64(),
            "max_depth_seen": depth,
            "pieces_placed": placed,
            "matched_480": matched,
            "nodes": nodes,
            "nps": nps,
            "bucas": bucas,
        }));
    }

    let report_path = out_dir.join("ab_report.json");
    std::fs::write(&report_path,
        serde_json::to_string_pretty(&summary).unwrap()).expect("write");
    eprintln!("\nReport: {}", report_path.display());
}
