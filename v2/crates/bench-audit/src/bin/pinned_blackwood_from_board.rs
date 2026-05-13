// Vol-17 NOVEL — re-run Blackwood CP with extra hints from one of OUR
// own ALNS-converged boards.
//
// Take a saved board (e.g. our 455) at canonical-E2. Choose K cells in
// the "backbone region" (typically rows 5-15) and add them as
// additional Hints to SolveOpts (on top of the 5 canonical). Run
// Blackwood CP from scratch with these (5+K) hints.
//
// The hypothesis (H20): the extra hints FORCE the CP search to make
// different piece-region assignments, potentially leading to a CP
// partial that admits a HIGHER ALNS ceiling than our current 455.
//
// CLI:
//   pinned_blackwood_from_board --source-board PATH
//                              [--pin-rows-from 5] [--pin-rows-to 15]
//                              [--max-extra K]
//                              [--cp-budget-ms MS] [--alns-budget-ms MS]
//                              [--schedule calibrated_v17a]
//                              [--seed N]

#![forbid(unsafe_code)]

use std::path::PathBuf;
use std::sync::Arc;
use std::time::Instant;

use eternity2_bench_audit::{placed_count, score_board_dense as score_board, ProgressSink};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::bucas_url;
use eternity2_core::{Board, Hint, Hints, Rotation};
use eternity2_localsearch::{
    piece_swap_hillclimb, polish_rotations, run_alns, Acceptance, AlnsConfig,
    BottomBandDestroy, ComponentDestroy, ConflictDriven, DestroyOp, HingeDestroy,
    MwpmDefectPair, RandomRegion, RepairKind, WorstBand, WorstWindow,
};
use eternity2_solver_engine::{
    blackwood_schedule_calibrated_v17a, blackwood_schedule_calibrated_v17b, EngineSolver,
};
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

fn load_board(path: &std::path::Path) -> Board {
    let raw = std::fs::read_to_string(path).expect("read");
    let v: serde_json::Value = serde_json::from_str(&raw).expect("parse");
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let mut b = Board::empty(&puzzle);
    if let Some(arr) = v.get("placement").and_then(|x| x.as_array()) {
        for p in arr {
            if p.is_null() { continue; }
            let pos = p["pos"].as_u64().unwrap() as u32;
            let pid = p["piece_id"].as_u64().unwrap() as u16;
            let rot = Rotation::from_u8(p["rotation"].as_u64().unwrap() as u8).unwrap();
            b.place(pos, pid, rot);
        }
    }
    b
}

