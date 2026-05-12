// Vol-14 #2 — Iterated random-restart loop around the CP engine.
//
// Joe-Saunders 2026 reports 17-49% iteration reduction from a
// "prune back to depth T and re-randomize after N stuck iters"
// policy. The engine doesn't expose mid-search restart hooks, so
// this is the cheapest faithful PoC of the *outer-loop* version:
//
//   while wall_clock < budget:
//     pick (solver, seed) — alternate BP-greedy and RandomShuffle
//     run for `round_ms` ms with that seed
//     remember best_partial across rounds (by max_depth_seen)
//
// This trades one deep dive for many shallower roots with
// different value-order biases. Combines vol-12 edge-BP
// (exploit) with the existing RandomShuffle profile (explore).
//
// CLI: --budget-ms (total, default 300_000) --round-ms (default 30_000).

use std::io::Write;
use std::path::PathBuf;
use std::sync::Arc;
use std::time::Instant;

use eternity2_bench_audit as _;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_bench_audit::{placed_count, score_board_dense as score_board};
use eternity2_benchmark::report::bucas_url;
use eternity2_core::Board;
use eternity2_events::{EventBody, EventSink, FinalStats, SolverEvent};
use eternity2_solver_engine::{load_edge_bp_marginals, EngineSolver};
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

struct RoundSink {
    best_depth: u32,
    final_stats: Option<FinalStats>,
}

impl RoundSink {
    fn new() -> Self {
        Self { best_depth: 0, final_stats: None }
    }
}

impl EventSink for RoundSink {
    fn emit(&mut self, event: SolverEvent) {
        if let EventBody::Backtrack { from_depth, .. } = &event.body {
            if *from_depth > self.best_depth { self.best_depth = *from_depth; }
        }
        if event.depth > self.best_depth { self.best_depth = event.depth; }
        match event.body {
            EventBody::Solved { final_stats, .. }
            | EventBody::Exhausted { final_stats, .. }
            | EventBody::TimedOut { final_stats, .. }
            | EventBody::Cancelled { final_stats, .. } => {
                self.final_stats = Some(final_stats);
            }
            _ => {}
        }
    }
}

/// Canonical E2 score: matched internal edges out of total internal
/// edges (480 on canonical 16x16). Unplaced cells contribute 0.

#[derive(Clone)]
enum Strategy { BpExploit, RandomExplore }

fn make_solver(s: &Strategy) -> EngineSolver {
    match s {
        Strategy::BpExploit => EngineSolver::joe_depth150_bp_par(),
        // gacolor_ac3_random_par is the seeded-random value-order profile
        // (vol-11). Different seeds reach different CP partials.
        Strategy::RandomExplore => EngineSolver::gacolor_ac3_random_par(),
    }
}

