// Vol-17 idea K — sequential pipeline:
//   1. Blackwood RAW + calibrated_v17a schedule produces a high-quality
//      sparse partial.
//   2. Convert placed cells (including canonical 5 hints) to a Hints
//      vector and feed to joe_depth150_bp_par for the FILL stage. The
//      engine sees all of them as pinned, so CSP only searches the
//      unplaced cells.
//   3. ALNS-fill on the result, with the same union-pinning so ALNS
//      doesn't churn the Blackwood-anchored cells.
//
// Motivation: vol-15 measured +260-270 ALNS lift from sparse Blackwood
// seeds vs baseline's +147 from a denser seed. If Blackwood places ~85
// cells of higher-than-average quality, joe_depth150_bp_par should be
// able to fill the remaining ~170 cells with HIGH coverage (vs cold
// start where it walls at ~175 placed = ~440 matched).
//
// Critical caveat: a Blackwood RAW run with break allowance produces a
// partial that may have ≤ N_breaks edge mismatches. Pinning those into
// joe_depth150_bp_par is then "approximately correct" — AC-3 / gacolor
// / NS-1 invariants may flag the pinned partial as infeasible. We
// guard via apply_symmetry_and_hints validation; if it rejects, fall
// back to the canonical 5 hints only (recovering baseline behaviour
// at worst).
//
// Stages, all single-seed, sequential, all multi-core (rayon defaults):
//   blackwood_raw  CP for --cp-bw-ms  (default 60_000 = 1 min)
//   joe_depth150   CP for --cp-csp-ms (default 240_000 = 4 min)
//   ALNS           for --alns-ms      (default 300_000 = 5 min)
//
// CLI:
//   --cp-bw-ms        Blackwood seed-generator budget (default 60_000)
//   --cp-csp-ms       joe_depth150_bp_par fill budget (default 240_000)
//   --alns-ms         ALNS final-repair budget       (default 300_000)
//   --seed            (default 1)
//   --schedule        "calibrated_v17a" (default) | "bw469"
//   --pin             "blackwood_partial" (default) | "canonical_only"

#![forbid(unsafe_code)]

use std::path::PathBuf;
use std::sync::Arc;
use std::time::Instant;

use eternity2_bench_audit::{placed_count, score_board_dense as score_board, ProgressSink};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::bucas_url;
use eternity2_core::{Board, Hint, Hints, Puzzle};
use eternity2_localsearch::{
    run_alns, Acceptance, AlnsConfig, ComponentDestroy, ComponentPlusHaloDestroy,
    ConflictDriven, DestroyOp, HingeDestroy, MwpmDefectPair, RandomRegion, RepairKind,
    WorstBand, WorstRow, WorstWindow,
};
use eternity2_solver_engine::{
    blackwood_schedule_469, blackwood_schedule_calibrated_v17a,
    load_edge_bp_marginals, EngineSolver,
};
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

