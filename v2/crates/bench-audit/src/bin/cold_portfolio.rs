// Vol-17 idea L — cold portfolio: run joe_depth150_bp_par on N
// different seeds, each followed by ALNS, and report variance.
//
// Motivation: vol-15 seed-1 hit 439/480 on baseline, but we've NEVER
// measured baseline variance across seeds. Log-normal search heuristics
// suggest best-of-K typically beats median by 5-15 matched edges. A
// cheap T1 hedge that ALSO gives every later vol-17 experiment a
// variance-aware comparison baseline.
//
// Two arms are run per seed when --arms=both is set:
//   baseline:   joe_depth150_bp_par CP + ALNS
//   calibrated: blackwood_raw_par (calibrated_v17a schedule) + ALNS
//
// Per-arm output: median/IQR/best/worst over the seed grid.
//
// CLI:
//   --seeds        "1,2,3,4,5,6,7,8" (default) — comma-separated u64s
//   --cp-ms        per-arm CP budget (default 300_000 = 5 min)
//   --alns-ms      per-arm ALNS budget (default 300_000)
//   --arms         "both" (default) | "baseline" | "calibrated"

#![forbid(unsafe_code)]

use std::path::PathBuf;
use std::sync::Arc;
use std::time::Instant;

use eternity2_bench_audit::{placed_count, score_board_dense as score_board, ProgressSink};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::bucas_url;
use eternity2_core::{Board, Hints, Puzzle};
use eternity2_localsearch::{
    run_alns, Acceptance, AlnsConfig, ComponentDestroy, ComponentPlusHaloDestroy,
    ConflictDriven, DestroyOp, MwpmDefectPair, RandomRegion, RepairKind, WorstBand,
    WorstRow, WorstWindow,
};
use eternity2_solver_engine::{
    blackwood_schedule_calibrated_v17a, load_edge_bp_marginals, EngineSolver,
};
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

#[derive(Debug, Clone)]
struct ArmResult {
    seed: u64,
    arm: String,
    cp_matched: u32,
    cp_placed: u32,
    cp_depth: u32,
    cp_elapsed_s: f64,
    alns_matched: u32,
    alns_placed: u32,
    alns_elapsed_s: f64,
    cp_bucas: String,
    alns_bucas: String,
}