fn main() {
    let mut source_board = PathBuf::new();
    let mut pin_rows_from: u32 = 5;
    let mut pin_rows_to: u32 = 15;
    let mut max_extra: u32 = 50;
    let mut cp_budget_ms: u64 = 300_000;
    let mut alns_budget_ms: u64 = 300_000;
    let mut schedule = "calibrated_v17a".to_string();
    let mut seed: u64 = 1;

    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--source-board" => source_board = PathBuf::from(args.next().unwrap()),
            "--pin-rows-from" => pin_rows_from = args.next().unwrap().parse().unwrap(),
            "--pin-rows-to" => pin_rows_to = args.next().unwrap().parse().unwrap(),
            "--max-extra" => max_extra = args.next().unwrap().parse().unwrap(),
            "--cp-budget-ms" => cp_budget_ms = args.next().unwrap().parse().unwrap(),
            "--alns-budget-ms" => alns_budget_ms = args.next().unwrap().parse().unwrap(),
            "--schedule" => schedule = args.next().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }
    if source_board.as_os_str().is_empty() {
        eprintln!("--source-board required");
        std::process::exit(1);
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, canonical_hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let src = load_board(&source_board);
    let (src_m, _) = score_board(&puzzle, &src);
    eprintln!("source board: {src_m}/480 — {}", source_board.display());

    // Build extra hints from source board's pin-rows.
    let w = puzzle.width;
    let mut extras: Vec<Hint> = Vec::new();
    // Take cells in rows [pin_rows_from, pin_rows_to], skipping cells
    // already covered by canonical hints. Pick `max_extra` deterministically
    // by row-major order (could be smarter — e.g., pick backbone-only).
    let canonical_pos: std::collections::HashSet<u32> =
        canonical_hints.hints.iter().map(|h| h.position).collect();
    for y in pin_rows_from..=pin_rows_to {
        for x in 0..w {
            let pos = y * w + x;
            if canonical_pos.contains(&pos) { continue; }
            if extras.len() as u32 >= max_extra { break; }
            if let Some((pid, rot)) = src.get(pos) {
                extras.push(Hint { position: pos, piece_id: pid, rotation: rot });
            }
        }
        if extras.len() as u32 >= max_extra { break; }
    }
    eprintln!(
        "extra hints from rows {}..={}: {} (max_extra={})",
        pin_rows_from, pin_rows_to, extras.len(), max_extra
    );

    let mut all_hints: Vec<Hint> = canonical_hints.hints.clone();
    all_hints.extend(extras.iter().cloned());
    let combined = Hints::new(all_hints);
    eprintln!("total hints (canonical + extras): {}", combined.hints.len());

    // Build schedule.
    let sched = match schedule.as_str() {
        "calibrated_v17a" => blackwood_schedule_calibrated_v17a(&puzzle, &combined),
        "calibrated_v17b" => blackwood_schedule_calibrated_v17b(&puzzle, &combined),
        other => panic!("unknown --schedule {other}"),
    }.expect("schedule build failed");
    let sched_arc = Arc::new(sched);

    // Stage 1: Blackwood CP with extra hints.
    eprintln!("\n--- Stage 1: Blackwood CP (calibrated_v17a, budget {}s, {} hints) ---",
        cp_budget_ms / 1000, combined.hints.len());
    let mut solver = EngineSolver::blackwood_raw_par(sched_arc.clone());
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = cp_budget_ms;
    opts.seed = seed;
    opts.hints = combined.clone();

    let run_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let out_dir = PathBuf::from("output/v17_pinned_bw");
    let _ = std::fs::create_dir_all(&out_dir);
    let cp_log = out_dir.join(format!("cp_{run_id}.log"));
    let mut sink = ProgressSink::new(&cp_log, 5_000).expect("log");
    sink.write_line(&format!("=== Stage 1 CP with {} hints ===", combined.hints.len()));
    let t_cp = Instant::now();
    let outcome = solver.solve(&puzzle, &opts, &mut sink);
    let cp_elapsed = t_cp.elapsed();
    let stats_cp = sink.final_stats.clone();
    let cp_board = match outcome {
        SolveOutcome::Solved(b)
        | SolveOutcome::TimedOut { best_partial: b, .. }
        | SolveOutcome::Cancelled { best_partial: b, .. } => b,
        SolveOutcome::AllSolutions(bs) => bs.into_iter().next().unwrap_or_else(|| Board::empty(&puzzle)),
        SolveOutcome::Exhausted => {
            eprintln!("CP EXHAUSTED — extra hints unsatisfiable with this schedule!");
            Board::empty(&puzzle)
        }
        SolveOutcome::Error(e) => { eprintln!("CP ERROR: {e}"); Board::empty(&puzzle) }
    };
    let (cp_m, _) = score_board(&puzzle, &cp_board);
    let cp_p = placed_count(&cp_board, &puzzle);
    let cp_depth = stats_cp.as_ref().map(|s| s.max_depth_seen).unwrap_or(sink.best_depth);
    eprintln!("CP: {:.1}s depth={cp_depth} placed={cp_p}/256 matched={cp_m}/480",
        cp_elapsed.as_secs_f64());

    // Stage 2: ALNS with same hint set pinned (note: pinning ALL hints not
    // just canonical — the extras should NOT be moved by ALNS).
    eprintln!("\n--- Stage 2: ALNS ({}s, {} pins) ---",
        alns_budget_ms / 1000, combined.hints.len());
    let mut ops: Vec<Box<dyn DestroyOp>> = vec![
        Box::new(RandomRegion { k: 4 }),
        Box::new(WorstWindow { k: 5 }),
        Box::new(ConflictDriven { max_size: 30 }),
        Box::new(ConflictDriven { max_size: 80 }),
        Box::new(MwpmDefectPair { max_pairs: 12 }),
        Box::new(WorstBand { k_rows: 4 }),
        Box::new(BottomBandDestroy { k_rows: 3, first_row: 8 }),
        Box::new(ComponentDestroy { max_size: 100, min_size: 6 }),
        Box::new(HingeDestroy { halo: 1 }),
    ];
    let pinned_set: std::collections::BTreeSet<u32> =
        combined.hints.iter().map(|h| h.position).collect();
    let cfg = AlnsConfig {
        time_budget_ms: alns_budget_ms,
        repair_budget_ms: 1500,
        acceptance: Acceptance::SimulatedAnnealing { t: 1.0 },
        segment_iters: 50,
        seed,
        verbose: false,
        repair: RepairKind::Sa,
        cp_fallback_to_sa: true,
        pinned_positions: combined.hints.iter().map(|h| h.position).collect(),
        iter_budget: 0,
        lex_break_isoscore: false,
        checkpoint_path: None,
        checkpoint_every_ms: 60_000,
    };
    let t_alns = Instant::now();
    let (alns_board, stats) = run_alns(&puzzle, &cp_board, ops.as_mut_slice(), &cfg);
    let (alns_board, rg) = polish_rotations(&puzzle, &alns_board, &pinned_set);
    let (alns_board, sg) = piece_swap_hillclimb(&puzzle, &alns_board, &pinned_set);
    let (alns_m, _) = score_board(&puzzle, &alns_board);
    let alns_p = placed_count(&alns_board, &puzzle);
    let url = bucas_url(&puzzle, &alns_board, "v17_pinned_bw_alns");
    eprintln!(
        "\nALNS: {:.1}s iters={} matched={alns_m}/480 placed={alns_p}/256 polish: rot=+{rg} swap=+{sg}",
        t_alns.elapsed().as_secs_f64(), stats.iters
    );
    eprintln!("vs source board {src_m}/480 — Δ = {:+}", alns_m as i32 - src_m as i32);
    eprintln!("bucas: {url}");

    let json = serde_json::json!({
        "source_board": source_board.to_string_lossy(),
        "source_score": src_m,
        "pin_rows_from": pin_rows_from, "pin_rows_to": pin_rows_to,
        "extras_added": extras.len(),
        "total_hints": combined.hints.len(),
        "schedule": schedule,
        "cp_score": cp_m, "cp_placed": cp_p, "cp_depth": cp_depth,
        "alns_score": alns_m, "alns_placed": alns_p,
        "bucas_url": url,
        "placement": (0..puzzle.cell_count()).map(|p| {
            alns_board.get(p).map(|(pid, rot)| serde_json::json!({
                "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
            }))
        }).collect::<Vec<_>>(),
    });
    let _ = std::fs::write(out_dir.join(format!("final_{run_id}.json")),
        serde_json::to_string_pretty(&json).unwrap());
    eprintln!("saved: output/v17_pinned_bw/final_{run_id}.json");
}