fn board_to_hints(puzzle: &Puzzle, board: &Board, base_hints: &Hints) -> Hints {
    let mut out: Vec<Hint> = base_hints.hints.clone();
    let already: std::collections::HashSet<u32> = base_hints
        .hints
        .iter()
        .map(|h| h.position)
        .collect();
    for pos in 0..puzzle.cell_count() {
        if already.contains(&pos) { continue; }
        if let Some((pid, rot)) = board.get(pos) {
            out.push(Hint { position: pos, piece_id: pid, rotation: rot });
        }
    }
    Hints { hints: out }
}

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let bp_path = PathBuf::from("output/v12_bp/edge_bp_60i.json");

    let mut cp_bw_ms: u64 = 60_000;
    let mut cp_csp_ms: u64 = 240_000;
    let mut alns_ms: u64 = 300_000;
    let mut seed: u64 = 1;
    let mut schedule_kind = "calibrated_v17a".to_string();
    let mut pin_mode = "blackwood_partial".to_string();
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--cp-bw-ms" => cp_bw_ms = args.next().unwrap().parse().unwrap(),
            "--cp-csp-ms" => cp_csp_ms = args.next().unwrap().parse().unwrap(),
            "--alns-ms" => alns_ms = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            "--schedule" => schedule_kind = args.next().unwrap(),
            "--pin" => pin_mode = args.next().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }

    let run_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let out_dir = PathBuf::from(format!("output/v17_bw_then_csp/run_{run_id}"));
    std::fs::create_dir_all(&out_dir).expect("mkdir");

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    eprintln!("loaded canonical E2 with {} hints", hints.hints.len());

    let edge_bp = load_edge_bp_marginals(&bp_path).ok();

    // ---------- Stage 1: Blackwood RAW (seed generator) ----------
    let schedule = match schedule_kind.as_str() {
        "bw469" => blackwood_schedule_469(&puzzle, &hints).expect("bw469 schedule"),
        "calibrated_v17a" | "calibrated" => blackwood_schedule_calibrated_v17a(&puzzle, &hints)
            .expect("calibrated_v17a schedule"),
        other => panic!("unknown --schedule {other}"),
    };
    eprintln!(
        "Blackwood schedule [{schedule_kind}]: pool={} targets={:?}",
        schedule.heuristic_pool_size, schedule.exhaustion_targets
    );
    let schedule_arc = Arc::new(schedule);

    let mut bw_opts = SolveOpts::default();
    bw_opts.time_budget_ms = cp_bw_ms;
    bw_opts.seed = seed;
    bw_opts.hints = hints.clone();
    if let Some(bp) = edge_bp.clone() { bw_opts.edge_bp_marginals = Some(bp); }

    let mut bw_solver = Box::new(EngineSolver::blackwood_raw_par(schedule_arc.clone()));
    let (bw_board, bw_m, bw_p, bw_d, _bw_n) = solve_to_board(
        "stage1_blackwood_raw",
        &mut bw_solver,
        &puzzle,
        &bw_opts,
        &out_dir.join("stage1_blackwood.log"),
    );
    let bw_url = bucas_url(&puzzle, &bw_board, "v17_stage1_blackwood");
    eprintln!("[stage1] bucas: {bw_url}");
    let _ = std::fs::write(
        out_dir.join("stage1_blackwood_board.json"),
        serde_json::to_string_pretty(&serde_json::json!({
            "placement": (0..puzzle.cell_count()).map(|p| {
                bw_board.get(p).map(|(pid, rot)| serde_json::json!({
                    "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
                }))
            }).collect::<Vec<_>>(),
            "bucas_url": &bw_url,
        })).unwrap(),
    );

    // ---------- Stage 2: joe_depth150_bp_par with Blackwood partial pinned ----------
    let pinned_hints = match pin_mode.as_str() {
        "blackwood_partial" => board_to_hints(&puzzle, &bw_board, &hints),
        "canonical_only" => hints.clone(),
        other => panic!("unknown --pin {other}"),
    };
    let extra_pinned = pinned_hints.hints.len() as u32 - hints.hints.len() as u32;
    eprintln!(
        "[stage2] pinning {} hints total ({} canonical + {} from blackwood partial)",
        pinned_hints.hints.len(), hints.hints.len(), extra_pinned
    );

    // Try the pin. If the engine rejects it (apply_symmetry_and_hints
    // fails — propagator invariant violation), fall back to canonical
    // hints only so we at least get a baseline run.
    let mut csp_opts = SolveOpts::default();
    csp_opts.time_budget_ms = cp_csp_ms;
    csp_opts.seed = seed.wrapping_add(1);
    csp_opts.hints = pinned_hints.clone();
    if let Some(bp) = edge_bp.clone() { csp_opts.edge_bp_marginals = Some(bp); }

    // Do a 1ms probe first — if the engine immediately exhausts (i.e.
    // the pinned partial is infeasible under its propagators), fall
    // back to canonical hints.
    let mut probe_opts = csp_opts.clone();
    probe_opts.time_budget_ms = 200;
    let mut probe_solver = Box::new(EngineSolver::joe_depth150_bp_par());
    let mut probe_sink = ProgressSink::new(&out_dir.join("stage2_probe.log"), 1_000_000)
        .expect("open probe log");
    let probe_outcome = probe_solver.solve(&puzzle, &probe_opts, &mut probe_sink);
    let pin_feasible = !matches!(probe_outcome, SolveOutcome::Exhausted)
        && !matches!(probe_outcome, SolveOutcome::Error(_));
    if !pin_feasible {
        eprintln!("[stage2] WARNING: probe with full pinning was infeasible — falling back to canonical-only hints");
        csp_opts.hints = hints.clone();
    } else {
        eprintln!("[stage2] probe ok with full pinning");
    }

    let mut csp_solver = Box::new(EngineSolver::joe_depth150_bp_par());
    let (csp_board, csp_m, csp_p, csp_d, _csp_n) = solve_to_board(
        "stage2_joe_csp",
        &mut csp_solver,
        &puzzle,
        &csp_opts,
        &out_dir.join("stage2_csp.log"),
    );
    let csp_url = bucas_url(&puzzle, &csp_board, "v17_stage2_csp");
    eprintln!("[stage2] bucas: {csp_url}");
    let _ = std::fs::write(
        out_dir.join("stage2_csp_board.json"),
        serde_json::to_string_pretty(&serde_json::json!({
            "placement": (0..puzzle.cell_count()).map(|p| {
                csp_board.get(p).map(|(pid, rot)| serde_json::json!({
                    "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
                }))
            }).collect::<Vec<_>>(),
            "bucas_url": &csp_url,
        })).unwrap(),
    );

    // ---------- Stage 3: ALNS ----------
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
    let pinned_positions: Vec<u32> = pinned_hints.hints.iter().map(|h| h.position).collect();
    let cfg = AlnsConfig {
        time_budget_ms: alns_ms,
        // Vol-17 — bumped from 500ms (see run_e2_blackwood note).
        repair_budget_ms: 1500,
        acceptance: Acceptance::SimulatedAnnealing { t: 1.0 },
        segment_iters: 50,
        seed,
        verbose: false,
        // Vol-17 — flip primary repair to CP. Sound here too since the
        // K-pipeline already pinned Blackwood's partial via Hints; the
        // remaining free set is what CP can search-fill.
        repair: RepairKind::Cp,
        cp_fallback_to_sa: true,
        pinned_positions: pinned_positions.clone(),
    };
    eprintln!("[stage3] ALNS pinning {} positions, budget={}s", pinned_positions.len(), alns_ms / 1000);
    let t_alns = Instant::now();
    let (alns_board, alns_stats) = run_alns(&puzzle, &csp_board, ops.as_mut_slice(), &cfg);
    let alns_elapsed = t_alns.elapsed();
    let (am, _at) = score_board(&puzzle, &alns_board);
    let ap = placed_count(&alns_board, &puzzle);
    let alns_url = bucas_url(&puzzle, &alns_board, "v17_stage3_alns");
    eprintln!(
        "[stage3] ALNS: {:.1}s  iters={}  placed={ap}/256  matched={am}/480  Δ_vs_csp={:+}",
        alns_elapsed.as_secs_f64(),
        alns_stats.iters,
        am as i32 - csp_m as i32
    );
    eprintln!("[stage3] bucas: {alns_url}");
    let _ = std::fs::write(
        out_dir.join("stage3_alns_board.json"),
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
    eprintln!("=== vol-17 idea K (Blackwood-then-CSP) summary (seed={seed}) ===");
    eprintln!(
        "  stage1 blackwood_raw [{schedule_kind}]:  matched={bw_m}/480  placed={bw_p}/256  depth={bw_d}"
    );
    eprintln!(
        "  stage2 joe_csp [{}]:  matched={csp_m}/480  placed={csp_p}/256  depth={csp_d}",
        if pin_feasible { "full-pin" } else { "fallback-canonical" }
    );
    eprintln!("  stage3 alns: matched={am}/480  placed={ap}/256  Δ_vs_stage2={:+}", am as i32 - csp_m as i32);

    let summary = serde_json::json!({
        "puzzle": "canonical_5_clue_16x16",
        "seed": seed,
        "schedule_kind": schedule_kind,
        "pin_mode": pin_mode,
        "pin_feasible": pin_feasible,
        "stage1_blackwood": { "matched": bw_m, "placed": bw_p, "depth": bw_d, "bucas": bw_url },
        "stage2_csp": { "matched": csp_m, "placed": csp_p, "depth": csp_d, "bucas": csp_url },
        "stage3_alns": { "matched": am, "placed": ap, "bucas": alns_url, "iters": alns_stats.iters },
    });
    let _ = std::fs::write(out_dir.join("summary.json"), serde_json::to_string_pretty(&summary).unwrap());
    eprintln!("\nlogs + boards: {}", out_dir.display());
}