fn run_one_arm(
    arm: &str,
    puzzle: &Puzzle,
    hints: &Hints,
    edge_bp: Option<Arc<Vec<f32>>>,
    seed: u64,
    cp_ms: u64,
    alns_ms: u64,
    out_dir: &std::path::Path,
) -> ArmResult {
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = cp_ms;
    opts.seed = seed;
    opts.hints = hints.clone();
    if let Some(bp) = edge_bp { opts.edge_bp_marginals = Some(bp); }

    let mut solver: Box<EngineSolver> = match arm {
        "baseline" => Box::new(EngineSolver::joe_depth150_bp_par()),
        "calibrated" => {
            let sched = blackwood_schedule_calibrated_v17a(puzzle, hints)
                .expect("calibrated_v17a schedule");
            Box::new(EngineSolver::blackwood_raw_par(Arc::new(sched)))
        }
        other => panic!("unknown arm {other}"),
    };

    let log = out_dir.join(format!("{arm}_seed{seed}_cp.log"));
    let mut sink = ProgressSink::new(&log, 10_000).expect("open log");
    let t = Instant::now();
    let outcome = solver.solve(puzzle, &opts, &mut sink);
    let cp_elapsed = t.elapsed();
    let stats = sink.final_stats.clone();
    let cp_board: Board = match outcome {
        SolveOutcome::Solved(b)
        | SolveOutcome::TimedOut { best_partial: b, .. }
        | SolveOutcome::Cancelled { best_partial: b, .. } => b,
        SolveOutcome::AllSolutions(bs) => bs.into_iter().next().unwrap_or_else(|| Board::empty(puzzle)),
        _ => Board::empty(puzzle),
    };
    let (cp_m, _) = score_board(puzzle, &cp_board);
    let cp_p = placed_count(&cp_board, puzzle);
    let cp_d = stats.as_ref().map(|s| s.max_depth_seen).unwrap_or(sink.best_depth);
    let cp_bucas = bucas_url(puzzle, &cp_board, &format!("v17_{arm}_s{seed}_cp"));

    // ALNS
    let mut ops: Vec<Box<dyn DestroyOp>> = vec![
        Box::new(RandomRegion { k: 4 }),
        Box::new(WorstWindow { k: 5 }),
        Box::new(ConflictDriven { max_size: 30 }),
        Box::new(ConflictDriven { max_size: 80 }),
        Box::new(MwpmDefectPair { max_pairs: 12 }),
        Box::new(WorstBand { k_rows: 4 }),
        Box::new(ComponentDestroy { max_size: 100, min_size: 6 }),
        Box::new(ComponentPlusHaloDestroy { max_size: 100, min_size: 6 }),
        Box::new(WorstRow),
    ];
    let cfg = AlnsConfig {
        time_budget_ms: alns_ms,
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
    let (alns_board, _alns_stats) = run_alns(puzzle, &cp_board, ops.as_mut_slice(), &cfg);
    let alns_elapsed = t_alns.elapsed();
    let (am, _) = score_board(puzzle, &alns_board);
    let ap = placed_count(&alns_board, puzzle);
    let alns_bucas = bucas_url(puzzle, &alns_board, &format!("v17_{arm}_s{seed}_alns"));

    // Persist board JSONs for any seed-arm we might want to inspect.
    let _ = std::fs::write(
        out_dir.join(format!("{arm}_seed{seed}_cp.json")),
        serde_json::to_string_pretty(&serde_json::json!({
            "seed": seed, "arm": arm,
            "matched": cp_m, "placed": cp_p, "depth": cp_d,
            "bucas_url": &cp_bucas,
        })).unwrap(),
    );
    let _ = std::fs::write(
        out_dir.join(format!("{arm}_seed{seed}_alns.json")),
        serde_json::to_string_pretty(&serde_json::json!({
            "seed": seed, "arm": arm,
            "matched": am, "placed": ap,
            "bucas_url": &alns_bucas,
        })).unwrap(),
    );

    ArmResult {
        seed, arm: arm.into(),
        cp_matched: cp_m, cp_placed: cp_p, cp_depth: cp_d,
        cp_elapsed_s: cp_elapsed.as_secs_f64(),
        alns_matched: am, alns_placed: ap,
        alns_elapsed_s: alns_elapsed.as_secs_f64(),
        cp_bucas, alns_bucas,
    }
}

fn quantile(vals: &mut [u32], q: f64) -> u32 {
    if vals.is_empty() { return 0; }
    vals.sort_unstable();
    let idx = ((vals.len() as f64 - 1.0) * q).round() as usize;
    vals[idx.min(vals.len() - 1)]
}

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let bp_path = PathBuf::from("output/v12_bp/edge_bp_60i.json");

    let mut seeds_str = "1,2,3,4,5,6,7,8".to_string();
    let mut cp_ms: u64 = 300_000;
    let mut alns_ms: u64 = 300_000;
    let mut arms_str = "both".to_string();
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--seeds" => seeds_str = args.next().unwrap(),
            "--cp-ms" => cp_ms = args.next().unwrap().parse().unwrap(),
            "--alns-ms" => alns_ms = args.next().unwrap().parse().unwrap(),
            "--arms" => arms_str = args.next().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }
    let seeds: Vec<u64> = seeds_str.split(',').map(|s| s.parse().expect("u64")).collect();
    let arms: Vec<&str> = match arms_str.as_str() {
        "both" => vec!["baseline", "calibrated"],
        "baseline" => vec!["baseline"],
        "calibrated" => vec!["calibrated"],
        other => panic!("unknown --arms {other}"),
    };

    let run_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let out_dir = PathBuf::from(format!("output/v17_cold_portfolio/run_{run_id}"));
    std::fs::create_dir_all(&out_dir).expect("mkdir");

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let edge_bp = load_edge_bp_marginals(&bp_path).ok();
    eprintln!(
        "=== vol-17 cold portfolio === seeds={:?} arms={:?} cp_ms={} alns_ms={}",
        seeds, arms, cp_ms, alns_ms,
    );
    eprintln!("output: {}", out_dir.display());

    let mut results: Vec<ArmResult> = Vec::new();
    let t_total = Instant::now();
    for &seed in &seeds {
        for &arm in &arms {
            eprintln!("\n--- arm={arm} seed={seed} ---");
            let r = run_one_arm(arm, &puzzle, &hints, edge_bp.clone(), seed, cp_ms, alns_ms, &out_dir);
            eprintln!(
                "[{arm} seed={seed}]  CP {:.0}s {}/{} placed depth={}  →  ALNS {:.0}s {}/{} placed  matched={}/480",
                r.cp_elapsed_s, r.cp_placed, puzzle.cell_count(), r.cp_depth,
                r.alns_elapsed_s, r.alns_placed, puzzle.cell_count(), r.alns_matched,
            );
            results.push(r);
        }
    }
    eprintln!("\nTotal wall: {:.1}s", t_total.elapsed().as_secs_f64());

    // Aggregate per-arm.
    eprintln!("\n=== vol-17 cold-portfolio summary ===");
    for &arm in &arms {
        let arm_results: Vec<&ArmResult> = results.iter().filter(|r| r.arm == arm).collect();
        let alns_vals: Vec<u32> = arm_results.iter().map(|r| r.alns_matched).collect();
        let cp_vals: Vec<u32> = arm_results.iter().map(|r| r.cp_matched).collect();
        let alns_min = *alns_vals.iter().min().unwrap_or(&0);
        let alns_max = *alns_vals.iter().max().unwrap_or(&0);
        let alns_med = quantile(&mut alns_vals.clone(), 0.5);
        let alns_p25 = quantile(&mut alns_vals.clone(), 0.25);
        let alns_p75 = quantile(&mut alns_vals.clone(), 0.75);
        let cp_min = *cp_vals.iter().min().unwrap_or(&0);
        let cp_max = *cp_vals.iter().max().unwrap_or(&0);
        let cp_med = quantile(&mut cp_vals.clone(), 0.5);
        eprintln!(
            "  arm={arm:<12}  ALNS min={alns_min} p25={alns_p25} median={alns_med} p75={alns_p75} max={alns_max} \
             (CP min={cp_min} median={cp_med} max={cp_max})"
        );
    }

    // Per-seed table.
    eprintln!("\n=== per-seed results ===");
    eprintln!("{:>4} {:>10} {:>6} {:>6} {:>6} {:>6} {:>6}", "seed", "arm", "cp_p", "cp_m", "cp_d", "al_p", "al_m");
    for r in &results {
        eprintln!(
            "{:>4} {:>10} {:>6} {:>6} {:>6} {:>6} {:>6}",
            r.seed, r.arm, r.cp_placed, r.cp_matched, r.cp_depth, r.alns_placed, r.alns_matched
        );
    }

    // JSON summary.
    let summary = serde_json::json!({
        "seeds": seeds,
        "arms": arms,
        "cp_ms": cp_ms, "alns_ms": alns_ms,
        "results": results.iter().map(|r| serde_json::json!({
            "seed": r.seed, "arm": r.arm,
            "cp": { "matched": r.cp_matched, "placed": r.cp_placed, "depth": r.cp_depth, "elapsed_s": r.cp_elapsed_s, "bucas": r.cp_bucas },
            "alns": { "matched": r.alns_matched, "placed": r.alns_placed, "elapsed_s": r.alns_elapsed_s, "bucas": r.alns_bucas },
        })).collect::<Vec<_>>(),
    });
    let _ = std::fs::write(out_dir.join("summary.json"), serde_json::to_string_pretty(&summary).unwrap());
    eprintln!("\nsummary: {}/summary.json", out_dir.display());
}