fn strategy_label(s: &Strategy) -> &'static str {
    match s { Strategy::BpExploit => "bp", Strategy::RandomExplore => "random" }
}

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let bp_path = PathBuf::from("output/v12_bp/edge_bp_60i.json");

    let run_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let out_dir = PathBuf::from(format!("output/v14_restart/run_{run_id}"));
    std::fs::create_dir_all(&out_dir).expect("mkdir");
    #[cfg(unix)]
    {
        let latest = PathBuf::from("output/v14_restart/latest");
        let _ = std::fs::remove_file(&latest);
        let _ = std::os::unix::fs::symlink(format!("run_{run_id}"), &latest);
    }

    let mut budget_ms: u64 = 300_000;
    let mut round_ms: u64 = 30_000;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--budget-ms" => budget_ms = args.next().unwrap().parse().unwrap(),
            "--round-ms" => round_ms = args.next().unwrap().parse().unwrap(),
            _ => eprintln!("(unrecognized arg: {a})"),
        }
    }

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let edge_bp: Arc<Vec<f32>> = load_edge_bp_marginals(&bp_path).expect("load edge_bp");

    eprintln!(
        "vol-14 #2 iterated-restart: budget={}s, round={}s, expected_rounds={}",
        budget_ms / 1000, round_ms / 1000, budget_ms / round_ms,
    );

    let log_path = out_dir.join("rounds.log");
    let mut log = std::fs::File::create(&log_path).expect("open log");

    let global_start = Instant::now();
    let mut best_depth_global: u32 = 0;
    let mut best_matched_global: u32 = 0;
    let mut best_placed_global: u32 = 0;
    let mut best_board: Option<Board> = None;
    let mut best_round: i32 = -1;
    let mut best_strategy: String = String::new();
    let mut round = 0u32;
    let mut seed: u64 = 1;

    let strategies = [Strategy::BpExploit, Strategy::RandomExplore];

    let _ = writeln!(log, "round\tstrategy\tseed\telapsed_ms\tround_ms\tnodes\tdepth\tmatched\tplaced\tbest_depth_global");

    loop {
        let total_elapsed = global_start.elapsed().as_millis() as u64;
        if total_elapsed >= budget_ms { break; }
        let remaining = budget_ms - total_elapsed;
        let this_round_ms = remaining.min(round_ms);

        let strategy = &strategies[(round as usize) % strategies.len()];
        let mut solver = make_solver(strategy);

        let mut opts = SolveOpts::default();
        opts.time_budget_ms = this_round_ms;
        opts.seed = seed;
        opts.hints = hints.clone();
        if matches!(strategy, Strategy::BpExploit) {
            opts.edge_bp_marginals = Some(edge_bp.clone());
        }

        let mut sink = RoundSink::new();
        let t0 = Instant::now();
        let outcome = solver.solve(&puzzle, &opts, &mut sink);
        let elapsed_ms = t0.elapsed().as_millis() as u64;

        let board = match outcome {
            SolveOutcome::Solved(b) => Some(b),
            SolveOutcome::TimedOut { best_partial, .. } => Some(best_partial),
            SolveOutcome::Cancelled { best_partial, .. } => Some(best_partial),
            SolveOutcome::Exhausted => None,
            SolveOutcome::AllSolutions(bs) => bs.into_iter().next(),
            SolveOutcome::Error(_) => None,
        };

        let (matched, _total) = board.as_ref().map(|b| score_board(&puzzle, b)).unwrap_or((0, 0));
        let placed = board.as_ref().map(|b| placed_count(b, &puzzle)).unwrap_or(0);
        let depth = sink.final_stats.as_ref().map(|s| s.max_depth_seen).unwrap_or(sink.best_depth);
        let nodes = sink.final_stats.as_ref().map(|s| s.nodes).unwrap_or(0);

        let _ = writeln!(
            log, "{round}\t{strat}\t{seed}\t{tot_elapsed}\t{elapsed_ms}\t{nodes}\t{depth}\t{matched}\t{placed}\t{best_depth_global}",
            strat = strategy_label(strategy),
            tot_elapsed = total_elapsed,
        );
        let _ = log.flush();

        eprintln!(
            "[round {round:>3}] {strat:>6} seed={seed:>3} elapsed={elapsed_ms:>6}ms depth={depth:>3} matched={matched:>4} placed={placed:>4}/{} (global best depth={best_depth_global})",
            puzzle.cell_count(),
            strat = strategy_label(strategy),
        );

        // Track global best by "depth desc, then matched desc, then placed desc".
        // depth is what the engine reports; matched is more robust for displaying
        // score. Both should monotonically improve in lockstep but we keep both.
        let improved = depth > best_depth_global
            || (depth == best_depth_global && matched > best_matched_global);
        if improved {
            best_depth_global = depth;
            best_matched_global = matched;
            best_placed_global = placed;
            best_round = round as i32;
            best_strategy = strategy_label(strategy).into();
            best_board = board;
        }

        round += 1;
        seed += 1;
    }

    let summary_path = out_dir.join("summary.json");
    let (bucas, board_json) = if let Some(b) = best_board.as_ref() {
        let bu = bucas_url(&puzzle, b, "v14_restart_best");
        let j = serde_json::json!({
            "placement": (0..puzzle.cell_count()).map(|pos| {
                b.get(pos).map(|(pid, rot)| serde_json::json!({
                    "pos": pos,
                    "piece_id": u32::from(pid),
                    "rotation": rot.as_u8(),
                }))
            }).collect::<Vec<_>>(),
        });
        (bu, j)
    } else {
        ("(no board)".to_string(), serde_json::json!({}))
    };

    let summary = serde_json::json!({
        "schema_version": 1,
        "budget_ms": budget_ms,
        "round_ms": round_ms,
        "rounds_completed": round,
        "best_round": best_round,
        "best_strategy": best_strategy,
        "best_depth_global": best_depth_global,
        "best_edge_matches": best_matched_global,
        "best_pieces_placed": best_placed_global,
        "puzzle_cells": puzzle.cell_count(),
        "bucas": bucas,
        "board": board_json,
    });
    std::fs::write(&summary_path, serde_json::to_string_pretty(&summary).unwrap())
        .expect("write summary");

    eprintln!(
        "\n=== vol-14 #2 RESTART FINAL ===\nrounds: {round}\nbest_round: {best_round} ({best_strategy})\nbest_depth: {best_depth_global}\nbest_matched: {best_matched_global}\nbest_placed: {best_placed_global}/{}\nbucas: {bucas}\nout: {}",
        puzzle.cell_count(),
        out_dir.display(),
    );
}
